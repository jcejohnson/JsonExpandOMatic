import json
import pathlib
from typing import Dict, cast

import pytest

from json_expand_o_matic import JsonExpandOMatic
from json_expand_o_matic.pydantic_contractor import (
    PydanticContractionProxy,
    PydanticContractionProxyContext,
)

from .fixtures import Fixtures
from .model import Actor, LazyActor, LazyActorDict, LazyBaseModel, LazyDict, Model

PYDANTIC = True
try:
    import pydantic  # type: ignore  # noqa: F401

except Exception:
    PYDANTIC = False


@pytest.mark.skipif(not PYDANTIC, reason="pydantic not available.")
@pytest.mark.unit
@pytest.mark.pydantic
class TestPydantic(Fixtures):
    """Test lazy loading pydantic models during contraction."""

    def test_model(self, test_data, original_data):
        assert "actors" in test_data

        instance = Model.parse_obj(test_data)
        assert instance

        assert json.dumps(original_data, sort_keys=True, indent=0) == instance.json(
            exclude_defaults=True, exclude_unset=True, sort_keys=True, indent=0
        )

    def test_eager_contraction(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.
        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root")
        assert contracted == original_data

        instance = Model.parse_obj(contracted)
        assert instance

        assert json.dumps(original_data, sort_keys=True, indent=0) == instance.json(
            exclude_defaults=True, exclude_unset=True, sort_keys=True, indent=0
        )

    @pytest.mark.lazy
    def test_lazy_root(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])

        with open(root) as f:
            data = json.load(f)

        data["actors"]["$ctx"] = 0

        instance = Model.parse_obj(data)
        assert isinstance(instance, Model)
        assert isinstance(instance.actors, LazyActorDict)

        assert list(expanded.keys())[0] == root.stem  # i.e. -- "root"
        assert instance.actors.ref == f"{root.stem}/actors.json"  # i.e. -- "root/actors.json"
        assert instance.actors.ctx == 0

    @pytest.mark.lazy
    def test_lazy_load(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_context_class=PydanticContractionProxyContext,
            contraction_proxy_class=PydanticContractionProxy,
        )

        instance = Model.parse_obj(contracted)

        assert issubclass(LazyActorDict, LazyDict)

        assert isinstance(instance, Model)
        assert isinstance(instance.actors, LazyActorDict)

        assert instance.actors.ref == f"{root.stem}/actors.json"

        actors = instance.actors
        keys = actors.keys()
        # print(keys)
        # print("Getting iterator")
        itr = iter(keys)
        # print("Got iterator")
        # print("Get list of keys")
        lst = list(itr)  # This triggers actors.__iter__
        # print("Got list of keys")
        # for key in lst:
        # print(key)

        lst = list(actors.keys())  # This triggers actors.__iter__

        assert issubclass(LazyActor, LazyBaseModel)

        # At this point actors["charlie_chaplin"] is a lazy object
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, LazyActor)

        # This will trigger the lazy load.
        assert charlie_chaplin.first_name == "Charlie"
        # Our local charlie_chaplin variable hasn't changed but
        # LazyBaseModel has replaced itself in the LazyDict that contains it.
        assert isinstance(charlie_chaplin, LazyActor)
        assert isinstance(actors["charlie_chaplin"], Actor)

        # Refresh our local copy from the lazy dict
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, Actor)

        # Verify that the original data returned by contract()
        # has not been mutated by the pydantic bits.
        assert isinstance(contracted, dict)
        assert isinstance(contracted["actors"], dict)
        assert "charlie_chaplin" not in contracted["actors"]
        assert "$ref" in contracted["actors"]

        ...
