import inspect
import json
import os
from abc import ABC, abstractmethod

from collections import UserDict, UserList
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Dict, Generic, List, Type, TypeVar, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, parse_obj_as, root_validator, create_model
from pydantic.generics import GenericModel
from pydantic.generics import _assigned_parameters as GenericModelDetails

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


class LazyParserMixin(ABC):
    """
    User LazyParserMixin.parse_lazy() as a replacement for PydanticBaseModel.parse_file().
    This will parse a single json file containing all of your data or a "root.json" file with
    a $ref key pointing to the next chunk.
    """

    @classmethod
    def parse_lazy(cls, path: Union[str, Path], lazy_type: Type = None):
        with open(path) as f:
            data = json.load(f)

        if not lazy_type:
            lazy_type = cls

        if PydanticBaseModel in inspect.getmro(lazy_type) and "__root__" in lazy_type.__fields__:
            # __root__ cannot be mixed with other fields
            model = parse_obj_as(lazy_type, data)
            return model

        if LazyBaseModel not in inspect.getmro(lazy_type):
            lazy_type = create_model(lazy_type.__name__, __base__=(lazy_type, LazyBaseModel))

        data.update({"$ref": os.path.basename(path), "$base": os.path.dirname(path), "$type": lazy_type})

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
    lazy_data: PydanticBaseModel = Field(default=None, alias="$data")

    def __getattr__(self, item):
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

    def __getitem__(self, item):
        """
        When a LazyBaseModel represents a list.
        """

        if self.lazy_data:
            return self.lazy_data[item]

        path = os.path.join(self.lazy_base, self.lazy_ref)
        self.lazy_data = self.parse_lazy(path, lazy_type=self.lazy_type)
        return self.lazy_data[item]

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
    def __lazy_raw_data_iterator__(self, data):
        pass

    def __lazy_data__(self):
        if self.__root__ is None:
            return None

        if not isinstance(self.__root__, LazyBaseModel):
            return self.__root__

        value_lazy_type = GenericModelDetails[type(self)][ValueT]

        path = os.path.join(self.__root__.lazy_base, self.__root__.lazy_ref)

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

        return self.__root__


class LazyDict(GenericModel, Generic[KeyT, ValueT], UserDict, LazyContainer):
    """
    Replacement for Dict[] that will lazy-load a json chunk when accessed.
    """

    # See https://docs.pydantic.dev/usage/models/#custom-root-types

    __root__: Union[LazyBaseModel, Dict[KeyT, Union[LazyBaseModel, ValueT]]]

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, item):
        return self.data[item]

    # LazyContainer implementation.

    def __lazy_init_root__(self):
        self.__root__ = parse_obj_as(Dict[KeyT, Union[LazyBaseModel, ValueT]], dict())

    def __lazy_addto_root__(self, key, obj):
        self.__root__[key] = obj

    def __lazy_raw_data_iterator__(self, data):
        for key, value in data.items():
            yield key, value

    @property
    def data(self) -> Union[None, Dict[KeyT, Union[LazyBaseModel, ValueT]]]:
        return self.__lazy_data__()

    @data.setter
    def data(self, value):
        raise Exception("blarg")


class LazyList(GenericModel, Generic[ValueT], UserList, LazyContainer):
    """
    Replacement for List[] that will lazy-load a json chunk when accessed.
    """

    # See https://docs.pydantic.dev/usage/models/#custom-root-types

    __root__: Union[LazyBaseModel, List[Union[LazyBaseModel, ValueT]]]

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, item):
        return self.data[item]

    # LazyContainer implementation.

    def __lazy_init_root__(self):
        self.__root__ = parse_obj_as(List[Union[LazyBaseModel, ValueT]], list())

    def __lazy_addto_root__(self, key, obj):
        self.__root__.append(obj)

    def __lazy_raw_data_iterator__(self, data):
        for key, value in enumerate(data):
            yield key, value

    @property
    def data(self) -> Union[None, List[Union[LazyBaseModel, ValueT]]]:
        return self.__lazy_data__()

    @data.setter
    def data(self, value):
        raise Exception("blarg")
