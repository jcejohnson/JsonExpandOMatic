# JSON Expand-O-Matic

Expand a dict into a collection of subdirectories and json files or contract (un-expand) the output of expand() into a dict.

## Overview

Construct

```python
expandomatic = JsonExpandOMatic(path=data_path, logger=logger)
```

Expand -- become or make larger or more extensive.

```python
data = { ... }
data_path = sys.argv[1] if len(sys.argv) > 1 else '.'
```

Create {data_path}/root.json and {data_path}/root/...

```python
expandomatic.expand(data)
```

Create {data_path}/foo.json and {data_path}/foo/...

```python
expandomatic.expand(foo, root_element='foo')
# Warning: expand() is destructive unless `preserve=True`
```

Contract -- decrease in size, number, or range.

```python
data = expandomatic.contract()
```

Or use jsonref

```python
import jsonref
with open(f'{data_path}/root.json') as f:
    data = jsonref.load(f, base_uri=f'file://{os.path.abspath(data_path)}/')
```

## Quick Start

```bash
# Create and activate the virtual environment
python3.10 -m venv .venv
source .venv/bin/activate
# Configure the venv for development
pip install -e .[dev]
# Run the tests
pytest tests
```

Do a thing:

```bash
rm -rf output
./expand.sh output tests/testresources/actor-data.json 2>&1 | tee log.txt
find output -type f | sort
```

Do another thing:

```bash
rm -rf output
./expand.sh output tests/testresources/actor-data.json '[{"/root/actors/.*": ["/[^/]+/movies/.*"]}]' 2>&1 | tee log.txt
find output -type f | sort
```

## Testing

Install & use tox:

```bash
pip install -e .[dev]
```

Managing code style:

```bash
tox -e format
```

Manually run the commands:

```bash
./wrapper.sh
./expand.sh output tests/testresources/actor-data.json
./contract.sh output | jq -S . > output.json
ls -l output.json tests/testresources/actor-data.json
cmp output.json <(jq -S . tests/testresources/actor-data.json)
```
