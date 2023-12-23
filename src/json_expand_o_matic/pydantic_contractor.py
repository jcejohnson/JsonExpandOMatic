"""
Support for lazy loading into a pydantic model.
"""

from collections.abc import MutableMapping, MutableSequence
from typing import Any, ClassVar, Dict, Generic, List, Type, TypeVar, Union

from peak.util.proxies import LazyWrapper
from pydantic import Field, parse_obj_as  # type: ignore
from pydantic.generics import GenericModel as GenericPydanticBaseModel
from pydantic.validators import _VALIDATORS

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


# LazyPydantic*


class LazyPydanticBaseThing(GenericPydanticBaseModel, Generic[T]):
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


class LazyPydanticBaseModel(LazyPydanticBaseThing[T], Generic[T]):
    #

    def _pre_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return raw_data

    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        # Replace the lazy model instance in the container.
        if self._container is not None:
            self._container[context.parent_key] = self._data
        return


class LazyPydanticDict(LazyPydanticBaseThing[MutableMapping[KT, VT]], Generic[KT, VT]):
    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        for value in self._data.values():
            if isinstance(value, LazyPydanticBaseThing):
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


class LazyPydanticList(LazyPydanticBaseThing[MutableSequence[T]], Generic[T]):
    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        for value in self._data:
            if isinstance(value, LazyPydanticBaseThing):
                value._container = self
        return


# Lazy*
# Using these requires Config.arbitrary_types_allowed=True


class LazyBaseThing(LazyWrapper, Generic[T]):  # GenericPydanticBaseModel, Generic[T]):
    # This might let me use LazyProxy with its more thorough __getattr__ and friends.
    # Requires lazy_base_thing_validator
    # Neither this nor subclasses can be a @dataclass (I think).

    ref: str
    ctx: int = None  # type: ignore
    root: str = None  # type: ignore

    _model_clazz: Type[T] = None  # type: ignore
    _data: T = None  # type: ignore
    _container: Any = None  # type: ignore

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)
        # We cannot use this callback because it has already been used.
        # We need to create another callback that behaves like `data()`
        context = PydanticContractionProxyContext.context_cache[self.ctx]
        LazyWrapper.__init__(self, func=context.callback)

    """
    @property
    def data(self) -> T:
        if not self._data:
            assert self.ctx or self.root, (
                "Missing PydanticContractionProxyContext identifier. "
                "Did you forget to use PydanticContractionProxy* objects during contract()?"
            )
            if self.ctx:
                context = PydanticContractionProxyContext.context_cache[self.ctx]
                raw_data = context._contract_now()
                raw_data = self._pre_parse_obj_as(context, raw_data)
                self._data = parse_obj_as(self._model_clazz, raw_data)
                self._post_parse_obj_as(context, raw_data)
            elif self.root:
                path = Path(self.root, self.ref)
                with open(path) as f:
                    data = json.load(f)
                assert self._model_clazz
                assert issubclass(self._model_clazz, PydanticBaseModel)
                # This will fail unless we iterate through attributes that are
                # list/dict and replace `$ref`` with `ref`` _and_ add `root`.
                # I'm not sure this is worth pursuing just to leverage LazyProxy.
                self._data = cast(T, self._model_clazz.parse_obj(data))

        return self._data

    def _pre_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return raw_data

    def _post_parse_obj_as(self, context: PydanticContractionProxyContext, raw_data):
        return

    def __getattr__(self, name):
        return object.__getattribute__(self.data, name)
    """


def lazy_base_thing_validator(v: Any, **kwargs) -> Any:
    if issubclass(kwargs["field"].type_, LazyBaseThing):
        v = {key[1:] if key.startswith("$") else key: value for key, value in v.items()}
        v = kwargs["field"].type_(**v)
        return v
    from pydantic.errors import ClassError

    raise ClassError()


_VALIDATORS.append((LazyBaseThing, [lazy_base_thing_validator]))


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
