# JSON Expand-O-Matic

Expand a dict into a collection of subdirectories and json files or contract (un-expand) the output of expand() into a dict.

## Overview

Construct

    expandomatic = JsonExpandOMatic(path=data_path, logger=logger)

Expand -- become or make larger or more extensive.

    data = { ... }

    data_path = sys.argv[1] if len(sys.argv) > 1 else '.'

Create {data_path}/root.json and {data_path}/root/...

    expandomatic.expand(data)

Create {data_path}/foo.json and {data_path}/foo/...

    expandomatic.expand(foo, root_element='foo')

    Warning: expand() is destructive unless `preserve=True`

Contract -- decrease in size, number, or range.

    data = expandomatic.contract()

Or use jsonref

    import jsonref
    with open(f'{data_path}/root.json') as f:
        data = jsonref.load(f, base_uri=f'file://{os.path.abspath(data_path)}/')

## Quick Start

Setup wrapper scripts:

    ./wrapper.sh

Install for development:

    ./expand.sh --version

Do a thing:

    rm -rf output
    ./expand.sh output tests/testresources/actor-data.json 2>&1 | tee log.txt
    find output -type f | sort

Do another thing:

    rm -rf output
    ./expand.sh output tests/testresources/actor-data.json '[{"/root/actors/.*": ["/[^/]+/movies/.*"]}]' 2>&1 | tee log.txt
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
    ./expand.sh output tests/testresources/actor-data.json
    ./contract.sh output | jq -S . > output.json
    ls -l output.json tests/testresources/actor-data.json
    cmp output.json <(jq -S . tests/testresources/actor-data.json)
