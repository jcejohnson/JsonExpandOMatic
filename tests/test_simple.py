import json
import shutil
import tempfile
import unittest

import jsonref  # type: ignore

from json_expand_o_matic import JsonExpandOMatic

raw_data = {
    "actors": {
        "charlie_chaplin": {
            "first_name": "Charlie",
            "last_name": "Chaplin",
            "is_funny": True,
            "birth_year": 1889,
            "filmography": [
                ("The Kid", 1921),
                ("A Woman of Paris", 1923),
                # ...
                ("Modern Times", 1936),
            ],
            "movies": {
                "modern_times": {
                    "title": "Modern Times",
                    "year": 1936,
                    "budget": 1500000,
                    "run_time_minutes": 87,
                }
            },
        },
        "dwayne_johnson": {
            "first_name": "Dwayne",
            "last_name": "Johnson",
            "hobbies": {},
            "movies": [
                {
                    "title": "Fast Five",
                    "cast": {
                        "dominic_toretto": {
                            "name": "Dominic Toretto",
                            "actor": "vin_diesel",
                        },
                        "brian_oconner": {
                            "name": "Brian O'Conner",
                            "actor": "paul_walker",
                        },
                        "mia_toretto": {
                            "name": "Mia Toretto",
                            "actor": "jordana_brewster",
                        },
                    },
                }
            ],
        },
    }
}


data_path = tempfile.mkdtemp()  # /tmp/tmp8d6hy1iq
data_path_basename = data_path.split("/")[-1]
data_path_dirname = "/".join(data_path.split("/")[0:-1])


class TestSimple(unittest.TestCase):
    def test_all_things(self):
        try:
            return self._test_all_things()
        finally:
            shutil.rmtree(data_path)

    def _test_all_things(self):

        # Make two copies of our raw data.
        # One will be our test victim, the other will be for validation.
        test_data = json.loads(json.dumps(raw_data))
        original_data = json.loads(json.dumps(raw_data))
        assert test_data == original_data

        expanded = JsonExpandOMatic(path=data_path).expand(test_data, root_element="root", preserve=True)
        assert test_data == original_data
        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{data_path_basename}/root.json"}}
        #                  {'root': {'$ref': 'tmp8d6hy1iq/root.json'}}

        expanded = JsonExpandOMatic(path=data_path).expand(test_data, root_element="root", preserve=False)
        assert test_data != original_data
        # expand() returns a new representation of `data`
        assert expanded == {"root": {"$ref": f"{data_path_basename}/root.json"}}
        #                  {'root': {'$ref': 'tmp8d6hy1iq/root.json'}}

        # We can use jsonref to load this new representation.
        # Note that loading in this way exposes the wrapping element `root`.
        # `data_path` must be a fully qualified path.
        loaded = jsonref.loads(json.dumps(expanded), base_uri=f"file://{data_path_dirname}/")
        assert loaded == {"root": original_data}
        assert loaded["root"] == original_data

        # A raw load of the wrapping document has references to the sub-elements.
        # This assersion assumes that the original data's elements are all dicts.
        with open(f"{data_path}/root.json") as f:
            assert json.load(f) == {k: {"$ref": f"root/{k}.json"} for k, v in original_data.items()}

        # We can use JsonExpandOMatic() to load the expanded data from the filesystem.
        # Note that this returns the original data exactly, the `root` wrapper is removed.
        contracted = JsonExpandOMatic(path=data_path).contract(root_element="root")
        assert contracted == original_data

        # Or we can use jsonref.load() to do the same.
        with open(f"{data_path}/root.json") as f:
            assert jsonref.load(f, base_uri=f"file://{data_path}/") == original_data


if __name__ == "__main__":
    unittest.main()
