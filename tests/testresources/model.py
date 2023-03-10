import json
import os

from collections import UserDict
from collections.abc import MutableMapping
from typing import Any, Dict, Generic, List, TypeVar, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, PrivateAttr, constr, parse_obj_as, root_validator, create_model
from pydantic.generics import GenericModel
from pydantic.generics import _assigned_parameters as GenericModelDetails

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")

ModelT = TypeVar("ModelT", bound=PydanticBaseModel)

LazyKey = constr(regex="\\$(base|ref)")


class LazyModel(PydanticBaseModel):
    lazy_ref: str = Field(..., alias="$ref")
    lazy_bass: str = Field(..., alias="$base")

    @root_validator(pre=True)
    @classmethod
    def lazy_base_model_root_validator(cls, values):

        for key, value in values.items():
            if not isinstance(value, MutableMapping):
                continue
            if "$ref" in value:
                value["$base"] = os.path.join(values["$base"], os.path.dirname(values["$ref"]))

        return values


class LazyModelParser(Generic[ModelT]):
    @classmethod
    def lazy_load(cls, ref: str, model_clazz: ModelT, base: str) -> Union[ModelT, LazyModel]:
        with open(f"{base}/{ref}") as f:
            data = json.load(f)

        data.update({"$ref": ref, "$base": str(base)})

        lazy_model = create_model(model_clazz.__name__, __base__=(model_clazz, LazyModel))

        model = parse_obj_as(lazy_model, data)

        return model


class LazyDict(GenericModel, Generic[KeyT, ValueT], UserDict):
    __root__: Union[LazyModel, Dict[KeyT, ValueT]]

    __subject__: Dict[KeyT, ValueT] = PrivateAttr(default=None)

    @property
    def data(self) -> Dict[KeyT, ValueT]:

        if not isinstance(self.__root__, LazyModel):
            return self.__root__

        if self.__subject__ is not None:
            # The lazy-loading has been done.
            return self.__subject__

        key_clazz = GenericModelDetails[type(self)][KeyT]
        value_clazz = GenericModelDetails[type(self)][ValueT]

        path = os.path.join(self.__root__.lazy_bass, self.__root__.lazy_ref)
        with open(path) as f:
            data = json.load(f)

        for key, value in data.items():
            if "$ref" not in value:
                # This element is not a lazy model.
                continue

            # Provide $base so that we can load the next layer.
            value["$base"] = os.path.dirname(path)

        self.__subject__ = parse_obj_as(Dict[key_clazz, Union[LazyModel, value_clazz]], data)

        return self.__subject__

    @data.setter
    def data(self, value):
        raise Exception("blarg")


class BaseModel(PydanticBaseModel):
    pass


class CastMember(BaseModel):
    actor: str
    name: str


class Film(BaseModel):
    __root__: List[Any]


class Hobby(BaseModel):
    name: str


class Movie(BaseModel):
    budget: int = 0
    run_time_minutes: int = 0
    title: str
    year: int = 0

    cast: LazyDict[str, CastMember] = Field(default_factory=dict)


class Spouse(BaseModel):
    first_name: str
    last_name: str
    children: List[str] = Field(default_factory=list)


class Actor(BaseModel):
    birth_year: int = 0
    first_name: str
    last_name: str
    is_funny: bool = False

    filmography: List[Film] = Field(default_factory=list)
    movies: Union[LazyDict[str, Movie], List[Movie]]

    hobbies: LazyDict[str, Hobby] = Field(default_factory=dict)
    spouses: LazyDict[str, Spouse] = Field(default_factory=dict)


class Model(BaseModel):
    actors: LazyDict[str, Actor]
