import json
import os
from functools import partial
from urllib.parse import urlparse

from .contraction_proxy import ContractionProxy


class Contractor:
    def __init__(self, *, logger, path, root_element, **options):
        self.logger = logger
        self.path = path
        self.root_element = root_element

        self.ref_key = options.get("ref_key", "$ref")

        self.lazy = options.get("lazy", False)
        self.lazy_proxy_factory = options.get(
            "lazy_proxy_factory", lambda _, partial_func: ContractionProxy(partial_func)
        )
        # lazy_proxy_factory is a function that takes a type (dict or list) and a partial function.
        # The factory should return a ContractionProxy instance or something that behaves like ContractionProxy.

        if self.lazy:
            dict_contractor = self._contract_dict
            self._contract_dict = lambda path, data: self.lazy_proxy_factory(
                dict, partial(dict_contractor, path=path, data=data)
            )
            list_contractor = self._contract_list
            self._contract_list = lambda path, data: self.lazy_proxy_factory(
                list, partial(list_contractor, path=path, data=data)
            )

    def execute(self):
        return self._contract(path=[self.path], data=self._slurp(self.path, f"{self.root_element}.json"))

    def _contract(self, *, path, data):
        if isinstance(data, dict):
            return self._contract_dict(path=path, data=data)

        if isinstance(data, list):
            return self._contract_list(path=path, data=data)

        return data

    def _contract_dict(self, *, path, data):
        for k, v in data.items():
            if self._something_to_follow(k, v):
                return self._contract(
                    path=path + [os.path.dirname(v)],
                    data=self._slurp(*path, v),
                )
            data[k] = self._contract(path=path, data=v)
        return data

    def _contract_list(self, path, data):
        for k, v in enumerate(data):
            data[k] = self._contract(path=path, data=v)
        return data

    def _something_to_follow(self, k, v):
        if k != self.ref_key:
            return False

        url_details = urlparse(v)
        return not (url_details.scheme or url_details.fragment)

    def _slurp(self, *args):
        with open(os.path.join(*args)) as f:
            return json.load(f)
