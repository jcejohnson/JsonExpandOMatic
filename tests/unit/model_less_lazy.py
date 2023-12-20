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
FilmsList: TypeAlias = List[AnyFilm]


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
MoviesList: TypeAlias = List[AnyMovie]
MoviesDict: TypeAlias = Dict[str, AnyMovie]
MoviesCollection: TypeAlias = Union[MoviesDict, MoviesList]


class Spouse(PydanticBaseModel):
    first_name: str
    last_name: str
    children: List[str] = Field(default_factory=list)


class LazySpouse(LazyBaseModel):
    _model_clazz: Type[PydanticBaseModel] = Spouse


AnySpouse: TypeAlias = Union[LazySpouse, Spouse]
SpousesDict: TypeAlias = Dict[str, AnySpouse]


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
ActorsDict: TypeAlias = Dict[str, AnyActor]


class LessLazyModel(PydanticBaseModel):
    """
    Define an alternate root-level model that doesn't require a LazyDict.

    This requires that the 'actors' element in .../root.json is a dict of
    LazyBaseThing and not a LazyBaseThing itself.

    Because we are not using a LazyDict, the LazyActor instances will not
    be able to replace themselves in AlternateModel.actors after creating
    the non-lazy Actor instances.
    """

    actors: Dict[str, AnyActor]

    EXPANSION_RULES: ClassVar[list] = [
        # Create a file per actor before recursing into it.
        # All four of these rules will accomplish the same thing.
        # The 3rd & 4th work because they match /root/actors/someone before
        # recursing into "someone's" attributes.
        "B>:/root/actors/.*",
        # "B>:/root/actors/.*$",
        # "B>:/root/actors/[^/]+",
        # "B>:/root/actors/[^/]+$",
        #
        # Create a file per actor after recursing into it. Because this is
        # done after recursion files are also created for each nested object.
        # This is default behavior so we don't need to include it.
        # "A>:/root/actors/[^/]+$",
        #
        # After recursing into the actors dict, slurp what would have been
        # actors.json into root.json. This is what allows us to declare
        # AlternateModel.actors as a regular dict instead of a LazyDict.
        "A<:/root/actors",
    ]
