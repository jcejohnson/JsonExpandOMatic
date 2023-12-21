import collections
import hashlib
import json
import os
from pathlib import Path
from typing import cast

from .leaf_node import LeafNode


class Expander:
    """Expand a dict or list into one or more json files."""

    HASH_MD5 = "HASH_MD5"

    def __init__(self, *, logger, path, data, leaf_nodes, **options):
        assert isinstance(data, dict) or isinstance(data, list)

        self.logger = logger
        self.path = path
        self.data = data
        self.leaf_nodes = leaf_nodes

        self.options = options if options is not None else dict()

        # options will not include pool or zip options when called recursively.
        self.pool_options = {
            # See ExpansionPool
            key: self.options.pop(key)
            for key in {key for key in self.options.keys() if key.startswith("pool_")}
        }
        self.zip_options = {
            # See ExpansionZipper
            key: self.options.pop(key)
            for key in {key for key in self.options.keys() if key.startswith("zip_")}
        }

        assert (
            (not self.pool_options and not self.zip_options) or self.pool_options or self.zip_options
        ), f"Cannot mix {sorted(self.pool_options.keys())} and {sorted(self.zip_options.keys())}"

        self.ref_key = self.options.get("ref_key", "$ref")

        self.json_dump_kwargs = self.options.get(
            "json_dump_kwargs", {"indent": "", "sort_keys": False, "separators": (",", ":")}
        )

        self.hash_mode = self.options.get("hash_mode", None)
        if self.hash_mode == Expander.HASH_MD5:
            self._hash_function = self._hash_md5
        else:
            self._hash_function = lambda *args, **kwargs: (None, None)

        # Map hashcodes of dict objects to the json files they are saved as.
        #   key   -- hashcode as specified by self.hash_mode
        #   value -- list of files w/ hashcode
        # We can use these in a 2nd pass to create $refs to identical objects.
        self.hashcodes = collections.defaultdict(lambda: list())

    def execute(self):
        """Expand self.data into one or more json files."""

        # Replace the _dump() method with a no-op for the root of the data.
        self._dump = lambda *args: None

        if self.zip_options:
            from .expansion_zipper import ExpansionZipper

            pool, work = ExpansionZipper(logger=self.logger, output_path=self.path, **self.zip_options).setup()
            self.path = pool.zip_root
        elif self.pool_options:
            from .expansion_pool import ExpansionPool

            pool, work = ExpansionPool(logger=self.logger, **self.pool_options).setup()
        else:
            from .expansion_pool import ExpansionPool

            pool, work = ExpansionPool(logger=self.logger, pool_disable=True).setup()

        expansion = self._execute(indent=0, my_path_component=os.path.basename(self.path), traversal="", work=work)

        pool.finalize()

        self._hashcodes_cleanup()

        return expansion

    def _execute(self, traversal, indent, my_path_component, work):
        """Main...

        Parameters
        ----------
        indent : int
            Used to indent log messages so that we can see the data tree.
        traversal : string
            A '/' separated path into the json doc.
            This is ${path} with self.path removed & is what we match against
            the self.leaf_nodes regular expressions.
        my_path_component : string
            This is the filesystem path component that represents self.data
            It is os.path.basename(self.path) with some mangling applied.

        Returns:
        --------
        dict
            data
        """

        self.indent = indent
        self.my_path_component = my_path_component
        self.traversal = traversal
        self.work = work

        self._log(f"path [{self.path}] traversal [{self.traversal}]")

        if self._is_leaf_node(LeafNode.When.BEFORE):
            return self.data

        # if self._is_leaf_node(LeafNode.When.AFTER):
        #     print(self.data)
        #     breakpoint()

        for key in self._data_iter():
            self._recursively_expand(key=key)

        # if self._is_leaf_node(LeafNode.When.AFTER):
        #     print(self.data)
        #     breakpoint()

        if self._is_leaf_node(LeafNode.When.AFTER):
            return self.data

        # If no LeafNode has matched, our default
        # action is to dump self.data to a file.
        self._dump()

        return self.data

    ########################################

    def _data_iter(self):
        if isinstance(self.data, dict):
            for key in sorted(self.data.keys()):
                yield key

        elif isinstance(self.data, list):
            for key, _ in enumerate(self.data):
                yield key

        return None

    def _dump(self, leaf_node=None):
        """Dump self.data to "{self.path}.json" if leaf_node.WHAT == LeafNode.What.DUMP
        and set self.data = {"$ref": f"{directory}/{filename}"}

        if self.hash_mode, calculate a hashcode for "{self.path}.json" and save
        as "{self.path}.xxx" (where `xxx` depends on the hash function selected).

        Always returns True so that _is_leaf_node() is less gross.
        """

        if leaf_node:
            if leaf_node.WHAT == LeafNode.What.INCLUDE:
                if leaf_node.WHEN == LeafNode.When.AFTER:
                    #
                    # This is triggered by:
                    #   "A<:/root/actors/[^/]+/filmography"
                    #
                    # In this scenario the contents of what would have been filmography.json
                    # is included in the <actor>.json file under the <actor> key.
                    # self.data at this point still expects that to be the case so its $ref
                    # elements are written relative to <actor> rather than `actors`. To make
                    # jsonref work we need to prefix $ref to make it relative to `actors`.
                    #
                    # self.path = "/path/to/root/actors/charlie_chaplin/filmography"
                    #
                    # self.data = [ {"$ref": "filmography/0.json"} ... ]
                    #                         ^--- becomes --v
                    # self.data = [ {"$ref": "charlie_chaplin/filmography/0.json"} ... ]
                    #
                    fq_path = Path(self.path)  # /path/to/root/actors/charlie_chaplin/filmography
                    fq_path_name = fq_path.name  # filmography
                    for key in self._data_iter():
                        assert isinstance(self.data[key], dict)  # FIXME: This may not be valid. Testing required.
                        value = cast(dict, self.data[key])  # value = {"$ref": "filmography/0.json"}
                        data_path = value.get(self.ref_key)  # data_path = "filmography/0.json"
                        assert data_path
                        if fq_path_name == Path(data_path).parent.name:
                            value[self.ref_key] = str(Path(fq_path.parent.name, data_path))

                return True

            assert leaf_node.WHAT == LeafNode.What.DUMP

        dumps = json.dumps(self.data, **self.json_dump_kwargs)

        directory = os.path.dirname(self.path)
        filename = os.path.basename(self.path)
        data_file = f"{filename}.json"

        checksum, checksumfile_suffix = self._hash_function(dumps)
        checksum_file = f"{filename}.{checksumfile_suffix}"

        if checksum:
            self.work.append((directory, data_file, dumps, checksum_file, checksum))
            self.hashcodes[checksum].append(data_file)
        else:
            self.work.append((directory, data_file, dumps, None, None))

        # Build a reference to the file we just wrote.
        directory = os.path.basename(directory)
        data_file = os.path.basename(data_file)
        self.data = {self.ref_key: f"{directory}/{data_file}"}

        return True

    def _hashcodes_cleanup(self):
        """Strip self.path from the hashcodes' files in case we want to make $refs from them.
        Also removes any entries having less than two files.
        """
        l = len(self.path) + 1  # noqa: E741
        self.hashcodes = {k: [f[l:] for f in v] for k, v in self.hashcodes.items() if len(v) > 1}

    def _hash_md5(self, dumps):
        """Compute and save the md5 hashcode of `dumps`.
        Returns checksum.
        """
        checksum = hashlib.md5(dumps.encode()).hexdigest()
        return checksum, "md5"

    def _is_leaf_node(self, when):
        for c in self.leaf_nodes:
            if c.comment or not c.match(string=self.traversal, when=when):
                continue

            if not c.children:
                return self._dump(c)

            self._log(f">>> Expand children of [{c.raw}]")
            expander = self._recursion_instance(
                path=os.path.dirname(self.path), data={os.path.basename(self.path): self.data}, leaf_nodes=c.children
            )
            expander._execute(
                indent=self.indent + 2, my_path_component=os.path.basename(self.path), traversal="", work=self.work
            )
            self._log(f"<<< Expand children of [{c.raw}]")

            return self._dump(c)

        return False

    def _log(self, string):
        self.logger.debug(" " * self.indent + string)

    def _recursively_expand(self, *, key):
        if not (isinstance(self.data[key], dict) or isinstance(self.data[key], list)):
            return

        path_component = str(key).replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")

        expander = self._recursion_instance(
            path=os.path.join(self.path, path_component), data=self.data[key], leaf_nodes=self.leaf_nodes
        )
        self.data[key] = expander._execute(
            indent=self.indent + 2,
            my_path_component=path_component,
            traversal=f"{self.traversal}/{key}",
            work=self.work,
        )

        # Add the child's hashcodes to our own so that when we unroll the recursion the root
        # will not need to recurse again to collect the entire list.
        for hashcode in expander.hashcodes:
            if hashcode in self.hashcodes:
                self.hashcodes[hashcode] += expander.hashcodes[hashcode]
            else:
                self.hashcodes[hashcode] = expander.hashcodes[hashcode]

    def _recursion_instance(self, *, path, data, leaf_nodes):  # key, path_component):
        expander = Expander(logger=self.logger, path=path, data=data, leaf_nodes=leaf_nodes, **self.options)

        return expander

        # self.data[key] = {"$ref": f"{self.my_path_component}/{path_component}.json"}
