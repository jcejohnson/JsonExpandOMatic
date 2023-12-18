import json
import os
from functools import partial
from typing import Any, Dict, List, Union
from urllib.parse import urlparse

from .lazy_contractor import (
    ContractionProxy,
    ContractionProxyContext,
    ContractionProxyState,
    DefaultContractionProxy,
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

    def __init__(self, *, logger, path, root_element, **options):
        self.logger = logger
        self.path = path
        self.root_element = root_element

        self.ref_key = options.get("ref_key", "$ref")
        self.eager = not options.get("lazy", False)
        self.contraction_proxy_class = options.get("contraction_proxy_class", DefaultContractionProxy)

        if self.eager:
            self._recursively_contract = self._eager_contraction
        else:
            self._recursively_contract = self._lazy_contraction

    def execute(self) -> Union[List[Any], Dict[Any, Any]]:
        root_data = self._slurp(self.path, f"{self.root_element}.json", parent=None)
        result = self._contract(path=[self.path], data=root_data, parent=None, parent_key=None)
        assert not isinstance(result, ContractionProxy)
        return result

    def _contract(self, *, path, data, parent, parent_key) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
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
        self, *, path, value, data, parent, parent_key
    ) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        data = self._slurp(*path, value, parent=data)
        return self._contract(path=path + [os.path.dirname(value)], data=data, parent=parent, parent_key=parent_key)

    def _lazy_contraction(self, *, path, data, parent, parent_key, value):
        context = ContractionProxyContext(path=path, value=value, data=data, parent=parent, parent_key=parent_key)
        callback = partial(self._lazy_delayed_contraction, context=context)
        proxy = self.contraction_proxy_class(callback=callback)
        return proxy

    def _lazy_delayed_contraction(
        self, *, context: ContractionProxyContext
    ) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        assert context.state == ContractionProxyState.waiting
        context.state = ContractionProxyState.loading
        lazy_data = self._eager_contraction(
            data=context.data,
            parent_key=context.parent_key,
            parent=context.parent,
            path=context.path,
            value=context.value,
        )
        # Replace the ContractionProxy instance with the lazy-loaded data.
        context.parent[context.parent_key] = lazy_data
        context.state = ContractionProxyState.ready
        assert not isinstance(lazy_data, ContractionProxy)
        return lazy_data

    def _slurp(self, *args, parent) -> Union[List[Any], Dict[Any, Any]]:
        with open(os.path.join(*args)) as f:
            return json.load(f)

    def _something_to_follow(self, *, key, value) -> bool:
        if key != self.ref_key:
            return False

        url_details = urlparse(value)
        return not (url_details.scheme or url_details.fragment)
