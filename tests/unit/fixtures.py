import json

import pytest

from json_expand_o_matic import JsonExpandOMatic


def idfn(fixture_value):
    # ID Function for expander_options fixture.
    if fixture_value == {}:
        return ""
    return "+".join([f"{k}:{v}" for k, v in fixture_value.items()])


class Fixtures:
    # Our raw test data.
    _raw_data = None

    @pytest.fixture
    def raw_data(self, resource_path_root):
        if not self.__class__._raw_data:
            self.__class__._raw_data = json.loads((resource_path_root / "actor-data.json").read_text())
        return self.__class__._raw_data

    # Fixtures to provide copies of the raw data to each test function.

    @pytest.fixture(
        params=[
            {},
            # ExpansionPool parameters.
            #   This tests acceptable combinations.
            #   Combinations that would fail assertions
            #   (e.g. - in ExpansionPool._set_pool_size) are not included.
            {"pool_disable": True},  # Force pool_size=1
            {"pool_size": 0},  # pool_size will be os.cpu_count()
            {"pool_size": 1},  # pool_ratio is ignored
            {"pool_size": 2},  # pool_mode default is SharedMemoryArray
            {"pool_size": 2, "pool_mode": "ArrayOfTuples"},
            {"pool_ratio": 0.5},  # pool_size must be None
            # ExpansionZipper parameters.
            #   Not exercising OutputChoice yet.
            {"zip_root": "foo"},
            {"zip_root": "bar", "zip_file": "zippy"},
            {"zip_file": "zipster.zip"},
            {"zip_output": "UnZipped"},
        ],
        ids=idfn,
    )
    def expander_options(self, request):
        yield request.param

    @pytest.fixture(
        params=[
            {"hash_mode": None},
            {"hash_mode": "HASH_MD5"},
        ],
        ids=["NoChecksum", "HASH_MD5"],
    )
    def hash_option(self, request):
        yield request.param

    @pytest.fixture
    def test_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture
    def original_data(self, raw_data):
        return json.loads(json.dumps(raw_data))

    @pytest.fixture(scope="function")
    def default_expansion(self, tmpdir, test_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(
            test_data,
            json_dump_kwargs={"indent": 2, "sort_keys": True},
        )
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}
        assert isinstance(expanded, dict)
        expanded["$tmpdir"] = tmpdir
        return expanded
