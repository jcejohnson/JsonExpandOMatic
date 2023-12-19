import copy
import json
from typing import Any, Dict, List, Union

import pytest

from json_expand_o_matic import JsonExpandOMatic
from json_expand_o_matic.contractor import ContractionProxy
from json_expand_o_matic.lazy_contractor import (
    DefaultContractionProxy,
    DefaultContractionProxyContext,
)

from .fixtures import Fixtures

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


class CountingContractionProxy(DefaultContractionProxy):
    def __init__(self, *, callback):
        global CONTRACTION_PROXY_INSTANCE_COUNTER
        CONTRACTION_PROXY_INSTANCE_COUNTER += 1
        super().__init__(callback=callback)


class CountingContractionProxyContext(DefaultContractionProxyContext):
    def proxy(self) -> ContractionProxy:
        global CONTRACTION_PROXY_COUNTER
        CONTRACTION_PROXY_COUNTER += 1
        return super().proxy()

    def _delayed_contraction(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        global CONTRACTION_DELAYED_CONTRACTION_COUNTER
        CONTRACTION_DELAYED_CONTRACTION_COUNTER += 1
        return super()._delayed_contraction()


"""
@dataclass
class CustomContractionProxy(LazyProxy, ContractionProxy):
    #

    COUNTER: ClassVar[int] = 0

    def __init__(self, *, callback):
        def custom_callback(*args, **kwargs):
            print("CALLBACK")
            CustomContractionProxy.COUNTER += 1
            return callback(*args, **kwargs)

        LazyProxy.__init__(self, custom_callback)
"""

simple_test_data = {
    "people": {
        "fred": {"first_name": "fred", "last_name": "flintstone"},
        "barney": {"first_name": "barney", "last_name": "rubble"},
    }
}

"""
def recursively_compare(a, b):
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        for key in a.keys():
            if not recursively_compare(a[key], b[key]):
                return False
        return True
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        for key, _ in enumerate(a):
            if not recursively_compare(a[key], b[key]):
                return False
        return True
    return a == b
"""


@pytest.mark.unit
@pytest.mark.lazy
class TestLazy(Fixtures):
    """Test lazy loading during contraction."""

    def test_equivalency(self, test_data, original_data):
        # Assert that independent copies of the raw data are equivalent.
        assert test_data == original_data

    def test_default_proxy_1(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        assert not isinstance(contracted, ContractionProxy)
        assert isinstance(contracted, dict)

        assert not isinstance(original_data["actors"], ContractionProxy)
        assert isinstance(original_data["actors"], dict)

        assert original_data.keys() == contracted.keys()
        assert "actors" in contracted.keys()

        # The proxy has not yet been triggered.
        assert isinstance(contracted["actors"], ContractionProxy)

        # This will trigger the lazy loading callback.
        assert isinstance(contracted["actors"], dict)

        # The proxy has been replaced by lazily loaded data.
        assert not isinstance(contracted["actors"], ContractionProxy)

        # Similar to the original_data / contracted assertions above.
        assert original_data["actors"] == contracted["actors"]
        assert original_data["actors"].values() != contracted["actors"].values()

        # Force full traversal and trigger all lazy loads.
        assert json.dumps(original_data) == json.dumps(contracted)

        assert original_data["actors"] == contracted["actors"]

        isinstance(contracted["actors"], ContractionProxy)
        isinstance(contracted["actors"]["charlie_chaplin"], ContractionProxy)
        isinstance(contracted["actors"]["charlie_chaplin"]["filmography"], ContractionProxy)

    def test_default_proxy_2(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        # assert not isinstance(contracted, ContractionProxy)
        assert isinstance(contracted, dict)

        # The proxy has not yet been triggered.
        assert isinstance(contracted["actors"], ContractionProxy)

        # This will trigger the lazy loading callback.
        assert list(original_data.values()) == list(contracted.values())

        # The proxy has been replaced by lazily loaded data.
        assert not isinstance(contracted["actors"], ContractionProxy)

        # Everything else is identical to test_default_proxy_1

    def test_default_proxy_3(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        # assert not isinstance(contracted, ContractionProxy)
        assert isinstance(contracted, dict)

        # The proxy has not yet been triggered.
        assert isinstance(contracted["actors"], ContractionProxy)

        # This will trigger the lazy loading callback.
        copied = copy.deepcopy(contracted)

        # The proxy has been replaced by lazily loaded data.
        assert not isinstance(contracted["actors"], ContractionProxy)

        assert list(original_data.values()) == list(copied.values())

        # Everything else is identical to test_default_proxy_1

    def test_triggers(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        reset_counters()

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_proxy_class=CountingContractionProxy,
            contraction_context_class=CountingContractionProxyContext,
        )
        assert_counters(1, 1, 0)

        assert not isinstance(contracted, CountingContractionProxy)
        assert_counters(1, 1, 0)

        # This won't trigger lazy loading because it is the root element
        # and has already been loaded.
        assert isinstance(contracted, dict)
        assert_counters(1, 1, 0)

        # Similarly, ** on the root element won't trigger another load.
        def foo(**stuff):
            return stuff

        foo(**contracted)  # type: ignore
        assert_counters(1, 1, 0)

        keys = contracted.keys()
        assert_counters(1, 1, 0)

        keys = list(keys)
        assert len(keys) == 1
        assert "actors" in keys
        assert_counters(1, 1, 0)

        actors = contracted["actors"]
        assert_counters(1, 1, 0)

        # These won't trigger delayed contraction because it
        # is the actual type of `actors`.
        assert isinstance(actors, ContractionProxy)
        assert isinstance(actors, DefaultContractionProxy)
        assert isinstance(actors, CountingContractionProxy)
        assert_counters(1, 1, 0)

        # This will trigger delayed contraction because the proxy
        # must look at the actual object.
        # _delayed_contraction will load actor.json
        # Because there are two actors in our data, two more
        # contexts will be created by the proxy() method.
        assert isinstance(actors, dict)
        assert_counters(
            proxy_instance=3,
            proxy_method=3,
            delayed_contraction_method=1,
        )

        charlie_chaplin = actors["charlie_chaplin"]
        assert_counters(3, 3, 1)

        # This will trigger _delayed_contraction to load charlie_chaplin.json
        # charlie_chaplin has three lazy loaded attributes:
        # - filmography
        # - movies
        # - spouses
        # Each of those causes invocation of proxy() and creation
        # of a CountingContractionProxy.
        charlie_chaplin = dict(charlie_chaplin)
        assert_counters(
            proxy_instance=6,
            proxy_method=6,
            delayed_contraction_method=2,
        )
