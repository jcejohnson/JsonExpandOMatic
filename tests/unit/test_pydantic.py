import json
import pathlib
from typing import Any, Dict, List, Union, cast

import pytest

from json_expand_o_matic import JsonExpandOMatic
from json_expand_o_matic.lazy_contractor import ContractionProxyState
from json_expand_o_matic.pydantic_contractor import (
    ContractionProxy,
    LazyPydanticBaseModel,
    LazyPydanticDict,
    PydanticContractionProxy,
    PydanticContractionProxyContext,
)

from .fixtures import Fixtures

PYDANTIC = True
try:
    import pydantic  # type: ignore  # noqa: F401

except Exception:
    PYDANTIC = False


# How many CountingContractionProxy instances are created
CONTRACTION_PROXY_INSTANCE_COUNTER: int = 0
# How many CountingContractionProxyContext.proxy is invoked
CONTRACTION_PROXY_COUNTER: int = 0
# How many times CountingContractionProxyContext._delayed_contraction is invoked
CONTRACTION_DELAYED_CONTRACTION_COUNTER: int = 0


def reset_counters():
    global CONTRACTION_PROXY_INSTANCE_COUNTER
    global CONTRACTION_PROXY_COUNTER
    global CONTRACTION_DELAYED_CONTRACTION_COUNTER

    CONTRACTION_PROXY_INSTANCE_COUNTER = 0
    CONTRACTION_PROXY_COUNTER = 0
    CONTRACTION_DELAYED_CONTRACTION_COUNTER = 0


def assert_counters(proxy_instance, proxy_method, delayed_contraction_method):
    assert CONTRACTION_PROXY_INSTANCE_COUNTER == proxy_instance
    assert CONTRACTION_PROXY_COUNTER == proxy_method
    assert CONTRACTION_DELAYED_CONTRACTION_COUNTER == delayed_contraction_method


class CountingContractionProxy(PydanticContractionProxy):
    def __init__(self, *, callback):
        global CONTRACTION_PROXY_INSTANCE_COUNTER
        CONTRACTION_PROXY_INSTANCE_COUNTER += 1
        super().__init__(callback=callback)


