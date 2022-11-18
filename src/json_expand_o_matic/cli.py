import json
import sys

from . import JsonExpandOMatic

# NOTE: This isn't meant to be a fully functional cli.
#       Mostly because I don't want to impose a dependency (click) on you.
#       It is simply here as a quick way to interact with the library.


def expand():

    JsonExpandOMatic(path=sys.argv[1]).expand(
        json.load(open(sys.argv[2])), preserve=False, leaf_nodes=sys.argv[3:] if len(sys.argv) > 3 else []
    )

    # For instance, leaf_nodes can include elements that are dictionaries
    # rather than regex strings. Each key of the dict is the regex and each
    # value is a leaf_nodes list. The file saved by the key is fed into a
    # new JsonExpandOMatic instance. Recursive recursion FTW.
    #
    #    leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*", "/[^/]+/filmography"]}]


def contract():

    root_element = sys.argv[2] if len(sys.argv) > 2 else "root"
    print(
        json.dumps(
            # You can also contract with jsonref (see the tests).
            # Our contract() method is here for convenience.
            # Due to its simple nature, it is also a bit more lightweight
            # than jsonref.
            JsonExpandOMatic(path=sys.argv[1]).contract(root_element=root_element),
            indent=4,
            sort_keys=True,
        )
    )
