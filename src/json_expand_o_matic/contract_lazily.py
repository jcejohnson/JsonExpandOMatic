import abc
import copy
import json
from typing import Any, Dict, List, Optional, Type, Union

import pytest

from json_expand_o_matic.expand_o_matic import JsonExpandOMatic
from pydantic import BaseModel, Field
from pydantic.class_validators import root_validator


class LazyMaker:
    """
    LazyMaker is designed to work with pydantic models and defer loading data until it is accessed.

    ContractionProxy is similar but is designed for the "dict of dicts" usecase.

    See the test case(s) for usage examples.
    """

    class LazyProxyBase(BaseModel):
        pass

    class LazyLoaderBase(abc.ABC):
        @abc.abstractmethod
        def load(self, name: str, data_type: type, reference: str) -> Any:
            ...

    def __init__(self, loader: Type[LazyLoaderBase], ref_key: str = "$ref") -> None:
        self._loader = loader()
        self._ref_key = ref_key
        self._actual_models = {}
        self._all_models = {}
        self._lazy_models = {}

    def __getitem__(self, class_name: str) -> type:
        v = self._all_models.get(class_name)
        if v or class_name.endswith("LazyModel") or class_name.endswith("ActualModel"):
            return v
        return self._actual_models.get(f"{class_name}ActualModel")

    def __call__(lazy_self, clazz):
        """ """

        class LazyProxy(LazyMaker.LazyProxyBase):
            class Config:
                underscore_attrs_are_private: bool = True

            ref_: str  # PrivateAttr does not support alias and this isn't really a private attribute anyway.
            _data: Optional[clazz] = None  # The actual model after it has been lazily loaded.
            _type: type = clazz  # The datatype of the actual model.

            @root_validator(pre=True, allow_reuse=True)
            @classmethod
            def lazy_proxy_root_validator(cls, values):
                if lazy_self._ref_key in values:
                    values["ref_"] = values.pop(lazy_self._ref_key)
                return values

            def __getattr__(self, name):
                """
                Lazily load the actual model on first reference and delegate all attribute requests to it.
                """
                if not self._data:
                    self._data = lazy_self._loader.load(name=name, data_type=self._type, reference=self.ref_)
                return getattr(self._data, name)

        lazy_self._all_models[f"{clazz.__name__}LazyModel"] = lazy_self._lazy_models[
            f"{clazz.__name__}LazyModel"
        ] = LazyProxy
        lazy_self._all_models[f"{clazz.__name__}ActualModel"] = lazy_self._actual_models[
            f"{clazz.__name__}ActualModel"
        ] = clazz

        clazz.LAZY = Union[LazyProxy, clazz]
        return clazz
