import json
import os
from collections.abc import MutableMapping, MutableSequence

import pytest  # type: ignore

from json_expand_o_matic import JsonExpandOMatic
from tests.testresources.lazy import LazyBaseModel, LazyDict, LazyList
from tests.testresources.model import Actor, LazyModel, Model

# Modify LazyDict so that we can count calls to __lazy_init_root__()

setattr(LazyDict, "__lazy_init_root__original", LazyDict.__lazy_init_root__)
setattr(LazyDict, "__lazy_init_root__counter", 0)


def lazydict_patch(monkeypatch):
    monkeypatch.setattr(LazyDict, "__lazy_init_root__", lazydict__lazy_init_root__counter)
    LazyDict.__lazy_init_root__counter = 0  # type: ignore


def lazydict__lazy_init_root__counter(*args, **kwargs):
    LazyDict.__lazy_init_root__counter += 1  # type: ignore
    LazyDict.__lazy_init_root__original(*args, **kwargs)  # type: ignore


def lazydict__lazy_init_root__assertion(invocations):
    assert LazyDict.__lazy_init_root__counter == invocations  # type: ignore


class TestLazyLoading:
    """
    Teach pydantic how to lazy-load an expanded json.
    """

    @pytest.fixture
    def raw_data(self, resource_path_root):
        return json.loads((resource_path_root / "actor-data.json").read_text())

    @pytest.fixture
    def model(self, resource_path_root):
        return Model.parse_file((resource_path_root / "actor-data.json"))

    @pytest.fixture
    def expansion(self, tmpdir, raw_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(raw_data, root_element="root", preserve=True)
        return tmpdir, expanded

    @pytest.fixture
    def lazy_model(self, expansion):
        tmpdir, expanded = expansion
        model = LazyModel.parse_lazy(tmpdir / "root.json")
        return model

    def test_load_model(self, resource_path_root):
        """
        Load a normal json file into the model.
        """

        model = Model.parse_file(resource_path_root / "actor-data.json")

        assert "charlie_chaplin" in model.actors
        assert "dwayne_johnson" in model.actors

        assert isinstance(model.actors["charlie_chaplin"], Actor)
        assert model.actors["charlie_chaplin"].filmography[0][0] == "The Kid"

    def test_load_lazy_model(self, resource_path_root):
        """
        Load a normal json file into the lazy model.
        """

        model = LazyModel.parse_lazy(resource_path_root / "actor-data.json")

        assert "charlie_chaplin" in model.actors
        assert "dwayne_johnson" in model.actors

        assert isinstance(model.actors["charlie_chaplin"], Actor)
        assert model.actors["charlie_chaplin"].filmography[0][0] == "The Kid"

    def test_expand(self, tmpdir, model):
        """
        Expand a model into a directory of files.
        """

        data = model.dict(exclude_defaults=True, by_alias=True)
        expanded = JsonExpandOMatic(path=tmpdir).expand(data, root_element="root", preserve=True)

        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        assert os.path.exists(f"{tmpdir}/root.json")
        assert os.path.exists(f"{tmpdir}/root")

    def test_model_with_mixin(self, expansion):
        """
        Lazy-load `Model(BaseModel, LazyParserMixin)`
        """

        tmpdir, expanded = expansion
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        with open(tmpdir / "root.json") as f:
            root = json.load(f)

        assert root == {"actors": {"$ref": "root/actors.json"}}

        model = Model.parse_lazy(tmpdir / "root.json")
        assert isinstance(model, Model)

    def test_model_with_lazybasemodel(self, expansion):
        """
        Lazy-load LazyModel(LazyBaseModel)
        """

        tmpdir, expanded = expansion
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        with open(tmpdir / "root.json") as f:
            root = json.load(f)

        assert root == {"actors": {"$ref": "root/actors.json"}}

        model = LazyModel.parse_lazy(tmpdir / "root.json")
        assert isinstance(model, LazyModel)
        assert model.lazy_ref == "root.json"
        assert model.lazy_base == tmpdir

        assert isinstance(model.actors, LazyDict)
        assert isinstance(model.actors, MutableMapping)
        assert isinstance(model.actors.__root__, LazyBaseModel)
        assert not isinstance(model.actors.__root__, MutableMapping)

        assert model.actors.__root__.lazy_ref == "root/actors.json"
        assert model.actors.__root__.lazy_base == tmpdir

    def test_trigger_get(self, lazy_model, monkeypatch):
        """
        Test `instance["key"]` lazy load trigger.
        """
        model = lazy_model

        lazydict_patch(monkeypatch)

        # Before we trigger the lazy load ...
        assert isinstance(model.actors, LazyDict)
        assert isinstance(model.actors, MutableMapping)

        assert isinstance(model.actors.__root__, LazyBaseModel)
        assert model.actors.__root__.lazy_ref == "root/actors.json"
        assert model.actors.__root__.lazy_base == model.lazy_base
        assert model.actors.__root__.lazy_type == LazyDict[str, Actor]

        # This will trigger the lazy load.
        # The LazyBaseModel instance (model.actors.__root__) will be evaluated
        # and replaced with a LazyDict instance containing the data specified
        # by the base/ref properties of the LazyBaseModel.
        charlie_chaplin = model.actors["charlie_chaplin"]

        lazydict__lazy_init_root__assertion(1)

        # The nature of our data is such that model.actors.__root__ is not (yet)
        # a dict of Actors but, instead, a dict of LazyBaseModels that can be
        # loaded to create Actors.
        assert isinstance(model.actors.__root__, dict)  # was LazyBaseModel
        for key, value in model.actors.__root__.items():
            assert isinstance(key, str)
            assert isinstance(value, LazyBaseModel)

        # We haven't asked for any property of model.actors["charlie_chaplin"]
        # so it is still a LazyBaseModel.
        assert isinstance(charlie_chaplin, LazyBaseModel)
        assert not isinstance(charlie_chaplin, Actor)

        assert charlie_chaplin.lazy_ref == "actors/charlie_chaplin.json"
        assert charlie_chaplin.lazy_base == f"{model.lazy_base}/root"
        assert charlie_chaplin.lazy_type == Actor

        #

        model.actors["dwayne_johnson"]
        lazydict__lazy_init_root__assertion(1)

    def test_trigger_in(self, lazy_model, monkeypatch):
        """
        Test `"key" in instance` lazy load trigger.
        """
        model = lazy_model

        lazydict_patch(monkeypatch)

        # This will trigger the lazy load.
        assert "charlie_chaplin" in model.actors

        assert isinstance(model.actors.__root__, dict)  # was LazyBaseModel
        for key, value in model.actors.__root__.items():
            assert isinstance(key, str)
            assert isinstance(value, LazyBaseModel)

        lazydict__lazy_init_root__assertion(1)

    def test_trigger_keys(self, lazy_model, monkeypatch):
        """
        Test `instance.keys()` lazy load trigger.
        """
        model = lazy_model

        lazydict_patch(monkeypatch)

        # This will trigger the lazy load.
        assert sorted(model.actors.keys()) == ["charlie_chaplin", "dwayne_johnson"]

        lazydict__lazy_init_root__assertion(1)

        assert isinstance(model.actors.__root__, dict)  # was LazyBaseModel
        for key, value in model.actors.__root__.items():
            assert isinstance(key, str)
            assert isinstance(value, LazyBaseModel)

        lazydict__lazy_init_root__assertion(1)

    def test_trigger_len(self, lazy_model):
        """
        Test `len(instance)` lazy load trigger.
        """
        model = lazy_model

        # This will trigger the lazy load.
        assert "charlie_chaplin" in model.actors

        assert isinstance(model.actors.__root__, dict)  # was LazyBaseModel
        assert len(model.actors) == 2

    def test_actor(self, lazy_model, monkeypatch):
        """
        Test properties of model.actors["some_actor"].
        """
        model = lazy_model

        lazydict_patch(monkeypatch)

        charlie_chaplin = model.actors["charlie_chaplin"]
        assert not charlie_chaplin.lazy_data

        lazydict__lazy_init_root__assertion(1)

        first_name = charlie_chaplin.first_name
        assert isinstance(charlie_chaplin.lazy_data, Actor)

        lazydict__lazy_init_root__assertion(1)

        assert first_name == "Charlie"
        assert charlie_chaplin.last_name == "Chaplin"
        assert charlie_chaplin.is_funny

        spouses = charlie_chaplin.spouses
        # Before we trigger the lazy load ...
        assert isinstance(spouses, LazyDict)
        assert isinstance(spouses, MutableMapping)

        lazydict__lazy_init_root__assertion(1)

        # This will trigger another lazy load.
        assert sorted(spouses.keys()) == ["lita_grey", "mildred_harris", "oona_oneill", "paulette_goddard"]

        lazydict__lazy_init_root__assertion(2)

    def test_filmography(self, lazy_model):
        """
        Test properties of model.actors["some_actor"].filmography.
        """
        model = lazy_model

        charlie_chaplin = model.actors["charlie_chaplin"]
        assert not charlie_chaplin.lazy_data

        filmography = charlie_chaplin.filmography
        assert isinstance(charlie_chaplin.lazy_data, Actor)

        # Before we trigger the lazy load ...
        assert isinstance(filmography, LazyList)
        assert isinstance(filmography, MutableSequence)

        # Trigger lazy load
        assert len(filmography) == 3

        for film in model.actors["charlie_chaplin"].filmography:
            assert isinstance(film, LazyBaseModel)

    def test_film(self, lazy_model):
        """
        Test properties of model.actors["some_actor"].filmography[n].
        """
        model = lazy_model

        charlie_chaplin = model.actors["charlie_chaplin"]

        # Trigger lazy load
        assert len(charlie_chaplin.filmography) == 3

        for film in model.actors["charlie_chaplin"].filmography:
            if not isinstance(film, LazyBaseModel):
                breakpoint()
            assert isinstance(film, LazyBaseModel), type(film)

        # A Film is just a list of things.
        assert model.actors["charlie_chaplin"].filmography[0][0] == "The Kid"

    def test_spouses(self, lazy_model):
        """
        Test properties of model.actors["some_actor"].spouses.
        """
        model = lazy_model

        charlie_chaplin = model.actors["charlie_chaplin"]
        assert not charlie_chaplin.lazy_data

        spouses = charlie_chaplin.spouses
        assert isinstance(charlie_chaplin.lazy_data, Actor)

        # Before we trigger the lazy load ...
        assert isinstance(spouses, LazyDict)
        assert isinstance(spouses, MutableMapping)

        # Trigger lazy load
        assert len(spouses) == 4

        assert model.actors["charlie_chaplin"].spouses["lita_grey"]
        assert model.actors["charlie_chaplin"].spouses["lita_grey"] == spouses["lita_grey"]
        assert model.actors["charlie_chaplin"].lazy_data.spouses["lita_grey"] == spouses["lita_grey"]
