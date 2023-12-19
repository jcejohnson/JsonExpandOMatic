from typing import Any, ClassVar, Dict, List, Type, Union

from pydantic import BaseModel as PydanticBaseModel  # type: ignore
from pydantic import Field  # type: ignore

from json_expand_o_matic.pydantic_contractor import LazyBaseModel, LazyDict, LazyList


class BaseModel(PydanticBaseModel):
    ...


class LazyModel(LazyBaseModel):
    ...


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


class LazyFilm(LazyBaseModel):
    _model_clazz: ClassVar[Type[PydanticBaseModel]] = Film


AnyFilm = Union[LazyFilm, Film]


class LazyFilmList(LazyList[AnyFilm]):
    _model_clazz: Type[list] = List[AnyFilm]


FilmsList = Union[LazyFilmList, List[AnyFilm]]


class Hobby(PydanticBaseModel):
    name: str


class Movie(PydanticBaseModel):
    budget: int = 0
    run_time_minutes: int = 0
    title: str
    year: int = 0

    cast: Dict[str, CastMember] = Field(default_factory=dict)


class LazyMovie(LazyBaseModel):
    _model_clazz: ClassVar[Type[PydanticBaseModel]] = Movie


AnyMovie = Union[LazyMovie, Movie]


class LazyMovieList(LazyList[AnyMovie]):
    _model_clazz: Type[list] = List[AnyMovie]


MoviesList = Union[LazyMovieList, List[AnyMovie]]


AnyMovie = Union[LazyMovie, Movie]


class LazyMovieDict(LazyDict[str, AnyMovie]):
    _model_clazz: Type[dict] = Dict[str, AnyMovie]


MoviesDict = Union[LazyMovieDict, Dict[str, AnyMovie]]


MoviesCollection = Union[MoviesDict, MoviesList]


class Spouse(PydanticBaseModel):
    first_name: str
    last_name: str
    children: List[str] = Field(default_factory=list)


class LazySpouse(LazyBaseModel):
    _model_clazz: ClassVar[Type[PydanticBaseModel]] = Spouse


AnySpouse = Union[LazySpouse, Spouse]


class LazySpouseDict(LazyDict[str, AnySpouse]):
    _model_clazz: Type[dict] = Dict[str, AnySpouse]


SpousesDict = Union[LazySpouseDict, Dict[str, AnySpouse]]


class Actor(PydanticBaseModel):
    birth_year: int = 0
    first_name: str
    last_name: str
    is_funny: bool = False

    filmography: FilmsList = Field(default_factory=list)
    movies: MoviesCollection

    hobbies: Dict[str, Hobby] = Field(default_factory=dict)
    spouses: SpousesDict = Field(default_factory=dict)


class LazyActor(LazyBaseModel):
    _model_clazz: ClassVar[Type[PydanticBaseModel]] = Actor


AnyActor = Union[LazyActor, Actor]


class LazyActorDict(LazyDict[str, AnyActor]):
    _model_clazz: Type[dict] = Dict[str, AnyActor]


ActorsDict = Union[LazyActorDict, Dict[str, AnyActor]]


class Model(PydanticBaseModel):
    actors: ActorsDict
