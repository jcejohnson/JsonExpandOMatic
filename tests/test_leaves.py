import json

import jsonref  # type: ignore
import os
import pytest

from json_expand_o_matic import JsonExpandOMatic


class TestLeaves:
    """Test `leaf_node` functionality."""

    # Our raw test data.
    _raw_data = None

    @pytest.fixture
    def raw_data(self, resource_path_root):
        if not TestLeaves._raw_data:
            TestLeaves._raw_data = json.loads((resource_path_root / "actor-data.json").read_text())
        return TestLeaves._raw_data

    # Fixtures to provide copies of the raw data to each test function.

    @pytest.fixture
    def test_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture
    def original_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    def test_actors1(self, tmpdir, test_data, original_data):
        """Verify that we can create a json file for each actor and not recurse any further."""

        self._actors_test(tmpdir, test_data, original_data, "/root/actors/.*")

    def test_actors2(self, tmpdir, test_data, original_data):
        """Same as test_actors1 but with a more precise regex."""

        self._actors_test(tmpdir, test_data, original_data, "/root/actors/[^/]+")

    def test_charlie1(self, tmpdir, test_data, original_data):
        """Verify that we can single out an actor."""
        self._charlie_test(tmpdir, test_data, original_data, "/root/actors/charlie_chaplin")

    def test_charlie2(self, tmpdir, test_data, original_data):
        """Like test_charlie1 but with a loose wildcard."""
        self._charlie_test(tmpdir, test_data, original_data, "/root/actors/[abcxyz].*")

    def test_charlie3(self, tmpdir, test_data, original_data):
        """Like test_charlie1 but with tighter regex."""
        self._charlie_test(tmpdir, test_data, original_data, "/root/actors/[abcxyz][^/]+")

    def _actors_test(self, tmpdir, test_data, original_data, regex):

        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data, root_element="root", preserve=False, leaf_nodes=[regex]
        )

        # preserve=True allows mangling of test_data by expand()
        assert test_data != original_data

        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        def _not(x):
            return not x

        # We expect to have the root and actors elements fully represented.
        # Our leaf-node regex (/root/actors/.*) tells expand to create a
        # per-actor file but not the per-actor directory or anything below that.
        self._assert_root(tmpdir)
        self._assert_actors(tmpdir)
        self._assert_actor_dirs(tmpdir, f=_not)
        self._assert_movies(tmpdir, f=_not)

    def _charlie_test(self, tmpdir, test_data, original_data, regex):
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data, root_element="root", preserve=False, leaf_nodes=[regex]
        )

        self._assert_root(tmpdir)
        self._assert_actors(tmpdir)

        # No recursion for Charlie Chaplin
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin")

        # Typical recursion for Dwayne Johnson
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies")
        # etc...

    def _assert_root(self, tmpdir):

        # This is the wrapper around the original data
        assert os.path.exists(f"{tmpdir}/root.json")
        assert os.path.exists(f"{tmpdir}/root")

    def _assert_actors(self, tmpdir):

        # Now we look at the original data's files
        assert os.path.exists(f"{tmpdir}/root/actors.json")

        # A file for each actor
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson.json")

    def _assert_actor_dirs(self, tmpdir, f=lambda x: x):

        # Now we look at the original data's files
        assert os.path.exists(f"{tmpdir}/root/actors.json")

        # A file for each actor
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson.json")

        # A directory for each actor
        assert f(os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin"))
        assert f(os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson"))

    def _assert_movies(self, tmpdir, f=lambda x: x):

        assert f(os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies.json"))
        assert f(os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies"))
        assert f(os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies.json"))
        assert f(os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies"))
