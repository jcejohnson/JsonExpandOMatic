import json
import logging
import os
import sys

from . import VERSION, JsonExpandOMatic

# NOTE: This isn't meant to be a fully functional cli.
#       Mostly because I don't want to impose a dependency (click) on you.
#       It is simply here as a quick way to interact with the library.


def usage():
    myself = sys.argv[0].split("/")[-1]
    print(f"{myself} expand <output-path> <input-file> [<leaf-nodes-spec> ...]")
    print(f"{myself} contract <input-path> [<root-element>]")


def main():
    cmd = sys.argv[1]
    argv = sys.argv[2:]

    if not argv or sys.argv[2] == "--help" or "--help" in argv:
        usage()
        return

    if sys.argv[2] == "--version":
        print(VERSION)
        return

    if sys.argv[2] == "--log-level":
        logger = _get_expando_logger(sys.argv[3])
        argv = sys.argv[4:]
    else:
        logger = _get_expando_logger(logging.INFO)

    if not argv:
        usage()
        return

    if cmd == "expand":
        expand(logger, *argv)
        return

    if cmd == "contract":
        contract(logger, *argv)
        return

    raise Exception(f"Unknown request [{cmd}]")


def expand(logger, output_path, input_file, *leaf_nodes_input):
    leaf_nodes = []
    for node in leaf_nodes_input:
        try:
            leaf_nodes.append(json.loads(node))
        except Exception:
            leaf_nodes.append(node)

    from .expander import Expander

    JsonExpandOMatic(logger=logger, path=output_path).expand(
        data=json.load(open(input_file)),
        root_element="root",
        preserve=False,
        leaf_nodes=leaf_nodes,
        hash_mode=Expander.HASH_MD5,
        pool_size=int(os.environ.get("JEOM_POOL_SIZE") or 1),
        pool_ratio=float(os.environ.get("JEOM_POOL_RATIO") or 1),
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


def contract(logger, input_path, root_element="root"):
    print(
        json.dumps(
            # You can also contract with jsonref (see the tests).
            # Our contract() method is here for convenience.
            # Due to its simple nature, it is also a bit more lightweight
            # than jsonref.
            JsonExpandOMatic(logger=logger, path=input_path).contract(root_element=root_element),
            indent=4,
            sort_keys=True,
        )
    )


def _get_expando_logger(level):
    logging.basicConfig(level=level)
    logger = logging.getLogger(JsonExpandOMatic.__name__)

    try:
        import coloredlogs  # type: ignore

        coloredlogs.install(level=level, logger=logger)
    except ModuleNotFoundError:
        pass

    return logger
