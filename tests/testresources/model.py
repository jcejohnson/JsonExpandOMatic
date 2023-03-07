import json
import os
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, PrivateAttr, constr, parse_obj_as
from pydantic.generics import GenericModel
from pydantic.generics import _assigned_parameters as GenericModelDetails

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")
LazyT = TypeVar("LazyT")


class LazyBaseModel(PydanticBaseModel):
    class Config:
        lazy_loader_anchor: str = None

    ref: Optional[str] = Field(alias="$ref")
    type: LazyT = Field(alias="$type")
    base: str = Field(alias="$base")


class BaseModel(PydanticBaseModel):
    pass


# I'm probably going to need a LazyList too.


class LazyDict(GenericModel, Generic[KeyT, ValueT]):
    __root__: Union[Dict[constr(regex="\\$ref"), str], Dict[KeyT, ValueT]]
    __subject__: Dict[KeyT, ValueT] = PrivateAttr(default=None)

    def __getitem__(self, key: KeyT) -> ValueT:
        if self.__subject__ is None:
            path = f'{LazyBaseModel.Config.lazy_loader_anchor}/{self.__root__["$ref"]}'
            with open(path) as f:
                data = json.load(f)
                key_clazz = GenericModelDetails[type(self)][KeyT]
                value_clazz = GenericModelDetails[type(self)][ValueT]
                for key, value in data.items():
                    if "$ref" in value:
                        value["$type"] = value_clazz
                        value["$base"] = os.path.dirname(path)
                self.__subject__ = parse_obj_as(Dict[key_clazz, Union[value_clazz, LazyBaseModel]], data)

        print(self.__subject__)

        return self.__subject__[key]


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
