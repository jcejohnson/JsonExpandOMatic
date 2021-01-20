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

    def expand(self, data, root_element="root", preserve=True, leaf_nodes=[]):
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

        Returns:
        --------
        dict
            {root_element: data} where `data` is the original data mutated
            to include jsonref elements for its list and dict elements.
        """
        if preserve:
            data = json.loads(json.dumps(data))

        self.leaf_nodes = [re.compile(p) for p in leaf_nodes] if leaf_nodes else []

        r = self._expand(path=self.path, key=root_element, data={root_element: data}, ref=".")

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

    def _expand(self, *, path, key, data, ref, indent=0, traversal=""):
        """Recursive expansion method.

        Parameters
        ----------
        path : str
            Fully qualified filesystem path where the data will be written.
        key : str
            data[key] is the element this iteration will do work on.
            ${key}.json is created at the current ${path}
        data : dict or list
            The data to be expanded.
        ref : str
            The jsonref path from `data`s parent to `data`.
            When this iteration of _expand() returns, the file written at
            the then-current ${path} will contain a jsonref value of
            ${ref}/${key}.json where ref and key are _this_ iteration's
            values.
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
        self.logger.debug(" " * indent + f"path [{path}] key [{key}] ref [{ref}] traversal [{traversal}]")

        if [p for p in self.leaf_nodes if p.match(traversal)]:
            return data

        assert isinstance(data, dict) or isinstance(data, list)

        if not isinstance(data[key], dict) and not isinstance(data[key], list):
            return data
        if not data[key]:
            self.logger.debug(" " * indent + f"data[{key}] is falsy")
            return data

        if not os.path.exists(path):
            os.mkdir(path)

        # FIXME: Do this with a regex
        filename_key = str(key).replace(":", "_").replace("/", "_").replace("\\", "_")

        if isinstance(data[key], list):
            self.logger.debug(" " * indent + ">> IS A LIST <<")
            for k, v in enumerate(data[key]):
                self._expand(
                    path=os.path.join(path, str(filename_key)),
                    key=k,
                    data=data[key],
                    ref=f"{ref}/{key}",
                    indent=indent + 2,
                    traversal=f"{traversal}/{ref}/{key}",
                )

        elif isinstance(data[key], dict):
            self.logger.debug(" " * indent + ">> IS A DICT <<")

            keys = sorted(data[key].keys())
            for k in keys:
                # v = data[key][k]
                self.logger.debug(" " * indent + k)
                self._expand(
                    path=os.path.join(path, str(filename_key)),
                    key=k,
                    data=data[key],
                    ref=key,
                    indent=indent + 2,
                    traversal=f"{traversal}/{key}",
                )

            with open(f"{path}/{filename_key}.json", "w") as f:
                self.logger.debug(f"Writing [{path}/{filename_key}.json] for [{traversal}]")
                json.dump(data[key], f, indent=4, sort_keys=True)

            data[key] = {"$ref": f"{ref}/{filename_key}.json"}

        try:
            os.rmdir(path)
        except Exception:
            pass

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

    def _something_to_follow(self, k, v):

        if k != "$ref":
            return False

        url_details = urlparse(v)
        return not (url_details.scheme or url_details.fragment)

    def _slurp(self, *args):
        with open(os.path.join(*args)) as f:
            return json.load(f)
