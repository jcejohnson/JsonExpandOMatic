import json
import sys

from . import JsonExpandOMatic

# NOTE: This isn't meant to be a fully functional cli.
#       Mostly because I don't want to impose a dependency (click) on you.
#       It is simply here as a quick way to interact with the library.


def main():

    if sys.argv[1] == "--help":
        myself = sys.argv[0].split("/")[-1]
        print(f"{myself} expand <output-path> <input-file> [<leaf-nodes-spec> ...]")
        print(f"{myself} contract <input-path> [<root-element>]")
    elif sys.argv[1] == "--version":
        print("v0.1.3")
    elif sys.argv[1] == "expand":
        expand(*sys.argv[2:])
    elif sys.argv[1] == "contract":
        contract(*sys.argv[2:])
    else:
        raise Exception(f"Unknown request [{sys.argv[1]}]")


def expand(output_path, input_file, *leaf_nodes_input):

    leaf_nodes = []
    for node in leaf_nodes_input:
        try:
            leaf_nodes.append(json.loads(node))
        except Exception:
            leaf_nodes.append(node)

    from .expander import Expander

    JsonExpandOMatic(path=output_path).expand(
        data=json.load(open(input_file)),
        root_element="root",
        preserve=False,
        leaf_nodes=leaf_nodes,
        hash_mode=Expander.HASH_MD5
        # leaf_nodes=["/.*"]
        # leaf_nodes=["/root/actors/.*/movies/.*"]
        # leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*"]}]
        # # This may be working...
        # leaf_nodes=[
        #     {
        #         ">B:/root/actors/[^/]+$": [
        #             "<B:/[^/]+/(?!movies)[^/]+$",
        #             ">B:/[^/]+/movies/[^/]+$",
        #             ">A:/[^/]+/movies$",
        #             # # ">A:/[^/]+/movies$",
        #             # # ">A:/[^/]+$",
        #             # "<A:/.*"
        #         ]
        #     }
        # ],
    )

    # For instance, leaf_nodes can include elements that are dictionaries
    # rather than regex strings. Each key of the dict is the regex and each
    # value is a leaf_nodes list. The file saved by the key is fed into a
    # new JsonExpandOMatic instance. Recursive recursion FTW.
    #
    #    leaf_nodes=[{"/root/actors/.*": ["/[^/]+/movies/.*", "/[^/]+/filmography"]}]


def contract(input_path, root_element="root"):

    print(
        json.dumps(
            # You can also contract with jsonref (see the tests).
            # Our contract() method is here for convenience.
            # Due to its simple nature, it is also a bit more lightweight
            # than jsonref.
            JsonExpandOMatic(path=input_path).contract(root_element=root_element),
            indent=4,
            sort_keys=True,
        )
    )
