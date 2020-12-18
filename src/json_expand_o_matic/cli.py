
import json
import sys
from . import JsonExpandOMatic


def expand():

    JsonExpandOMatic(path=sys.argv[1]).expand(json.load(open(sys.argv[2])), preserve=False)


def contract():

    root_element = sys.argv[2] if len(sys.argv) > 2 else 'root'
    print(json.dumps(JsonExpandOMatic(path=sys.argv[1]).
                     contract(root_element=root_element), indent=4, sort_keys=True))