class CountingContractionProxyContext(PydanticContractionProxyContext):
    def proxy(self) -> ContractionProxy:
        global CONTRACTION_PROXY_COUNTER
        CONTRACTION_PROXY_COUNTER += 1
        return super().proxy()

    def _delayed_contraction(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        global CONTRACTION_DELAYED_CONTRACTION_COUNTER
        CONTRACTION_DELAYED_CONTRACTION_COUNTER += 1
        return super()._delayed_contraction()


@pytest.mark.skipif(not PYDANTIC, reason="pydantic not available.")
@pytest.mark.unit
@pytest.mark.pydantic
class TestPydantic(Fixtures):
    """Test lazy loading pydantic models during contraction."""

    def test_model(self, test_data, original_data):
        from .model_with_lazy_pydantic_base_thing import VeryLazyModel

        assert "actors" in test_data

        instance = VeryLazyModel.parse_obj(test_data)
        assert instance

        assert json.dumps(original_data, sort_keys=True, indent=0) == instance.json(
            exclude_defaults=True, exclude_unset=True, sort_keys=True, indent=0
        )

    def test_eager_contraction(self, original_data, default_expansion):
        from .model_with_lazy_pydantic_base_thing import VeryLazyModel

        tmpdir = default_expansion.pop("$tmpdir")

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.
        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root")
        assert contracted == original_data

        instance = VeryLazyModel.parse_obj(contracted)
        assert instance

        assert json.dumps(original_data, sort_keys=True, indent=0) == instance.json(
            exclude_defaults=True, exclude_unset=True, sort_keys=True, indent=0
        )

    @pytest.mark.lazy
    def test_lazy_root(self, tmpdir, test_data, original_data):
        from .model_less_lazy_with_lazy_pydantic_base_thing import LessLazyModel

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
            leaf_nodes=LessLazyModel.EXPANSION_RULES,
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])

        with open(root) as f:
            data = json.load(f)

        # LazyBaseModel requires a $ctx
        # That is handled by the custom context & proxy but we have to cheat here.
        for subdata in data.values():
            if "$ref" in subdata:
                subdata["$ctx"] = 0
                continue
            for subsubdata in subdata.values():
                if "$ref" in subsubdata:
                    subsubdata["$ctx"] = 0

        instance = LessLazyModel.parse_obj(data)
        assert isinstance(instance, LessLazyModel)
        assert isinstance(instance.actors, dict)

        for key, actor in instance.actors.items():
            assert isinstance(actor, LessLazyModel.LazyActor), key

        actors = instance.actors

        # At this point actors["charlie_chaplin"] is a lazy object
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, LessLazyModel.LazyActor)

        # This will trigger the lazy load but that will fail because we loaded
        # the data directly rather than using contract() and therefore the
        # LazyActor does not have a PydanticContractionProxyContext that it can
        # use to load the actual data.
        try:
            assert charlie_chaplin.first_name == "Charlie"
            assert False, "BUG"
        except AssertionError:
            ...

    @pytest.mark.lazy
    @pytest.mark.xfail
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")  # Remove this once the tests is fixed.
    def test_lazy_root_with_lazy_base_thing(self, tmpdir, test_data):
        from .model_less_lazy_with_lazy_base_thing import LessLazyModel

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
            leaf_nodes=LessLazyModel.EXPANSION_RULES,
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])

        with open(root) as f:
            data = json.load(f)

        # LazyBaseModel requires a $ctx
        # That is handled by the custom context & proxy but we have to cheat here.
        for subdata in data.values():
            assert "$ref" not in subdata
            for key, subsubdata in subdata.items():
                assert "$ref" in subsubdata
                stuff = subdata[key]
                subdata[key] = LessLazyModel.LazyActor(**stuff)
                #     ref=subsubdata["$ref"],
                #     ctx=None,
                #     root=root.parent,
                # )

        # parse_obj() currently fails because of LazyBaseThing.data()
        # when `ctx and not root`. I would like to fix it but I'm not
        # sure it is worth the effort.
        instance = LessLazyModel.parse_obj(data)

        assert True, "instance = LessLazyModel.parse_obj(data) should have raised an exception."

        assert isinstance(instance, LessLazyModel)
        assert isinstance(instance.actors, dict)

        for key, actor in instance.actors.items():
            assert isinstance(actor, LessLazyModel.LazyActor), key

        actors = instance.actors

        # At this point actors["charlie_chaplin"] is a lazy object
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, LessLazyModel.LazyActor)

        # This will trigger the lazy load but that will fail because we loaded
        # the data directly rather than using contract() and therefore the
        # LazyActor does not have a PydanticContractionProxyContext that it can
        # use to load the actual data.
        try:
            assert charlie_chaplin.first_name == "Charlie"
            assert False, "BUG"
        except AssertionError:
            ...

    @pytest.mark.lazy
    def test_lazy_load(self, default_expansion):
        from .model_with_lazy_pydantic_base_thing import LazyActorDict, VeryLazyModel

        tmpdir = default_expansion.pop("$tmpdir")

        expanded = cast(Dict[str, Dict[str, str]], default_expansion)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_context_class=PydanticContractionProxyContext,
            contraction_proxy_class=PydanticContractionProxy,
        )

        instance = VeryLazyModel.parse_obj(contracted)

        assert issubclass(LazyActorDict, LazyPydanticDict)

        assert isinstance(instance, VeryLazyModel)
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
        assert lst

        assert issubclass(VeryLazyModel.LazyActor, LazyPydanticBaseModel)

        # At this point actors["charlie_chaplin"] is a lazy object
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, VeryLazyModel.LazyActor)

        # This will trigger the lazy load.
        assert charlie_chaplin.first_name == "Charlie"
        # Our local charlie_chaplin variable hasn't changed but
        # LazyBaseModel has replaced itself in the LazyDict that contains it.
        assert isinstance(charlie_chaplin, VeryLazyModel.LazyActor)
        assert isinstance(actors["charlie_chaplin"], VeryLazyModel.Actor)

        # Refresh our local copy from the lazy dict
        charlie_chaplin = actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, VeryLazyModel.Actor)

        # Verify that the original data returned by contract()
        # has not been mutated by the pydantic bits.
        assert isinstance(contracted, dict)
        assert isinstance(contracted["actors"], dict)
        assert "charlie_chaplin" not in contracted["actors"]
        assert "$ref" in contracted["actors"]

        # FIXME: Exercise LazyList
        # FIXME: Exercise model.dict() -- should load everything
        # FIXME: Exercise model.json() -- should not load everything

        ...

    @pytest.mark.lazy
    def test_basic_less_lazy_load(self, tmpdir, test_data):
        # from .model_less_lazy_with_lazy_pydantic_base_thing import LessLazyModel
        from .model_less_lazy_with_lazy_base_thing import LessLazyModel

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
            leaf_nodes=LessLazyModel.EXPANSION_RULES,
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # breakpoint()

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])
        assert root

        # breakpoint()

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_context_class=PydanticContractionProxyContext,
            contraction_proxy_class=PydanticContractionProxy,
        )

        from pydantic import parse_obj_as

        # def whacky_validator(v: Any, **kwargs):  # *args, **kwargs):
        #     breakpoint()
        #     if issubclass(kwargs["field"].type_, LessLazyModel.LazyActor):
        #         v = {key[1:] if key.startswith("$") else key: value for key, value in v.items()}
        #         return v
        #     raise ClassError()
        # _VALIDATORS.append((LessLazyModel.LazyActor, [whacky_validator]))
        # breakpoint()

        assert isinstance(contracted, dict)
        assert isinstance(contracted["actors"], dict)

        charlie_chaplin = contracted["actors"]["charlie_chaplin"]
        assert isinstance(contracted["actors"]["charlie_chaplin"], PydanticContractionProxy)

        lazy_actor = parse_obj_as(LessLazyModel.LazyActor, charlie_chaplin)

        # breakpoint()
        lazy_actor.first_name

        # breakpoint()

        instance = LessLazyModel.parse_obj(contracted)
        assert instance

        # breakpoint()
        ...

    @pytest.mark.lazy
    def test_less_lazy_load(self, tmpdir, test_data):
        from .model_less_lazy_with_lazy_base_thing import (
            Actor,
            LazyActor,
            LessLazyModel,
        )

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
            leaf_nodes=LessLazyModel.EXPANSION_RULES,
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # breakpoint()

        expanded = cast(Dict[str, Dict[str, str]], expanded)
        root = pathlib.Path(tmpdir.dirname, expanded["root"]["$ref"])
        assert root

        # breakpoint()

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_context_class=PydanticContractionProxyContext,
            contraction_proxy_class=PydanticContractionProxy,
        )

        assert isinstance(contracted, dict)
        assert isinstance(contracted["actors"], dict)

        charlie_chaplin = contracted["actors"]["charlie_chaplin"]
        assert charlie_chaplin is contracted["actors"]["charlie_chaplin"]
        assert isinstance(charlie_chaplin, PydanticContractionProxy)
        # Nothing has changed, no proxies were triggered.
        assert charlie_chaplin is contracted["actors"]["charlie_chaplin"]

        # breakpoint()

        instance = LessLazyModel.parse_obj(contracted)
        assert instance

        #
        # After loading we generally won't use `contracted` but it is important
        # to understand what has happened to it.
        #

        assert not (charlie_chaplin is contracted["actors"]["charlie_chaplin"])
        assert isinstance(charlie_chaplin, PydanticContractionProxy)

        # The proxy in contracted["actors"] has been replaced with the json data
        assert not isinstance(contracted["actors"]["charlie_chaplin"], PydanticContractionProxy)
        assert isinstance(contracted["actors"]["charlie_chaplin"], dict)
        assert set(contracted["actors"]["charlie_chaplin"].keys()) == {"$ref", "$ctx"}
        assert contracted["actors"]["charlie_chaplin"]["$ref"] == "root/actors/charlie_chaplin.json"
        assert isinstance(contracted["actors"]["charlie_chaplin"]["$ctx"], int)

        #
        # Inspect the proxy context.
        # This is the glue between the raw json data, the lazy model and the complete model.
        #

        cid = contracted["actors"]["charlie_chaplin"]["$ctx"]
        context = PydanticContractionProxyContext.context_cache[cid]
        assert isinstance(context, PydanticContractionProxyContext)
        assert id(context) == cid

        # json file has been loaded (that's how we get the `contracted["actors"]["charlie_chaplin"]` dict)
        assert context.state == ContractionProxyState.ready
        # The json/dict has not yet been converted to a non-lazy model because we haven't requested any attributes.
        assert context.model_state == ContractionProxyState.waiting

        #
        # What we're more interested in is `instance`
        #

        assert set(instance.actors.keys()) == {"charlie_chaplin", "dwayne_johnson"}

        charlie_chaplin = instance.actors["charlie_chaplin"]
        assert charlie_chaplin is instance.actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, LazyActor)

        # Nothing has changed, no proxies were triggered.
        assert charlie_chaplin is instance.actors["charlie_chaplin"]
        assert (context.state, context.model_state) == (ContractionProxyState.ready, ContractionProxyState.waiting)

        # LazyActor subclasses LazyBaseThing which subclasses LazyWrapper.
        # Accessing attributes of LazyActor and LazyBaseThing won't trigger the proxy.
        assert charlie_chaplin._model_clazz is Actor
        assert charlie_chaplin._ref == "root/actors/charlie_chaplin.json"
        assert isinstance(charlie_chaplin._ctx, int)

        assert id(context) == charlie_chaplin._ctx

        # Nothing has changed, no proxies were triggered.
        assert charlie_chaplin is instance.actors["charlie_chaplin"]
        assert (context.state, context.model_state) == (ContractionProxyState.ready, ContractionProxyState.waiting)

        # Let's trigger some proxies.

        assert isinstance(contracted["actors"]["charlie_chaplin"], dict)  # Before secondary contraction.

        first_name = charlie_chaplin.first_name
        assert first_name == "Charlie"

        # secondary proxy has fired.
        assert (context.state, context.model_state) == (ContractionProxyState.ready, ContractionProxyState.ready)

        # The secondary proxy doesn't know how to replace the LazyActor with the Actor in `instance.actors`
        # FIXME: How can I update the context's parent/key so that this happens?
        assert charlie_chaplin is instance.actors["charlie_chaplin"]
        assert isinstance(charlie_chaplin, LazyActor)

        # But the secondary proxy _does_ know how to replace the LazyActor with the Actor in `contracated`
        assert isinstance(contracted["actors"]["charlie_chaplin"], Actor)

        movies = charlie_chaplin.movies
        assert isinstance(movies, dict)

        # breakpoint()

        dwayne_johnson = instance.actors["dwayne_johnson"]

        # This fails with "KeyError: 0" because movies is a list.
        # FIXME: Start here
        first_name = dwayne_johnson.first_name
        assert dwayne_johnson.first_name == "Dwayne"

        movies = dwayne_johnson.movies
        assert isinstance(movies, list)

    @pytest.mark.lazy
    def test_less_lazy_to_dict(self, tmpdir, test_data):
        from .model_less_lazy_with_lazy_base_thing import LessLazyModel

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
            leaf_nodes=LessLazyModel.EXPANSION_RULES,
        )

        expanded = cast(Dict[str, Dict[str, str]], expanded)

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_context_class=PydanticContractionProxyContext,
            contraction_proxy_class=PydanticContractionProxy,
        )

        instance = LessLazyModel.parse_obj(contracted)

        # breakpoint()

        assert isinstance(instance.actors["dwayne_johnson"].movies, list)
        movie_0 = instance.actors["dwayne_johnson"].movies[0]

        # This will trigger a load which _was_ failing because Movie needs a
        # CastMembersDict which can be CastMember or LazyCastMember.
        assert not isinstance(movie_0, str)

        # breakpoint()
        data = instance.dict()
        assert isinstance(data, dict)

        blob = instance.json()
        assert isinstance(blob, str)

        # TODO: Verify that expansion of `instance` is equivalent to the original expansion.
