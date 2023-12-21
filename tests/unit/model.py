"""
Lazy loading for fully expanded data.

Every non-atomic attribute is expected to be its own file.
Compatible with default expansion rules.
Uses LazyBaseModel, LazyDict and LazyList.

Expected expansion layout:

    root/actors/charlie_chaplin.json
    root/actors/charlie_chaplin/filmography.json
    root/actors/charlie_chaplin/filmography/0.json
    ...
    root/actors/charlie_chaplin/movies.json
    root/actors/charlie_chaplin/movies/modern_times.json
    root/actors/charlie_chaplin/spouses.json
    root/actors/charlie_chaplin/spouses/lita_grey.json
    root/actors/charlie_chaplin/spouses/lita_grey/children.json
    ...
    root/actors/dwayne_johnson.json
    ...
    root/actors.json
    root.json
"""

from typing import Any, ClassVar, Dict, List, Type, Union

from pydantic import BaseModel as PydanticBaseModel  # type: ignore
from pydantic import Field  # type: ignore

from json_expand_o_matic.pydantic_contractor import LazyBaseModel, LazyDict, LazyList

try:
    # Fails for python < 3.10
    from typing import TypeAlias
except Exception:
    from typing_extensions import TypeAlias


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
    _model_clazz: Type[PydanticBaseModel] = Film


AnyFilm: TypeAlias = Union[LazyFilm, Film]


class LazyFilmList(LazyList[AnyFilm]):
    _model_clazz: Type[list] = List[AnyFilm]


FilmsList: TypeAlias = Union[LazyFilmList, List[AnyFilm]]


class Hobby(PydanticBaseModel):
    name: str


class Movie(PydanticBaseModel):
    budget: int = 0
    run_time_minutes: int = 0
    title: str
    year: int = 0

    cast: Dict[str, CastMember] = Field(default_factory=dict)


class LazyMovie(LazyBaseModel):
    _model_clazz: Type[PydanticBaseModel] = Movie


AnyMovie: TypeAlias = Union[LazyMovie, Movie]


class LazyMovieList(LazyList[AnyMovie]):
    _model_clazz: Type[list] = List[AnyMovie]


MoviesList: TypeAlias = Union[LazyMovieList, List[AnyMovie]]


class LazyMovieDict(LazyDict[str, AnyMovie]):
    _model_clazz: Type[dict] = Dict[str, AnyMovie]


MoviesDict: TypeAlias = Union[LazyMovieDict, Dict[str, AnyMovie]]


MoviesCollection: TypeAlias = Union[MoviesDict, MoviesList]


class Spouse(PydanticBaseModel):
    first_name: str
    last_name: str
    children: List[str] = Field(default_factory=list)


class LazySpouse(LazyBaseModel):
    _model_clazz: Type[PydanticBaseModel] = Spouse


AnySpouse: TypeAlias = Union[LazySpouse, Spouse]


class LazySpouseDict(LazyDict[str, AnySpouse]):
    _model_clazz: Type[dict] = Dict[str, AnySpouse]


SpousesDict: TypeAlias = Union[LazySpouseDict, Dict[str, AnySpouse]]


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
    _model_clazz: Type[PydanticBaseModel] = Actor


AnyActor: TypeAlias = Union[LazyActor, Actor]


class LazyActorDict(LazyDict[str, AnyActor]):
    _model_clazz: Type[dict] = Dict[str, AnyActor]


ActorsDict: TypeAlias = Union[LazyActorDict, Dict[str, AnyActor]]


class VeryLazyModel(PydanticBaseModel):
    actors: ActorsDict

    # Default expansion rules creates separate files for each attribute
    # that is a list or dict.
    EXPANSION_RULES: ClassVar[list] = []

    Actor: ClassVar[Type] = Actor
    CastMember: ClassVar[Type] = CastMember
    Film: ClassVar[Type] = Film
    Hobby: ClassVar[Type] = Hobby
    LazyActor: ClassVar[Type] = LazyActor
    LazyActorDict: ClassVar[Type] = LazyActorDict
    LazyFilm: ClassVar[Type] = LazyFilm
    LazyFilmList: ClassVar[Type] = LazyFilmList
    LazyMovie: ClassVar[Type] = LazyMovie
    LazyMovieDict: ClassVar[Type] = LazyMovieDict
    LazyMovieList: ClassVar[Type] = LazyMovieList
    LazySpouse: ClassVar[Type] = LazySpouse
    LazySpouseDict: ClassVar[Type] = LazySpouseDict
    Movie: ClassVar[Type] = Movie
    Spouse: ClassVar[Type] = Spouse
