import json
import os
from logging import Logger
from typing import Any, Dict, List, Type, Union
from urllib.parse import urlparse

from .lazy_contractor import (
    ContractionProxy,
    ContractionProxyContext,
    DefaultContractionProxy,
    DefaultContractionProxyContext,
)

"""
from peak.util.proxies import get_callback  # type: ignore[import-untyped]

class ContractionProxyJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ContractionProxy):
            callback = get_callback(o)
            data = callback.keywords["data"]
            return data
        return o


def json_dumps(*args, **kwargs):
    if "cls" not in kwargs:
        return json.dumps(*args, cls=ContractionProxyJSONEncoder, **kwargs)
    return json.dumps(*args, **kwargs)
"""


class Contractor:
    """ """

    def __init__(
        self,
        *,
        logger: Logger,
        path: str,
        root_element: str,
        lazy: bool = False,
        ref_key: str = "$ref",
        contraction_context_class: Type[ContractionProxyContext] = DefaultContractionProxyContext,
        contraction_proxy_class: Type[ContractionProxy] = DefaultContractionProxy,
        **options,
    ):
        self.logger = logger
        self.path = path
        self.ref_key = ref_key
        self.root_element = root_element

        self.lazy = lazy
        self.contraction_context_class = contraction_context_class
        self.contraction_proxy_class = contraction_proxy_class

        if lazy:
            assert self.contraction_context_class
            assert self.contraction_proxy_class
            self._recursively_contract = self._lazy_contraction
        else:
            self._recursively_contract = self._eager_contraction

    def execute(self) -> Union[List[Any], Dict[Any, Any]]:
        root_data = self._slurp(self.path, f"{self.root_element}.json", parent=None)
        result = self._contract(path=[self.path], data=root_data, parent=None, parent_key=None)
        assert not isinstance(result, ContractionProxy)
        return result

    def _contract(
        self, *, path: List[str], data, parent, parent_key
    ) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        assert not isinstance(data, ContractionProxy)

        if isinstance(data, list):
            for k, v in enumerate(data):
                data[k] = self._contract(path=path, data=v, parent=data, parent_key=k)

        elif isinstance(data, dict):
            for k, v in data.items():
                if self._something_to_follow(key=k, value=v):
                    return self._recursively_contract(
                        path=path, data=data, parent=parent, parent_key=parent_key, value=v
                    )

                data[k] = self._contract(path=path, data=v, parent=data, parent_key=k)

        return data

    def _eager_contraction(
        self, *, path: List[str], value, data, parent, parent_key
    ) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        data = self._slurp(*path, value, parent=data)
        return self._contract(path=path + [os.path.dirname(value)], data=data, parent=parent, parent_key=parent_key)

    def _lazy_contraction(
        self, *, path: List[str], value, data, parent, parent_key
    ) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        context = self.contraction_context_class(
            contractor=self,
            path=path,
            value=value,
            data=data,
            parent=parent,
            parent_key=parent_key,
            contraction_proxy_class=self.contraction_proxy_class,
        )
        # Request a proxy object that will delegate to _eager_contraction() when
        # any attributes, methods, etc. are requested.
        proxy = context.proxy()
        return proxy

    def _slurp(self, *args, parent) -> Union[List[Any], Dict[Any, Any]]:
        with open(os.path.join(*args)) as f:
            return json.load(f)

    def _something_to_follow(self, *, key, value) -> bool:
        if key != self.ref_key:
            return False

        url_details = urlparse(value)
        return not (url_details.scheme or url_details.fragment)
