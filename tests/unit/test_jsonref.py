import json
from typing import cast

import pytest

from json_expand_o_matic import JsonExpandOMatic

from .fixtures import Fixtures

JSONREF = True
try:
    import jsonref  # type: ignore
except Exception:
    JSONREF = False


@pytest.mark.skipif(not JSONREF, reason="jsonref not available.")
@pytest.mark.unit
@pytest.mark.jsonref
class TestJsonRef(Fixtures):
    """Test jsonref integration."""

    def test_one(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        with open(f"{tmpdir}/root.json") as f:
            assert jsonref.load(f, base_uri=f"file://{tmpdir}/") == original_data

    def test_two(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)

        # We can use jsonref to load this new representation.
        # Note that loading in this way exposes the wrapping element `root`.
        # `tmpdir` must be a fully qualified path.
        loaded = jsonref.loads(json.dumps(expanded), base_uri=f"file://{tmpdir.dirname}/")
        assert loaded == {"root": original_data}
        assert cast(dict, loaded)["root"] == original_data

        # A raw load of the wrapping document has references to the sub-elements.
        # This assersion assumes that the original data's elements are all dicts.
        with open(f"{tmpdir}/root.json") as f:
            assert json.load(f) == {k: {"$ref": f"root/{k}.json"} for k, v in original_data.items()}
