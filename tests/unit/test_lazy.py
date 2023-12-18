import pytest

from json_expand_o_matic import JsonExpandOMatic

from .fixtures import Fixtures


@pytest.mark.unit
class TestLazy(Fixtures):
    """Test lazy loading during contraction."""

    def test_equivalency(self, test_data, original_data):
        # Assert that independent copies of the raw data are equivalent.
        assert test_data == original_data

    def test_contract(self, tmpdir, test_data):
        test_data = {
            "people": {
                "fred": {"first_name": "fred", "last_name": "flintstone"},
                "barney": {"first_name": "barney", "last_name": "rubble"},
            }
        }
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=True)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        assert contracted == test_data

    def test_lazy_contraction(self, tmpdir, test_data, original_data):
        ...
