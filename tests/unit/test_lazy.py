import copy
import json

import pytest

from json_expand_o_matic import JsonExpandOMatic
from json_expand_o_matic.contractor import ContractionProxy

from .fixtures import Fixtures

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

    # @pytest.fixture(scope="function")
    # def contraction_proxy_class(self):
    #     CustomContractionProxy.COUNTER = 0
    #     return CustomContractionProxy

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

        # expectation = '{"actors": {"$ref": "root/actors.json", "$loaded": true}}'
        # assert expectation == json.dumps(contracted, cls=ContractionProxyJSONEncoder)

        # target = copy.deepcopy(contracted)
        # assert original_data == target

        # assert original_data.keys() == target.keys()
        # assert original_data.values() != target.values()

        # assert recursively_compare(original_data, target)

        # assert recursively_compare(original_data, contracted)

    def test_default_proxy_2(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        # assert not isinstance(contracted, ContractionProxy)
        assert isinstance(contracted, dict)

        # The proxy has not yet been triggered.
        assert isinstance(contracted["actors"], ContractionProxy)

        # For any two dicts d1 and d2: d1.values() != d2.values() BUT list(d1.values()) == list(d2.values())
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

    """
    def test_custom_proxy(self, tmpdir, contraction_proxy_class):
        #

        expanded = JsonExpandOMatic(path=tmpdir).expand(simple_test_data, root_element="root", preserve=True)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.

        assert 0 == contraction_proxy_class.COUNTER

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_proxy_class=contraction_proxy_class,
        )

        assert 0 == contraction_proxy_class.COUNTER

        assert isinstance(contracted, dict)

        assert 0 == contraction_proxy_class.COUNTER

        d = contracted["people"]
        breakpoint()

        json.dumps(d, cls=CustomJSONEncoder)

        assert simple_test_data.keys() == contracted.keys()
        assert simple_test_data.values() == contracted.values()

        assert 1 == contraction_proxy_class.COUNTER

    def test_contract(self, tmpdir, test_data, original_data, contraction_proxy_class):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.

        assert 0 == contraction_proxy_class.COUNTER

        contracted = JsonExpandOMatic(path=tmpdir).contract(
            root_element="root",
            lazy=True,
            contraction_proxy_class=contraction_proxy_class,
        )

        assert isinstance(contracted, dict)

        assert 0 == contraction_proxy_class.COUNTER

        assert original_data.keys() == contracted.keys()
        assert original_data.values() == contracted.values()
        breakpoint()

        actual = contraction_proxy_class.COUNTER
        assert 1 == actual

    """
