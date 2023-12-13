import abc
import copy
import json
from typing import Any, Dict, List, Optional, Union

import pytest

from json_expand_o_matic.contract_lazily import LazyMaker
from json_expand_o_matic.expand_o_matic import JsonExpandOMatic
from pydantic import BaseModel, Field
from pydantic.class_validators import root_validator



class AktorDataLazyLoader(LazyMaker.LazyLoaderBase):
    def load(self, name: str, data_type: type, reference: str) -> Any:
        return data_type(...)


make_lazy = LazyMaker(loader=AktorDataLazyLoader)

# The models that we @make_lazy need to agree with the expansion rules.
# It shouldn't hurt to @make_lazy something that doesn't need it but
# loading will fail if you don't @make_lazy something that is lazy.

@make_lazy
class Film(BaseModel):
    __root__: List[Union[str,int]]

class CastMember(BaseModel):
    actor: str
    character: str = Field(..., alias="name")

@make_lazy
class Movie(BaseModel):
    title: str
    year: Optional[int]
    run_time_minutes: Optional[int]
    budget: Optional[int]
    cast: Optional[CastMember]

@make_lazy
class Spouse(BaseModel):
    first_name: str
    last_name: str
    childrent: List[str]


@make_lazy
class Actor(BaseModel):
    first_name: str
    last_name: str
    birth_year: int
    filmography: Optional[List[Film.LAZY]]
    hobbies: Optional[dict]
    is_funny: Optional[bool]
    spouses: Optional[Dict[str, Spouse.LAZY]]
    movies: Union[Dict[str, Movie.LAZY], List[Movie.LAZY]]

class Model(BaseModel):
    actors: Dict[str, Actor.LAZY]


class TestLaziness:
    """ """


    # Our raw test data.
    _raw_data = None

    @pytest.fixture
    def raw_data(self, resource_path_root):
        if not TestLaziness._raw_data:
            TestLaziness._raw_data = json.loads((resource_path_root / "actor-data.json").read_text())
        return TestLaziness._raw_data

    @pytest.fixture
    def test_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture
    def original_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    def test_expansion(self, tmpdir, test_data, resource_path_root):
        expanded = JsonExpandOMatic(path=resource_path_root/"blarg").expand( test_data, root_element="root")
