
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as wait_for
from time import sleep

import json
import os

from .leaf_node import LeafNode


class Expander:
    """Expand a dict or list into one or more json files."""

    def __init__(self, *, logger, path, data, leaf_nodes, thread_pool=None):

        assert isinstance(data, dict) or isinstance(data, list)

        self.logger = logger
        self.path = path
        self.data = data
        self.leaf_nodes = leaf_nodes

        self.main_thread = (thread_pool == None)
        self.thread_pool = thread_pool if thread_pool else ThreadPoolExecutor()

    def execute(self):
        """Expand self.data into one or more json files."""

        # Replace the _dump() method with a no-op for the root of the data.
        self._dump = lambda *args: None

        return self._execute(indent=0, my_path_component=os.path.basename(self.path), traversal="")

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

        futures = {}
        for key in self._data_iter():
            self._recursively_expand(key=key, futures=futures)

        completed, incomplete = wait_for(futures.values())
        if incomplete:
            raise Exception(f"Some tasks did not complete: {incomplete}")
        for key in futures:
            self.data[key] = futures[key].result()

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

        Always returns True so that _is_leaf_node() is less gross.
        """

        if leaf_node and not leaf_node.WHAT == LeafNode.What.DUMP:
            return True

        directory = os.path.dirname(self.path)
        filename = f"{self.path}.json"
        os.makedirs(directory, exist_ok=True)
        with open(filename, "w") as f:
            json.dump(self.data, f, indent=4, sort_keys=True)

        # Build a reference to the file we just wrote.
        directory = os.path.basename(directory)
        filename = os.path.basename(filename)
        self.data = {"$ref": f"{directory}/{filename}"}

        return True

    def _is_leaf_node(self, when):

        for c in self.leaf_nodes:

            if c.comment or not c.match(string=self.traversal, when=when):
                continue

            if not c.children:
                return self._dump(c)

            self._log(f">>> Expand children of [{c.raw}]")
            Expander(
                logger=self.logger,
                path=os.path.dirname(self.path),
                data={os.path.basename(self.path): self.data},
                leaf_nodes=c.children,
            )._execute(indent=self.indent + 2, my_path_component=os.path.basename(self.path), traversal="")
            self._log(f"<<< Expand children of [{c.raw}]")

            return self._dump(c)

        return False

    def _log(self, string):
        self.logger.debug(" " * self.indent + string)

    def _recursively_expand(self, *, key, futures):

        if not (isinstance(self.data[key], dict) or isinstance(self.data[key], list)):
            return None

        path_component = str(key).replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")

        def launch_expansion():
            return Expander(
                logger=self.logger,
                path=os.path.join(self.path, path_component),
                data=self.data[key],
                leaf_nodes=self.leaf_nodes,
                thread_pool=self.thread_pool
            )._execute(indent=self.indent + 2, my_path_component=path_component, traversal=f"{self.traversal}/{key}")

        # This is naive.
        # A deeply nested json doc will use all threads before any get a chance
        # to start processing. We need to put the launches on a queue have the
        # pool fed from there.
        futures[key] = self.thread_pool.submit(launch_expansion)

        # self.data[key] = {"$ref": f"{self.my_path_component}/{path_component}.json"}
