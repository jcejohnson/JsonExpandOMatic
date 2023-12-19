import json
import os
from pathlib import Path

import pytest

from json_expand_o_matic import JsonExpandOMatic

from .fixtures import Fixtures


@pytest.mark.unit
class TestSimple(Fixtures):
    """Test the basics."""

    def test_equivalency(self, test_data, original_data):
        # Assert that independent copies of the raw data are equivalent.
        assert test_data == original_data

    def test_expand_preserve(self, tmpdir, test_data, original_data, expander_options, hash_option):
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data, root_element="root", preserve=True, **expander_options, **hash_option
        )

        ref_root = expander_options.get("zip_root", tmpdir.basename)

        # preserve=True prevents mangling of test_data by expand()
        assert test_data == original_data

        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{ref_root}/root.json"}}

    def test_expand_mangle(self, tmpdir, test_data, original_data, expander_options, hash_option):
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data, root_element="root", preserve=False, **expander_options, **hash_option
        )

        if "zip_root" in expander_options:
            ref_root = expander_options["zip_root"]
            root_json = Path(tmpdir) / expander_options["zip_root"] / "root.json"
        else:
            ref_root = tmpdir.basename
            root_json = Path(tmpdir) / "root.json"

        # preserve=True allows mangling of test_data by expand()
        assert test_data != original_data

        # test_data is the content of "{ref_root}/root.json"
        assert test_data == json.loads(root_json.read_text())

        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{ref_root}/root.json"}}

    def test_file_exixtence(self, tmpdir, test_data, original_data, expander_options):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", **expander_options)

        if "zip_root" in expander_options:
            ref_root = expander_options["zip_root"]
            json_root = Path(tmpdir) / expander_options["zip_root"]
        else:
            ref_root = tmpdir.basename
            json_root = Path(tmpdir)

        assert expanded == {"root": {"$ref": f"{ref_root}/root.json"}}

        # This is the wrapper around the original data
        assert os.path.exists(f"{json_root}/root.json")
        assert os.path.exists(f"{json_root}/root")

        # Now we look at the original data's files
        assert os.path.exists(f"{json_root}/root/actors.json")
        assert os.path.exists(f"{json_root}/root/actors")
        # A file and directory for each actor
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin.json")
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin")
        assert os.path.exists(f"{json_root}/root/actors/dwayne_johnson.json")
        assert os.path.exists(f"{json_root}/root/actors/dwayne_johnson")
        # A file and directory for each actor's movies
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin/movies.json")
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin/movies")
        assert os.path.exists(f"{json_root}/root/actors/dwayne_johnson/movies.json")
        assert os.path.exists(f"{json_root}/root/actors/dwayne_johnson/movies")
        # A file and directory Charlie Chaplin's filmography.
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin/filmography.json")
        assert os.path.exists(f"{json_root}/root/actors/charlie_chaplin/filmography")
        # I didn't define filmography test data for Dwayne Johnson.
        assert not os.path.exists(f"{json_root}/root/actors/dwayne_johnson/filmography.json")
        assert not os.path.exists(f"{json_root}/root/actors/dwayne_johnson/filmography")
        # But I did define an empty hobbies directory for Dwayne Johnson so we will have
        # a file but not a directory (since there was nothing to recurse into).
        assert os.path.exists(f"{json_root}/root/actors/dwayne_johnson/hobbies.json")
        assert not os.path.exists(f"{json_root}/root/actors/dwayne_johnson/hobbies")

        # I'm not going to go any deeper. You get the idea...
        # See `test_leaves.py` for some more interesting things about the files.

    def test_contract(self, tmpdir, test_data, original_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(test_data, root_element="root", preserve=False)
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.
        contracted = JsonExpandOMatic(path=tmpdir).contract(root_element="root")

        assert contracted == original_data
        assert json.dumps(contracted) == json.dumps(original_data)
