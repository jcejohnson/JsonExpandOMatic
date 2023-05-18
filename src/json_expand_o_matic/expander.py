import concurrent.futures
import collections
import hashlib
import json
import os
from functools import partial
from asyncio import sleep
from queue import Queue
from .leaf_node import LeafNode

from aiofile import async_open
import asyncio
from .expansion_pool import ExpansionPool
import threading

def _write_file(directory, filename, data):
    try:
        # Assume that the path will already exist.
        # We'll take a hit on the first file in each new path but save the overhead
        # of checking on each subsequent one. This assumes that most objects will
        # have multiple nested objects.
        with open(filename, "w") as f:
            f.write(data)
    except FileNotFoundError:
        os.makedirs(directory, exist_ok=True)
        with open(filename, "w") as f:
            f.write(data)

class Expander:
    """Expand a dict or list into one or more json files."""

    HASH_MD5 = "HASH_MD5"

    def __init__(self, *, logger, path, data, leaf_nodes, queue=None, **options):
        assert isinstance(data, dict) or isinstance(data, list)

        self.logger = logger
        self.path = path
        self.data = data
        self.leaf_nodes = leaf_nodes

        self.queue = queue

        self.options = options if options is not None else dict()

        self.ref_key = self.options.get("ref_key", "$ref")

        self.hash_mode = self.options.get("hash_mode", None)
        if self.hash_mode == Expander.HASH_MD5:
            self._hash_function = self._hash_md5
        else:
            self._hash_function = lambda *args, **kwargs: None, None

        # Map hashcodes of dict objects to the json files they are saved as.
        #   key   -- hashcode as specified by self.hash_mode
        #   value -- list of files w/ hashcode
        # We can use these in a 2nd pass to create $refs to identical objects.
        self.hashcodes = collections.defaultdict(lambda: list())

    def execute(self):
        """Expand self.data into one or more json files."""

        self._dump = lambda *args : None

        pool_size = int(os.cpu_count()/2+1)
        print(f"Pool size is {pool_size}")
        with concurrent.futures.ProcessPoolExecutor(pool_size) as pool:
            self.queue = pool.queue

            print("Begin Work")
            expansion = self._execute(indent=0, my_path_component=os.path.basename(self.path), traversal="")
            print(self.queue.qsize())

            while not self.queue.empty():
                directory, filename, checksum, checksum_file, dumps = self.queue.get()
                pool.submit(_write_file, directory, filename, checksum, checksum_file, dumps)

        print("Hashcode Cleanup")
        self._hashcodes_cleanup()

        print("Work Complete")
        return expansion

    async def _json_save(self, directory, filename, checksum, checksum_file, dumps):
        try:
            # Assume that the path will already exist.
            # We'll take a hit on the first file in each new path but save the overhead
            # of checking on each subsequent one. This assumes that most objects will
            # have multiple nested objects.
            async with async_open(filename, "w") as f:
                await f.write(dumps)
            async with async_open(checksum_file, "w") as f:
                await f.write(checksum)

        except FileNotFoundError:
            os.makedirs(directory, exist_ok=True)
            async with async_open(filename, "w") as f:
                await f.write(dumps)
            async with async_open(checksum_file, "w") as f:
                await f.write(checksum)

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
        data_file: str = f"{self.path}.json"

        assert isinstance(directory, str)
        assert isinstance(data_file, str)

        dumps = json.dumps(self.data, indent="", sort_keys=False)
        self.queue.put((directory, data_file, dumps))

        checksum, file_suffix = self._hash_function(dumps)
        if checksum:
            md5_file: str = f"{self.path}.{file_suffix}"
            self.queue.put((directory, md5_file, checksum))
            self.hashcodes[checksum].append(data_file)

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
            queue=self.queue,
            #
            data=data,
            leaf_nodes=leaf_nodes,
            path=path,
            #
            **self.options,
        )
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
