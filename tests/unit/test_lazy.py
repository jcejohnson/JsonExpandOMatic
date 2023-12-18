import json

import pytest

from json_expand_o_matic import JsonExpandOMatic


class TestLazy:
    """Test lazy loading during contraction."""

    # Our raw test data.
    _raw_data = None

    @pytest.fixture
    def raw_data(self, resource_path_root):
        if not TestLazy._raw_data:
            TestLazy._raw_data = json.loads((resource_path_root / "actor-data.json").read_text())
        return TestLazy._raw_data

    # Fixtures to provide copies of the raw data to each test function.

    @pytest.fixture
    def test_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture
    def original_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    def test_equivalency(self, test_data, original_data):
        # Assert that independent copies of the raw data are equivalent.
        assert test_data == original_data

    def test_contract(self, tmpdir, test_data, original_data):
        test_data = {
            "people": {
                "jcej": {"first_name": "james", "last_name": "johnson"},
                "kaj": {"first_name": "karla", "last_name": "johnson"},
            }
        }
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=True)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.

        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root", lazy=True)

        assert contracted == test_data
