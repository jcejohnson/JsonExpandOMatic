import json
import logging
import os
import re
from urllib.parse import urlparse


class JsonExpandOMatic:
    def __init__(self, *, path, logger=logging.getLogger(__name__)):
        """Expand a dict into a collection of subdirectories and json files.

        Parameters
        ----------
        path : str
            Target directory where expand will write the expanded json data
            and/or where contract will find the expanded data to be loaded.
        """
        self.path = os.path.abspath(path)
        self.logger = logger

    def expand(self, data, root_element="root", preserve=True, leaf_nodes=[], path_json=False):
        """Expand a dict into a collection of subdirectories and json files.

        Creates:
        - {self.path}/{root_element}.json
        - {self.path}/{root_element}/...

        Parameters
        ----------
        data : dict or list
            The data to be expanded.
        root_element : str
            Name of the element to "wrap around" the data we expand.
        preserve : bool
            If true, make a deep copy of `data` so that our operation does not
            change it.
        leaf_nodes : list
            A list of regular expressions.
            Recursion stops if the current path into the data matches an item
            in this list.
        path_json : bool
            If set, f"{self.path}.json" will be created.
            This may sound like a good idea but it is redundant and confusing.
            We already have one "extra" layer over our data (root_element) and
            path_json=True is just adding another. It's only worth enabling to
            see why you don't want to enable it.

        Returns:
        --------
        dict
            {root_element: data} where `data` is the original data mutated
            to include jsonref elements for its list and dict elements.
        """
        if preserve:
            data = json.loads(json.dumps(data))

        self._path_json = path_json

        self._compile_regexs(leaf_nodes)

        r = self._expand(path=self.path, data={root_element: data}, my_path_component=os.path.basename(self.path))

        # Cleanup before leaving.
        self.leaf_nodes = None

        return r

    def contract(self, root_element="root"):
        """Contract (un-expand) the results of `expand()` into a dict.

        Loads:
        - {self.path}/{root_element}.json
        - {self.path}/{root_element}/...

        Parameters
        ----------
        root_element : str
            Name of the element to "wraped around" the data we expanded
            previously. This will not be included in the return value.

        Returns:
        --------
        dict or list
            The data that was originally expanded.
        """
        return self._contract(path=[self.path], data=self._slurp(self.path, f"{root_element}.json"))

    ########################################
    # primary implementations

    def _expand(self, *, path, data, indent=0, traversal="", my_path_component=None):
        """Recursive expansion method.

        Parameters
        ----------
        path : str
            Fully qualified filesystem path where the data will be written.
        data : dict or list
            The data to be expanded.
        indent : int
            Used to indent log messages so that we can see the data tree.
        traversal : string
            A '/' separated path into the json doc.
            This is ${path} with self.path removed & is what we match against
            the self.leaf_nodes regular expressions.

        Returns:
        --------
        dict
            data
        """
        self.logger.debug(" " * indent + f"path [{path}] traversal [{traversal}]")

        assert isinstance(data, dict) or isinstance(data, list)

        if self._pluck_leaf_node(path=path, data=data, indent=indent, traversal=traversal):
            return data

        if not os.path.exists(path):
            os.mkdir(path)

        context = {
            "path": path,
            "data": data,
            "indent": indent,
            "traversal": traversal,
            "my_path_component": my_path_component,
        }

        if isinstance(data, dict):
            for key in sorted(data.keys()):
                self._recursively_expand(key=key, **context)

        elif isinstance(data, list):
            for key, _ in enumerate(data):
                self._recursively_expand(key=key, **context)

        try:
            os.rmdir(path)
        except Exception:
            pass

        if not traversal and not self._path_json:
            return data

        with open(f"{path}.json", "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

        return data

    def _contract(self, *, path, data):

        if isinstance(data, list):
            for k, v in enumerate(data):
                data[k] = self._contract(path=path, data=v)

        elif isinstance(data, dict):

            for k, v in data.items():
                if self._something_to_follow(k, v):
                    return self._contract(path=path + [os.path.dirname(v)], data=self._slurp(*path, v))
                data[k] = self._contract(path=path, data=v)

        return data

    ########################################
    # _expand support

    def _compile_regexs(self, leaf_nodes):

        self.leaf_nodes = []
        self.other_things = {}
        if not leaf_nodes:
            return

        for p in leaf_nodes:
            if isinstance(p, str):
                self.leaf_nodes.append(re.compile(p))
            elif isinstance(p, dict):
                for x, y in p.items():
                    c = re.compile(x)
                    self.leaf_nodes.append(c)
                    self.other_things[c] = y
            else:
                raise Exception(f"Illegal type for leaf-node: {type(p)} : {p}")

    def _pluck_leaf_node(self, *, path, data, indent, traversal):

        for c in self.leaf_nodes:
            if not c.match(traversal):
                continue

            with open(f"{path}.json", "w") as f:
                json.dump(data, f, indent=4, sort_keys=True)

            if c in self.other_things:
                JsonExpandOMatic(path=os.path.dirname(path)).expand(
                    data, preserve=False, leaf_nodes=self.other_things[c], root_element=os.path.basename(path)
                )

            return data

    def _recursively_expand(self, *, path, data, indent, traversal, my_path_component, key):

        if not (isinstance(data[key], dict) or isinstance(data[key], list)):
            return

        path_component = str(key).replace(":", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")
        self._expand(
            path=os.path.join(path, path_component),
            data=data[key],
            indent=indent + 2,
            traversal=f"{traversal}/{key}",
            my_path_component=path_component,
        )

        data[key] = {"$ref": f"{my_path_component}/{path_component}.json"}

    ########################################
    # _contract support

    def _something_to_follow(self, k, v):

        if k != "$ref":
            return False

        url_details = urlparse(v)
        return not (url_details.scheme or url_details.fragment)

    def _slurp(self, *args):
        with open(os.path.join(*args)) as f:
            return json.load(f)
