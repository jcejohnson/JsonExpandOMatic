from typing import Any, List, Union
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from .lazy import LazyDict, LazyBaseModel, LazyList, LazyParserMixin


class CastMember(PydanticBaseModel):
    actor: str
    name: str


class Film(PydanticBaseModel):
    __root__: List[Any]

    # https://docs.pydantic.dev/usage/models/#custom-root-types

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class Hobby(PydanticBaseModel):
    name: str


class Movie(PydanticBaseModel):
    budget: int = 0
    run_time_minutes: int = 0
    title: str
    year: int = 0

    cast: LazyDict[str, CastMember] = Field(default_factory=dict)


class Spouse(PydanticBaseModel):
    first_name: str
    last_name: str
    children: LazyList[str] = Field(default_factory=list)


class Actor(PydanticBaseModel):
    birth_year: int = 0
    first_name: str
    last_name: str
    is_funny: bool = False

    filmography: LazyList[Film] = Field(default_factory=list)
    movies: Union[LazyDict[str, Movie], LazyList[Movie]]

    hobbies: LazyDict[str, Hobby] = Field(default_factory=dict)
    spouses: LazyDict[str, Spouse] = Field(default_factory=dict)


class Model(PydanticBaseModel, LazyParserMixin):
    # LazyParserMixin.parse_lazy() will inject LazyBaseModel as a superclass.
    # No fields are added and regular pydantic mechanisms can be used to
    # create instances of Model.
    # Use this approach if your input data might or might not be lazy-loadable.

    actors: LazyDict[str, Actor]


class LazyModel(LazyBaseModel):
    # LazyBaseModel adds required lazy-loading fields.
    # LazyParserMixin.parse_lazy() will set these, or they can be provided to
    # normal pydantic instantiation mechanisms just like other fields.
    # Use this approach if your input data is lazy-loadable.

    actors: LazyDict[str, Actor]
