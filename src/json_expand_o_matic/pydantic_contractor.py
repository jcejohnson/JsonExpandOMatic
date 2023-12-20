"""
Support for lazy loading into a pydantic model.
"""

from collections.abc import MutableMapping, MutableSequence
from typing import Any, ClassVar, Dict, Generic, List, Type, TypeVar, Union

from pydantic import Field, parse_obj_as  # type: ignore
from pydantic.generics import GenericModel as GenericPydanticBaseModel

from json_expand_o_matic.lazy_contractor import (
    ContractionProxy,
    DefaultContractionProxy,
    DefaultContractionProxyContext,
)

T = TypeVar("T")  # Any type.
KT = TypeVar("KT")  # Key type.
VT = TypeVar("VT")  # Value type.


class PydanticContractionProxyContext(DefaultContractionProxyContext):
    """
    Overrides _contract_now() to return a dict compatible with LazyBaseThing.
    """

    context_cache: ClassVar[Dict[int, "PydanticContractionProxyContext"]] = dict()

    def proxy(self) -> ContractionProxy:
        result = super().proxy()
        return result

    def _delayed_contraction(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        result = super()._delayed_contraction()
        return result

    def _contract_now(self):
        assert isinstance(self, PydanticContractionProxyContext)

        cid = id(self)
        PydanticContractionProxyContext.context_cache[cid] = self
        result = self.data | {"$ctx": cid}

        self._contract_now = super()._contract_now

        return result


class PydanticContractionProxy(DefaultContractionProxy):
    def __init__(self, *, callback):
        super().__init__(callback=callback)


class LazyBaseThing(GenericPydanticBaseModel, Generic[T]):
    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    ref: str = Field(alias="$ref")
    ctx: int = Field(alias="$ctx")

    _model_clazz: Type[T]
    _data: T = None  # type: ignore
    _container: Any = None  # type: ignore

    @property
    def data(self) -> T:
        if not self._data:
            assert self.ctx, (
                "Missing PydanticContractionProxyContext identifier. "
                "Did you forget to use PydanticContractionProxy* objects during contract()?"
            )
            context = PydanticContractionProxyContext.context_cache[self.ctx]
            raw_data = context._contract_now()
            raw_data = self._pre_parse_obj_as(context, raw_data)
            self._data = parse_obj_as(self._model_clazz, raw_data)
            self._post_parse_obj_as(context, raw_data)
        return self._data

    def _pre_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return raw_data

    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return

    def __getattr__(self, name):
        return object.__getattribute__(self.data, name)


class LazyBaseModel(LazyBaseThing[T], Generic[T]):
    #

    def _pre_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return raw_data

    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        # Replace the lazy model instance in the container.
        if self._container is not None:
            self._container[context.parent_key] = self._data
        return


class LazyDict(LazyBaseThing[MutableMapping[KT, VT]], Generic[KT, VT]):
    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        for value in self._data.values():
            if isinstance(value, LazyBaseThing):
                value._container = self
        return

    def __iter__(self):
        yield from self.data

    def __delitem__(self, key):
        return self.data.__delitem__(key)

    def __getitem__(self, index):
        return self.data.__getitem__(index)

    def __len__(self):
        return self.data.__len__()

    def __setitem__(self, key, value):
        return self.data.__setitem__(key, value)


class LazyList(LazyBaseThing[MutableSequence[T]], Generic[T]):
    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        for value in self._data:
            if isinstance(value, LazyBaseThing):
                value._container = self
        return
