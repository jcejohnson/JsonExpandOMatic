import json
import os

from .leaf_node import LeafNode


class Expander:
    def __init__(self, *, logger, path, data, leaf_nodes):

        assert isinstance(data, dict) or isinstance(data, list)

        self.logger = logger
        self.path = path
        self.data = data
        self.leaf_nodes = leaf_nodes

    def execute(self):
        return self._execute(indent=0, my_path_component=os.path.basename(self.path), traversal="")

    def _execute(self, traversal, indent, my_path_component):
        """Recursive expansion method.

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

        if self._is_leaf_node():
            return self.data

        if not os.path.exists(self.path):
            os.mkdir(self.path)

        for key in self._data_iter():
            self._recursively_expand(key=key)

        try:
            os.rmdir(self.path)
        except Exception:
            pass

        if not traversal:
            return self.data

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

        if leaf_node and not leaf_node.WHAT == LeafNode.What.DUMP:
            return self.data

        filename = f"{self.path}.json"
        with open(filename, "w") as f:
            json.dump(self.data, f, indent=4, sort_keys=True)

        # Build a reference to the file we just wrote.
        directory = os.path.basename(os.path.dirname(self.path))
        filename = os.path.basename(filename)
        return {"$ref": f"{directory}/{filename}"}

    def _log(self, string):
        self.logger.debug(" " * self.indent + string)

    def _is_leaf_node(self):

        for c in self.leaf_nodes:
            if not c.match(self.traversal):
                continue

            if not c.children:
                return self._dump(c)

            self._log(">>> Expander")
            Expander(
                logger=self.logger,
                path=os.path.dirname(self.path),
                data={os.path.basename(self.path): self.data},
                leaf_nodes=c.children,
            )._execute(indent=self.indent + 2, my_path_component=os.path.basename(self.path), traversal="")
            self._log("<<< Expander")

            return self._dump(c)

        return None

    def _recursively_expand(self, *, key):

        if not (isinstance(self.data[key], dict) or isinstance(self.data[key], list)):
            return

        path_component = str(key).replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")

        r = Expander(
            logger=self.logger,
            path=os.path.join(self.path, path_component),
            data=self.data[key],
            leaf_nodes=self.leaf_nodes,
        )._execute(indent=self.indent + 2, my_path_component=path_component, traversal=f"{self.traversal}/{key}")

        self.data[key] = {"$ref": f"{self.my_path_component}/{path_component}.json"}

        return r
