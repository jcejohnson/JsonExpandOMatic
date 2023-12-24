"""
Less lazy loading for semi-expanded data.

Every non-atomic attribute that is also not a list or dict is
expected to be its own file.
Requires custom expansion rules to create the necessary files.
Uses LazyBaseModel.
Does not use LazyDict and LazyList.

Expected expansion layout:

  Entries preceeded wit '-' represent a list or dict and should
  not be present.

    root/actors/charlie_chaplin.json
  - root/actors/charlie_chaplin/filmography.json
    root/actors/charlie_chaplin/filmography/0.json
    ...
  - root/actors/charlie_chaplin/movies.json
    root/actors/charlie_chaplin/movies/modern_times.json
  - root/actors/charlie_chaplin/spouses.json
    root/actors/charlie_chaplin/spouses/lita_grey.json
  - root/actors/charlie_chaplin/spouses/lita_grey/children.json
    ...
    root/actors/dwayne_johnson.json
    ...
  - root/actors.json
    root.json
"""

from typing import Any, ClassVar, Dict, List, Type, Union

from pydantic import BaseModel as PydanticBaseModel  # type: ignore
from pydantic import Field  # type: ignore

from json_expand_o_matic.pydantic_contractor import LazyBaseModel

try:
    # Fails for python < 3.10
    from typing import TypeAlias
except Exception:
    from typing_extensions import TypeAlias


class CastMember(PydanticBaseModel):
    """
    /root/actors/[^/]+/movies/[^/]+/cast/[^/]+
    """

    actor: str
    name: str


class Film(PydanticBaseModel):
    """
    /root/actors/[^/]+/filmography/[^/]+
    """

    __root__: List[Any]

    # https://docs.pydantic.dev/usage/models/#custom-root-types

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class LazyFilm(LazyBaseModel[Film]):
    _model_clazz: Type[PydanticBaseModel] = Film


AnyFilm: TypeAlias = Union[LazyFilm, Film]
FilmsList: TypeAlias = List[AnyFilm]


class Hobby(PydanticBaseModel):
    """
    /root/actors/[^/]+/hobbies/[^/]+
    """

    name: str


class Movie(PydanticBaseModel):
    """
    /root/actors/[^/]+/movies/[^/]+
    """

    budget: int = 0
    run_time_minutes: int = 0
    title: str
    year: int = 0

    cast: Dict[str, CastMember] = Field(default_factory=dict, description="/root/actors/[^/]+/movies/[^/]+/cast")


class LazyMovie(LazyBaseModel[Movie]):
    _model_clazz: Type[PydanticBaseModel] = Movie


AnyMovie: TypeAlias = Union[LazyMovie, Movie]
MoviesList: TypeAlias = List[AnyMovie]
MoviesDict: TypeAlias = Dict[str, AnyMovie]
MoviesCollection: TypeAlias = Union[MoviesDict, MoviesList]


class Spouse(PydanticBaseModel):
    """
    /root/actors/[^/]+/spouses/[^/]+
    """

    first_name: str
    last_name: str
    children: List[str] = Field(default_factory=list, description="/root/actors/[^/]+/spouses/[^/]+/children")


class LazySpouse(LazyBaseModel[Spouse]):
    _model_clazz: Type[PydanticBaseModel] = Spouse


AnySpouse: TypeAlias = Union[LazySpouse, Spouse]
SpousesDict: TypeAlias = Dict[str, AnySpouse]


class Actor(PydanticBaseModel):
    """
    /root/actors/[^/]+
    """

    class Config:
        arbitrary_types_allowed = True

    birth_year: int = 0
    first_name: str
    last_name: str
    is_funny: bool = False

    filmography: FilmsList = Field(default_factory=list, description="/root/actors/[^/]+/filmography")
    movies: MoviesCollection = Field(..., description="/root/actors/[^/]+/movies")

    hobbies: Dict[str, Hobby] = Field(default_factory=dict, description="/root/actors/[^/]+/hobies")
    spouses: SpousesDict = Field(default_factory=dict, description="/root/actors/[^/]+/spouses")


class LazyActor(LazyBaseModel[Actor]):
    _model_clazz: Type[PydanticBaseModel] = Actor


AnyActor: TypeAlias = Union[LazyActor, Actor]
ActorsDict: TypeAlias = Dict[str, AnyActor]


class LessLazyModel(PydanticBaseModel):
    """
    Define an alternate root-level model that doesn't require a LazyDict.

    This requires that the 'actors' element in .../root.json is a dict of
    LazyBaseThing and not a LazyBaseThing itself.

    Because we are not using a LazyDict, the LazyActor instances will not
    be able to replace themselves in AlternateModel.actors after creating
    the non-lazy Actor instances.

    /root
    """

    class Config:
        arbitrary_types_allowed = True

    actors: Dict[str, AnyActor] = Field(..., description="/root/actors")

    EXPANSION_RULES: ClassVar[list] = [
        "B>:/root/actors/[^/]+/filmography/.*",  # Create a file per film
        "A<:/root/actors/[^/]+/filmography",  # Eliminate filmography.json
        #
        "B>:/root/actors/[^/]+/hobbies/.*",  # Create a file per hobby
        "A<:/root/actors/[^/]+/hobbies",  # Eliminate hobbies.json
        #
        "B>:/root/actors/[^/]+/movies/[^/]+/cast/.*",  # Create a file per cast member
        "A<:/root/actors/[^/]+/movies/[^/]+/cast",  # Eliminate cast.json
        "A>:/root/actors/[^/]+/movies/.*",  # Create a file per movie. Note `A>`
        "A<:/root/actors/[^/]+/movies",  # Eliminate movies.json
        #
        "B>:/root/actors/[^/]+/spouses/[^/]+/children/.*",  # Create a file per child
        "A<:/root/actors/[^/]+/spouses/[^/]+/children",  # Eliminate children.json
        "A>:/root/actors/[^/]+/spouses/.*",  # Create a file per movie. Note `A>`
        "A<:/root/actors/[^/]+/spouses",  # Eliminate spouses.json
        #
        "A>:/root/actors/.*",  # Create a file per actor. Note `A>`
        "A<:/root/actors",  # Eliminate actors.json
        #
        # Notes:
        #   `A>` - is used to create a "file per foo" when you want some of foo's
        #          attributes to have been put into their own files. Using `B>`
        #          instead would prevent recursion and cause all of foo's data to
        #          be included in foo's file.
    ]

    Actor: ClassVar[Type] = Actor
    ActorsDict: ClassVar[Type] = ActorsDict
    CastMember: ClassVar[Type] = CastMember
    Film: ClassVar[Type] = Film
    FilmsList: ClassVar[Type] = FilmsList
    Hobby: ClassVar[Type] = Hobby
    LazyActor: ClassVar[Type] = LazyActor
    LazyFilm: ClassVar[Type] = LazyFilm
    LazyMovie: ClassVar[Type] = LazyMovie
    LazySpouse: ClassVar[Type] = LazySpouse
    Movie: ClassVar[Type] = Movie
    MoviesDict: ClassVar[Type] = MoviesDict
    MoviesList: ClassVar[Type] = MoviesList
    Spouse: ClassVar[Type] = Spouse
    SpousesDict: ClassVar[Type] = SpousesDict
