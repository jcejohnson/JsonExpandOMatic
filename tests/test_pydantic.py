import copy
import json
from typing import ClassVar, Dict, List, Optional, Type, Union

import pytest

from pydantic import BaseModel, Field, PrivateAttr
from pydantic.main import create_model

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


class LazyLoaderBase(BaseModel):
    """ """

    ref_: str = Field(..., alias="$ref")
    data_: Optional[BaseModel] = None

    def __getattr__(self, name):
        if not self.data_:
            self.data_ = self.type_(**DATA["actors"][self.ref_])
        return getattr(self.data_, name)


class LazyMaker:
    """ """

    ACTUAL_MODELS = {}
    LAZY_MODELS = {}

    def __getitem__(self, class_name: str) -> type:
        v = self.ACTUAL_MODELS.get(class_name) or self.LAZY_MODELS.get(class_name)
        if v:
            return v
        if class_name.endswith("LazyModel") or class_name.endswith("ActualModel"):
            return v
        return self.ACTUAL_MODELS.get(f"{class_name}ActualModel")

    def __call__(self, clazz):
        """ """

        class LazyLoader(LazyLoaderBase):
            type_: type = clazz

        # LazyModel = create_model(f"{clazz.__name__}LazyModel", __base__=LazyLoader, __module__=__name__)
        # ActualModel = create_model(f"{clazz.__name__}ActualModel", __base__=clazz, __module__=__name__)

        self.LAZY_MODELS[f"{clazz.__name__}LazyModel"] = LazyLoader
        self.ACTUAL_MODELS[f"{clazz.__name__}ActualModel"] = clazz

        return Union[LazyLoader, clazz]


make_lazy = LazyMaker()


@make_lazy
class Movie(BaseModel):
    title: str
    runtime: int


@make_lazy
class Actor(BaseModel):
    first_name: str
    last_name: str
    movies: Optional[Union[Dict[str, Movie], List[Movie]]] = Field(default=None)


class Model(BaseModel):
    actors: Dict[str, Actor]


class TestPydantic:
    """ """

    @pytest.fixture
    def raw_data(self, resource_path_root):
        return json.loads((resource_path_root / "actor-data.json").read_text())

    @pytest.fixture
    def data(self):
        return copy.deepcopy(DATA)

    def test_one(self, data):
        m = Model.parse_obj(data)
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["ActorLazyModel"])
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["ActorActualModel"])
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["Actor"])
        assert m.actors["dwayne_johnson"].first_name == "Dwayne"

    def test_two(self, data):
        data["actors"]["dwayne_johnson"] = {"$ref": "dwayne_johnson"}

        Model.Config.orm_mode = True
        m = Model.parse_obj(data)
        assert isinstance(m.actors["dwayne_johnson"], make_lazy["ActorLazyModel"])
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["ActorActualModel"])
        assert not isinstance(m.actors["dwayne_johnson"], make_lazy["Actor"])
        assert m.actors["dwayne_johnson"].first_name == "Dwayne"

    def test_three(self):
        assert make_lazy["ActorLazyModel"].type_ is make_lazy["Actor"]
        assert make_lazy["MovieLazyModel"].type_ is make_lazy["Movie"]

    def test_four(self, data):
        Model.Config.orm_mode = True
        m = Model.parse_obj(data)
        m.actors["dwayne_johnson"].first_name = "Mr."
        assert m.actors["dwayne_johnson"].first_name == "Mr."
