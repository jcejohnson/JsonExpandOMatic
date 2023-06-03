import abc
import copy
import json
from typing import Any, Dict, List, Optional, Union

import pytest

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


class LazyMaker:
    """ """

    class LazyProxyBase(BaseModel):
        pass

    class LazyLoaderBase(abc.ABC):
        @abc.abstractmethod
        def load(self, name: str, data_type: type, reference: str) -> Any:
            ...

    ACTUAL_MODELS = {}
    ALL_MODELS = {}
    LAZY_MODELS = {}

    def __init__(self, loader: LazyLoaderBase, ref_key: str = "$ref") -> None:
        self._loader = loader
        self._ref_key = ref_key

    def __getitem__(self, class_name: str) -> type:
        v = self.ALL_MODELS.get(class_name)
        if v or class_name.endswith("LazyModel") or class_name.endswith("ActualModel"):
            return v
        return self.ACTUAL_MODELS.get(f"{class_name}ActualModel")

    def __call__(self, clazz):
        """ """

        data_loader = self._loader
        ref_key = self._ref_key

        class LazyProxy(LazyMaker.LazyProxyBase):
            class Config:
                underscore_attrs_are_private: bool = True

            ref_: str  # PrivateAttr does not support alias and this isn't really a private attribute anyway.
            _data: Optional[clazz] = None  # The actual model after it has been lazily loaded.
            _type: type = clazz  # The datatype of the actual model.

            @root_validator(pre=True, allow_reuse=True)
            @classmethod
            def lazy_proxy_root_validator(cls, values):
                if ref_key in values:
                    values["ref_"] = values.pop(ref_key)
                return values

            def __getattr__(self, name):
                """
                Lazily load the actual model on first reference and delegate all attribute requests to it.
                """
                if not self._data:
                    self._data = data_loader.load(name=name, data_type=self._type, reference=self.ref_)
                return getattr(self._data, name)

        self.ALL_MODELS[f"{clazz.__name__}LazyModel"] = self.LAZY_MODELS[f"{clazz.__name__}LazyModel"] = LazyProxy
        self.ALL_MODELS[f"{clazz.__name__}ActualModel"] = self.ACTUAL_MODELS[f"{clazz.__name__}ActualModel"] = clazz

        clazz.LAZY_UNION = Union[LazyProxy, clazz]
        return clazz


class AktorDataLazyLoader(LazyMaker.LazyLoaderBase):
    def load(self, name: str, data_type: type, reference: str) -> Any:
        return data_type(**DATA["actors"][reference])


make_lazy = LazyMaker(loader=AktorDataLazyLoader())


@make_lazy
class Movie(BaseModel):
    title: str
    runtime: int


@make_lazy
class Actor(BaseModel):
    first_name: str
    last_name: str
    movies: Optional[Union[Dict[str, Movie.LAZY_UNION], List[Movie.LAZY_UNION]]] = Field(default=None)


class Model(BaseModel):
    actors: Dict[str, Actor.LAZY_UNION]


class TestPydantic:
    """ """

    @pytest.fixture
    def raw_data(self, resource_path_root):
        return json.loads((resource_path_root / "actor-data.json").read_text())

    @pytest.fixture
    def test_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture
    def expanded(self, tmpdir, test_data):
        return JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root")

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

    def test_expanded_laziness(self, expanded):
        ...
