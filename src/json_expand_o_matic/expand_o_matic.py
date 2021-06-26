import json
import logging
import os
from urllib.parse import urlparse

from .leaf_node import LeafNode


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

    def expand(self, data, root_element="root", preserve=True, leaf_nodes=[], **expander_options):
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

        from .expander import Expander

        expander = Expander(
            logger=self.logger,
            path=self.path,
            data={root_element: data},
            leaf_nodes=LeafNode.construct(leaf_nodes),
            **expander_options,
        )
        result = expander.execute()
        self.hashcodes = expander.hashcodes

        return result

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
