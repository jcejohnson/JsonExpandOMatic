
import json
import jsonref
import logging
import os
import sys

from json_expand_o_matic import JsonExpandOMatic


raw_data = {
    'actors': {
        'charlie_chaplin': {
            'first_name': 'Charlie',
            'last_name': 'Chaplin',
            'is_funny': True,
            'birth_year': 1889,
            'filmography': [
                ('The Kid', 1921),
                ('A Woman of Paris', 1923),
                # ...
                ('Modern Times', 1936)
            ],
            'movies': {
                'modern_times': {
                    'title': 'Modern Times',
                    'year': 1936,
                    'budget': 1500000,
                    'run_time_minutes': 87,
                }
            }
        },
        'dwayne_johnson': {
            'first_name': 'Dwayne',
            'last_name': 'Johnson',
            'hobbies': {},
            'movies': [
                {
                    'title': 'Fast Five',
                    'cast': {
                        'dominic_toretto': {'name': 'Dominic Toretto', 'actor': 'vin_diesel'},
                        'brian_oconner': {'name': 'Brian O\'Conner', 'actor': 'paul_walker'},
                        'mia_toretto': {'name': 'Mia Toretto', 'actor': 'jordana_brewster'}
                    }
                }
            ]
        }
    }
}

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

data_path = sys.argv[1] if len(sys.argv) > 1 else '.'

# Make two copies of our raw data.
# One will be our test victim, the other will be for validation.
test_data = json.loads(json.dumps(raw_data))
original_data = json.loads(json.dumps(raw_data))
assert test_data == original_data

expanded = JsonExpandOMatic(path=data_path, logger=logger).expand(
    test_data, root_element='root', preserve=True)
assert test_data == original_data
# expand() returns a new representation of `data`
assert expanded == {'root': {'$ref': './root.json'}}

expanded = JsonExpandOMatic(path=data_path, logger=logger).expand(
    test_data, root_element='root', preserve=False)
assert test_data != original_data
# expand() returns a new representation of `data`
assert expanded == {'root': {'$ref': './root.json'}}

# We can use jsonref to load this new representation.
# Note that loading in this way exposes the wrapping element `root`.
loaded = jsonref.loads(json.dumps(expanded), base_uri=f'file://{os.getcwd()}/{data_path}/')
assert loaded == {'root': original_data}
assert loaded['root'] == original_data

# A raw load of the wrapping document has references to the sub-elements.
# This assersion assumes that the original data's elements are all dicts.
with open(f'{data_path}/root.json') as f:
  assert json.load(f) == {k: {"$ref": f"root/{k}.json"} for k, v in original_data.items()}

# We can use JsonExpandOMatic() to load the expanded data from the filesystem.
# Note that this returns the original data exactly, the `root` wrapper is removed.
contracted = JsonExpandOMatic(path=data_path, logger=logger).contract(root_element='root')
assert contracted == original_data

# Or we can use jsonref.load() to do the same.
with open(f'{data_path}/root.json') as f:
  assert jsonref.load(f, base_uri=f'file://{os.getcwd()}/{data_path}/') == original_data
