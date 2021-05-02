# JSON Expand-O-Matic

Expand a dict into a collection of subdirectories and json files or contract (un-expand) the output of expand() into a dict.

Expand -- become or make larger or more extensive.

Contract -- decrease in size, number, or range.

## Overview

Construct

    data_path = ...
    expandomatic = JsonExpandOMatic(path=data_path, logger=logger)

Expand -- Creates {data_path}/root.json and {data_path}/root/...

    data = { ... }
    expandomatic.expand(data)

Contract -- Returns dict representation of {data_path}/root.json and {data_path}/root/...

    data = expandomatic.contract()

Contract using jsonref

    import jsonref
    f = open(f'{data_path}/root.json')  # Yes, use a context.
    data = jsonref.load(f, base_uri=f'file://{os.path.abspath(data_path)}/')

## Quick Start

Setup wrapper scripts & venv:

    ./wrapper.sh

Validate setup:

    ./expand.sh --version

Do a thing:

    rm -rf output
    ./expand.sh output tests/testresources/actor-data.json 2>&1 | tee log.txt
    find output -type f | sort

Do another thing:

    rm -rf output
    ./expand.sh output tests/testresources/actor-data.json \
        '[{"/root/actors/.*": ["/[^/]+/movies/.*"]}]' 2>&1 | tee log.txt
    find output -type f | sort

## Testing

Install & use tox:

    ./tox.sh

Update requirements.txt and dev-requirements.txt:

    ./tox.sh -e deps

Reformat the code to make it pretty:

    ./tox.sh -e fmt

Manually run the commands:

    ./wrapper.sh
    ./venv/bin/JsonExpandOMatic expand output tests/testresources/actor-data.json
    ./venv/bin/JsonExpandOMatic contract output | jq -S . > output.json
    ls -l output.json tests/testresources/actor-data.json
    cmp output.json <(jq -S . tests/testresources/actor-data.json)

## Beyond Basics

In the simplest case we will create a directory tree full of json files. A file is created for each dict or list in the source dict. These are the things covered by [test_simple.py](tests/test_simple.py).

In the real world, we want to have more control over when we create the json files. Given our [test data](tests/testresources/actor-data.json), we may want to create a json file per actor, per movie or per some other criteria. We do this by specifying [LeafNodes](src/json_expand_o_matic/leaf_node.py) (as in leaves on a tree that terminate branches) and these are the things covered by [test_leaves.py](tests/test_leaves.py). There are also commented-out examples of leaf nodes in the [cli](src/json_expand_o_matic/cli.py).

To be continued...
