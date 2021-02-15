import json
import os

import jsonref  # type: ignore
import pytest

from json_expand_o_matic import JsonExpandOMatic


class TestSimple:
    """Test the basics."""

    # Our raw test data.
    _raw_data = None

    @pytest.fixture
    def raw_data(self, resource_path_root):
        if not TestSimple._raw_data:
            TestSimple._raw_data = json.loads((resource_path_root / "actor-data.json").read_text())
        return TestSimple._raw_data

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

    def test_expand_preserve(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=True)

        # preserve=True prevents mangling of test_data by expand()
        assert test_data == original_data

        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

    def test_expand_mangle(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)

        # preserve=True allows mangling of test_data by expand()
        assert test_data != original_data

        # test_data is the content of "{tmpdir.basename}/root.json"
        assert test_data == {"actors": {"$ref": "root/actors.json"}}
        assert test_data == json.loads(tmpdir.join("root.json").read())

        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

    def test_file_exixtence(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root")
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # This is the wrapper around the original data
        assert os.path.exists(f"{tmpdir}/root.json")
        assert os.path.exists(f"{tmpdir}/root")

        # Now we look at the original data's files
        assert os.path.exists(f"{tmpdir}/root/actors.json")
        assert os.path.exists(f"{tmpdir}/root/actors")
        # A file and directory for each actor
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson")
        # A file and directory for each actor's movies
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies")
        # A file and directory Charlie Chaplin's filmography.
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/filmography.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/filmography")
        # I didn't define filmography test data for Dwayne Johnson.
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/filmography.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/filmography")
        # But I did define an empty hobbies directory for Dwayne Johnson so we will have
        # a file but not a directory (since there was nothing to recurse into).
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies")

        # I'm not going to go any deeper. You get the idea...
        # See `test_leaves.py` for some more interesting things about the files.

    def test_contract(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.
        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root")
        assert contracted == original_data

        # Or we can use jsonref.load() to do the same.
        with open(f"{tmpdir}/root.json") as f:
            assert jsonref.load(f, base_uri=f"file://{tmpdir}/") == original_data

    def test_jsonref(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)

        # We can use jsonref to load this new representation.
        # Note that loading in this way exposes the wrapping element `root`.
        # `tmpdir` must be a fully qualified path.
        loaded = jsonref.loads(json.dumps(expanded), base_uri=f"file://{tmpdir.dirname}/")
        assert loaded == {"root": original_data}
        assert loaded["root"] == original_data

        # A raw load of the wrapping document has references to the sub-elements.
        # This assersion assumes that the original data's elements are all dicts.
        with open(f"{tmpdir}/root.json") as f:
            assert json.load(f) == {k: {"$ref": f"root/{k}.json"} for k, v in original_data.items()}
