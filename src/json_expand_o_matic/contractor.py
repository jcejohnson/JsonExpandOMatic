import json
import os
from functools import partial
from typing import Any, Dict, List, Union
from urllib.parse import urlparse

from proxytypes import LazyProxy  # type: ignore


class ContractionProxy(LazyProxy):
    def __init__(self, *, function):
        super().__init__(callback=function)


class Contractor:
    def __init__(self, *, logger, path, root_element, **options):
        self.logger = logger
        self.path = path
        self.root_element = root_element

        self.ref_key = options.get("ref_key", "$ref")
        self.eager = not options.get("lazy", False)

    def execute(self) -> Union[List[Any], Dict[Any, Any]]:
        root_data = self._slurp(self.path, f"{self.root_element}.json", parent=None)
        result = self._contract(path=[self.path], data=root_data)
        assert not isinstance(result, ContractionProxy)
        return result

    def _contract(self, *, path, data) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        assert not isinstance(data, ContractionProxy)

        if isinstance(data, list):
            for k, v in enumerate(data):
                data[k] = self._contract(path=path, data=v)

        elif isinstance(data, dict):
            for k, v in data.items():
                if self._something_to_follow(k, v):
                    if self.eager:
                        return self._recursively_contract(path=path, v=v, data=data)

                    return ContractionProxy(
                        function=partial(self._recursively_contract, path=path, v=v, data=data),
                    )

                data[k] = self._contract(path=path, data=v)

        return data

    def _something_to_follow(self, k, v) -> bool:
        if k != self.ref_key:
            return False

        url_details = urlparse(v)
        return not (url_details.scheme or url_details.fragment)

    def _recursively_contract(self, path, v, data) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        data = self._slurp(*path, v, parent=data)
        return self._contract(path=path + [os.path.dirname(v)], data=data)

    def _slurp(self, *args, parent) -> Union[List[Any], Dict[Any, Any]]:
        with open(os.path.join(*args)) as f:
            return json.load(f)
