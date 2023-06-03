import abc
import copy
import json
from typing import Any, Dict, List, Optional, Union

import pytest

from json_expand_o_matic.contract_lazily import LazyMaker
from json_expand_o_matic.expand_o_matic import JsonExpandOMatic
from pydantic import BaseModel, Field
from pydantic.class_validators import root_validator

DATA = {
    "actors": {
        "charlie_chaplin": {"first_name": "Charlie", "last_name": "Chaplin"},
        "dwayne_johnson": {
            "first_name": "Dwayne",
            "last_name": "Johnson",
            "movies": [{"title": "Fast Five", "runtime": 120}],
        },
    }
}


class AktorDataLazyLoader(LazyMaker.LazyLoaderBase):
    def load(self, name: str, data_type: type, reference: str) -> Any:
        return data_type(**DATA["actors"][reference])


make_lazy = LazyMaker(loader=AktorDataLazyLoader)


@make_lazy
class Movie(BaseModel):
    title: str
    runtime: int


@make_lazy
class Actor(BaseModel):
    first_name: str
    last_name: str
    movies: Optional[Union[Dict[str, Movie.LAZY], List[Movie.LAZY]]] = Field(default=None)


class Model(BaseModel):
    actors: Dict[str, Actor.LAZY]


class TestSimpleLaziness:
    """ """

    @pytest.fixture
    def data(self):
        return copy.deepcopy(DATA)

    def test_traditional(self, data):
        m = Model.parse_obj(data)
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["ActorLazyModel"])
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["ActorActualModel"])
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["Actor"])
        assert m.actors["dwayne_johnson"].first_name == "Dwayne"

    def test_lazy(self, data):
        data["actors"]["dwayne_johnson"] = {"$ref": "dwayne_johnson"}

        Model.Config.orm_mode = True
        m = Model.parse_obj(data)
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["ActorLazyModel"])
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["ActorActualModel"])
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["Actor"])
        assert m.actors["dwayne_johnson"].first_name == "Dwayne"

    def test_get_model(self):
        assert make_lazy["ActorLazyModel"]._type is make_lazy["Actor"]
        assert make_lazy["MovieLazyModel"]._type is make_lazy["Movie"]

    def test_attribute_update(self, data):
        Model.Config.orm_mode = True
        m = Model.parse_obj(data)
        m.actors["dwayne_johnson"].first_name = "Mr."
        assert m.actors["dwayne_johnson"].first_name == "Mr."
