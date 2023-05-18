import collections
import hashlib
import json
import os


from .expansion_pool import ExpansionPool
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

        self.work = None

        self.options = options if options is not None else dict()

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

        pool = ExpansionPool(logger=self.logger)
        self.work = pool.work

        expansion = self._execute(indent=0, my_path_component=os.path.basename(self.path), traversal="")

        pool.drain()

        self._hashcodes_cleanup()

        return expansion

    def _execute(self, traversal, indent, my_path_component):
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

        self.traversal = traversal
        self.indent = indent
        self.my_path_component = my_path_component

        self._log(f"path [{self.path}] traversal [{self.traversal}]")

        if self._is_leaf_node(LeafNode.When.BEFORE):
            return self.data

        for key in self._data_iter():
            self._recursively_expand(key=key)

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

        if leaf_node and not leaf_node.WHAT == LeafNode.What.DUMP:
            return True

        directory: str = os.path.dirname(self.path)
        data_file: str = f"{os.path.basename(self.path)}.json"

        assert isinstance(directory, str)
        assert isinstance(data_file, str)

        dumps = json.dumps(self.data, **self.json_dump_kwargs)
        self.work.append((directory, data_file, dumps))

        checksum, file_suffix = self._hash_function(dumps)
        if checksum:
            md5_file: str = f"{os.path.basename(self.path)}.{file_suffix}"
            # self.work.append((directory, data_file, dumps, md5_file, checksum))
            self.work.append((directory, md5_file, checksum))
            self.hashcodes[checksum].append(data_file)
        # else:
        #     self.work.append((directory, data_file, dumps, None, None))

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
            self._recursion_instance(
                path=os.path.dirname(self.path),
                data={os.path.basename(self.path): self.data},
                leaf_nodes=c.children,
            )._execute(indent=self.indent + 2, my_path_component=os.path.basename(self.path), traversal="")
            self._log(f"<<< Expand children of [{c.raw}]")

            return self._dump(c)

        return False

    def _log(self, string):
        self.logger.debug(" " * self.indent + string)

    def _recursion_instance(self, *, path, data, leaf_nodes):
        instance = Expander(
            logger=self.logger,
            #
            data=data,
            leaf_nodes=leaf_nodes,
            path=path,
            #
            **self.options,
        )
        instance.work=self.work
        return instance

    def _recursively_expand(self, *, key):
        if not (isinstance(self.data[key], dict) or isinstance(self.data[key], list)):
            return

        path_component = str(key).replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")

        expander = self._recursion_instance(
            path=os.path.join(self.path, path_component),
            data=self.data[key],
            leaf_nodes=self.leaf_nodes,
        )
        self.data[key] = expander._execute(
            indent=self.indent + 2, my_path_component=path_component, traversal=f"{self.traversal}/{key}"
        )

        # Add the child's hashcodes to our own so that when we unroll the recursion the root
        # will not need to recurse again to collect the entire list.
        for hashcode in expander.hashcodes:
            if hashcode in self.hashcodes:
                self.hashcodes[hashcode] += expander.hashcodes[hashcode]
            else:
                self.hashcodes[hashcode] = expander.hashcodes[hashcode]

        # self.data[key] = {"$ref": f"{self.my_path_component}/{path_component}.json"}
