import inspect
import json
import os
from abc import ABC, abstractmethod
from collections import UserDict, UserList
from collections.abc import MutableMapping
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generic,
    Iterator,
    List,
    MutableSequence,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseModel as PydanticBaseModel  # type: ignore
from pydantic import Field, create_model, parse_obj_as, root_validator
from pydantic.generics import GenericModel  # type: ignore
from pydantic.generics import _assigned_parameters as GenericModelDetails  # noqa : N812

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class LazyParserMixin(ABC):
    """
    User LazyParserMixin.parse_lazy() as a replacement for PydanticBaseModel.parse_file().
    This will parse a single json file containing all of your data or a "root.json" file with
    a $ref key pointing to the next chunk.
    """

    @classmethod
    def parse_lazy(cls, path: Union[str, Path], lazy_type: Optional[Type] = None):
        with open(path) as f:
            data = json.load(f)

        if lazy_type is None:
            lazy_type = cls
            assert lazy_type is not None

        if (
            PydanticBaseModel in inspect.getmro(lazy_type)
            and "__root__" in cast(PydanticBaseModel, lazy_type).__fields__
        ):
            # __root__ cannot be mixed with other fields
            model = parse_obj_as(lazy_type, data)
            return model

        if LazyBaseModel not in inspect.getmro(lazy_type):
            lazy_type = create_model(lazy_type.__name__, __base__=(lazy_type, LazyBaseModel))
            assert lazy_type is not None

        data.update({"$ref": os.path.basename(path), "$base": os.path.dirname(path), "$type": lazy_type})

        assert issubclass(lazy_type, LazyBaseModel)

        for key, value in data.items():
            if isinstance(value, MutableMapping) and "$ref" in value:
                value["$base"] = os.path.dirname(path)
                value["$type"] = lazy_type.__fields__[key].type_

        model = parse_obj_as(lazy_type, data)

        return model


class LazyBaseModel(PydanticBaseModel, LazyParserMixin):
    """
    Maintains the fields necessary for lazy loading.

    LazyBaseModel can be used as a replacement for PydanticBaseModel if you know
    you will have lazy-loadable data.
    """

    lazy_ref: str = Field(..., alias="$ref")
    lazy_base: str = Field(..., alias="$base")
    lazy_type: Any = Field(..., alias="$type")
    lazy_data: Optional[PydanticBaseModel] = Field(default=None, alias="$data")

    def __getattr__(self, item) -> Any:
        """
        When a LazyBaseModel represents a dict.
        """

        if self.lazy_data:
            # Use object.__getattribute__ because lazy_data may itself be a LazyDict
            # which could cause infinite recursion.
            return object.__getattribute__(self.lazy_data, item)

        path = os.path.join(self.lazy_base, self.lazy_ref)
        self.lazy_data = self.parse_lazy(path, lazy_type=self.lazy_type)
        return object.__getattribute__(self.lazy_data, item)

    def __getitem__(self, item) -> Any:
        """
        When a LazyBaseModel represents a list.
        """

        if self.lazy_data:
            return cast(MutableSequence, self.lazy_data).__getitem__(item)

        path = os.path.join(self.lazy_base, self.lazy_ref)
        self.lazy_data = self.parse_lazy(path, lazy_type=self.lazy_type)
        return cast(MutableSequence, self.lazy_data)[item]

    @root_validator(pre=True)
    @classmethod
    def lazy_base_model_root_validator(cls, values):
        """
        Insert $base and $type into any elements having a $ref key.
        This gives parse_lazy() everything it needs to load the chunk.
        """
        for key, value in values.items():
            if isinstance(value, MutableMapping) and "$ref" in value:
                d = os.path.dirname(values["$ref"])
                value["$base"] = os.path.join(values["$base"], d) if d else values["$base"]
                value["$type"] = cls.__fields__[key].type_

        return values


class LazyContainer(ABC):
    """
    Common functionality for LazyDict and LazyList.
    """

    @abstractmethod
    def __lazy_init_root__(self):
        pass

    @abstractmethod
    def __lazy_addto_root__(self, key, obj):
        pass

    @abstractmethod
    def __lazy_raw_data_iterator__(self, data) -> Iterator:
        pass

    def __contains__(self, item) -> bool:
        data = self.data  # type: ignore  # Provided by subclasses.
        return data.__contains__(item) if data else False

    def __getitem__(self, item):
        # Let it raise an error if self.data is None
        return self.data[item]  # type: ignore

    def __iter__(self):
        # Let it raise an error if self.data is None
        return iter(self.data)  # type: ignore

    def __lazy_data__(self) -> Any:
        container = self.__root__  # type: ignore

        if container is None:
            return None

        if not isinstance(container, LazyBaseModel):
            return container

        assert isinstance(self, PydanticBaseModel)
        value_lazy_type = GenericModelDetails[type(self)][ValueT]

        path = os.path.join(container.lazy_base, container.lazy_ref)

        with open(path) as f:
            data = json.load(f)

        self.__lazy_init_root__()

        for key, value in self.__lazy_raw_data_iterator__(data):
            if "$ref" in value:
                obj = parse_obj_as(
                    LazyBaseModel,
                    {
                        "$ref": value["$ref"],
                        "$base": os.path.dirname(path),
                        "$type": value_lazy_type,
                    },
                )
            else:
                obj = parse_obj_as(value.lazy_type, value)

            self.__lazy_addto_root__(key, obj)

        return self.__root__  # type: ignore


# -----------------v must come first so that its __*__ methods are used.
class LazyDict(LazyContainer, GenericModel, Generic[KeyT, ValueT], UserDict[KeyT, ValueT]):
    """
    Replacement for Dict[] that will lazy-load a json chunk when accessed.
    """

    # See https://docs.pydantic.dev/usage/models/#custom-root-types

    __root__: Union[LazyBaseModel, Dict[KeyT, Union[LazyBaseModel, ValueT]]]

    # LazyContainer implementation.

    def __lazy_init_root__(self):
        self.__root__ = parse_obj_as(Dict[KeyT, Union[LazyBaseModel, ValueT]], dict())

    def __lazy_addto_root__(self, key, obj):
        cast(dict, self.__root__)[key] = obj

    def __lazy_raw_data_iterator__(self, data):
        for key, value in data.items():
            yield key, value

    @property
    def data(self) -> dict:  # Union[None, Dict[KeyT, Union[LazyBaseModel, ValueT]]]:
        return self.__lazy_data__()

    @data.setter
    def data(self, value):
        raise Exception("Setting the internal data is not permitted.")


# -----------------v must come first so that its __*__ methods are used.
class LazyList(LazyContainer, GenericModel, Generic[ValueT], UserList[ValueT]):
    """
    Replacement for List[] that will lazy-load a json chunk when accessed.
    """

    # See https://docs.pydantic.dev/usage/models/#custom-root-types

    __root__: Union[LazyBaseModel, List[Union[LazyBaseModel, ValueT]]]

    # LazyContainer implementation.

    def __lazy_init_root__(self):
        self.__root__ = parse_obj_as(List[Union[LazyBaseModel, ValueT]], list())

    def __lazy_addto_root__(self, key, obj):
        self.__root__.append(obj)

    def __lazy_raw_data_iterator__(self, data):
        for key, value in enumerate(data):
            yield key, value

    @property
    def data(self) -> list:  # Union[None, List[Union[LazyBaseModel, ValueT]]]:
        return self.__lazy_data__()

    @data.setter
    def data(self, value):
        raise Exception("Setting the internal data is not permitted.")
