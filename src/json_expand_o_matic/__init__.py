"""Expand a dict into a collection of subdirectories and json files or
   contract (un-expand) the output of expand() into a dict.

    Construct

      expandomatic = JsonExpandOMatic(path=data_path, logger=logger)

    Expand

      data = { ... }

      data_path = sys.argv[1] if len(sys.argv) > 1 else '.'

      expandomatic.expand(data)
        Creates {data_path}/root.json and {data_path}/root/...

      expandomatic.expand(foo, root_element='foo')
        Creates {data_path}/foo.json and {data_path}/foo/...

      Warning: expand() is destructive unless `preserve=True`

    Contract

      data = expandomatic.contract()

      import jsonref
      with open(f'{data_path}/root.json') as f:
        data = jsonref.load(f, base_uri=f'file://{os.path.abspath(data_path)}/')

    See also: .jsonrefkeeper

"""

from .expand_o_matic import JsonExpandOMatic
