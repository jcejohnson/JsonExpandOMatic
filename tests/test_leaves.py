import json
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

    def test_nested1(self, tmpdir, test_data, original_data):
        """Test a simple leaf_nodes scenario."""
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*", "/[^/]+/filmography"]}],
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # This is the same thing you would expect in the non-nested case.
        self._assert_root(tmpdir)
        self._assert_actors(tmpdir)

        # Unlike the non-nested case with regex "/root/actors/.*", the nested case
        # will have a directory per actor.
        # See the discussion in test_nested1_equivalency on why this is.
        self._assert_actor_dirs(tmpdir)

        # The nested "/[^/]+/movies/.*" gives us a file-per-movie
        self._assert_movies(tmpdir)
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies/modern_times.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies/0.json")

        # It is also worth noting that other dicts not explicitly mentiond in the list
        # of nested expressions are given no special treatment.
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/oona_oneill.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/oona_oneill")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/oona_oneill/children.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies")

    def test_nested1_equivalency(self, tmpdir, test_data, original_data):
        """
        In a nested leaf-node expression the dict key is treated as it
        would be in the non-nested case.

        The nested functionality takes the file written by that expression
        and feeds it back through JsonExpandOMatic with the dict's value
        as the new leaf_nodes parameter value.

        You can represent any of the nested expressions as non-tested but,
        IMO, nested expressions can be easier to follow in some cases.
        """

        import glob

        JsonExpandOMatic(path=f"{tmpdir}/n").expand(
            test_data,
            root_element="root",
            preserve=False,
            leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*", "/[^/]+/filmography"]}],
        )
        nested_files = [x.replace(f"{tmpdir}/n", "") for x in glob.glob(f"{tmpdir}/n", recursive=True)]

        JsonExpandOMatic(path=f"{tmpdir}/f").expand(
            test_data,
            root_element="root",
            preserve=False,
            leaf_nodes=["/root/actors/.*/movies/.*", "/root/actors/.*/filmography"],
        )
        flattened_files = [x.replace(f"{tmpdir}/f", "") for x in glob.glob(f"{tmpdir}/f", recursive=True)]

        assert nested_files == flattened_files

    def test_nested2(self, tmpdir, test_data, original_data):
        """Test a targeted leaf_node exmple.

        The expressions listed in the dict value are relative to the
        element matched by the dict key expression.
        Our previous examlpes used a regex to ignore that but we can do
        interesting things with it if we want.

        In this example we will collapse all of Dwayne Johnson's movies
        and Charlie Chaplin's spouses.
        """
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            leaf_nodes=[{"/root/actors/.*": ["/dwayne_johnson/movies", "/charlie_chaplin/spouses"]}],
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        # This is the same thing you would expect in the non-nested case.
        self._assert_root(tmpdir)
        self._assert_actors(tmpdir)

        # Unlike the non-nested case with regex "/root/actors/.*", the nested case
        # will have a directory per actor.
        # See the discussion in test_nested1_equivalency on why this is.
        self._assert_actor_dirs(tmpdir)

        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies.json")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies")
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies")

    def xtest_enhanced_nested1(self, tmpdir, test_data, original_data):
        """Enhanced nested #1...

        But what if we want a single json file per actor to include
        everything about that actor _except_ movies and a separate
        movies.json for each actor with all of that actor's movie data?

        You might initially have thought that we would do:
            leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*"]}]
        But we have already established that is equivalent to:
            leaf_nodes=["/root/actors/.*/movies/.*"]
        We will stop recursion at each movie but everything else will be
        done as normal (i.e. - file per dict/list).

        Or maybe you would consider:
            leaf_nodes=["/root/actors/.*", "/root/actors/.*/movies/.*"]
        or:
            leaf_nodes=["/root/actors/.*/movies/.*", "/root/actors/.*"]
        But that won't work because "/root/actors/.*" will stop recursion
        before paths matching "/root/actors/.*/movies/.*" are seen.
        Remember:  All regexes are checked for each path & the first one
        matching stops recursion.

        This is what we will do:
            [
              {
                "/root/actors/.*": [
                  "/[^/]+/movies/.*",
                  "<A:/.*"
                ]
              }
            ]

        The key of the nested expression ("/root/actors/.*") tells expand
        start a new JsonExpandOMatic recursion and save the resulting
        "mangled" data as {actor}.json when that recursion completes.
        That's normal nested behavior and during normal nested behavior
        of "/[^/]+/movies/.*" expand would create {movie}.json but expand
        any other dict/list found for the actor.
        The '<A:' prefix, however, alters the behavior for those paths that
        are matched by the expression "/.*". This expression will be applied
        after (A) recursion and the result included (<) in their parent.
        """

        JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            root_element="root",
            preserve=False,
            leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*", "<A:/.*"]}],
        )

        # This is the same thing you would expect in the non-nested case.
        self._assert_root(tmpdir)
        self._assert_actors(tmpdir)

        # Unlike the non-nested case with regex "/root/actors/.*", the nested case
        # will have a directory per actor.
        # See the discussion in test_nested1_equivalency on why this is.
        self._assert_actor_dirs(tmpdir)

        # The nested "/[^/]+/movies/.*" gives us a file-per-movie
        self._assert_movies(tmpdir)
        assert os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/movies/modern_times.json")
        assert os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/movies/0.json")

        # TODO: Explain these assertions
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses")
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/lita_grey.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/lita_grey")
        assert not os.path.exists(f"{tmpdir}/root/actors/charlie_chaplin/spouses/lita_grey/children.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies.json")
        assert not os.path.exists(f"{tmpdir}/root/actors/dwayne_johnson/hobbies")

        with open(f"{tmpdir}/root/actors/charlie_chaplin.json") as f:
            data = json.load(f)
            assert data.get("spouses", None)
            assert data.get["spouses"].get("lita_grey", None)
            assert data.get["spouses"]["lita_grey"].get("children", None)

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
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

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
