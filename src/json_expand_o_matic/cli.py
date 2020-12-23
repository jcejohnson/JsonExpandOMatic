
import logging
import json
import sys

from . import JsonExpandOMatic
from .cycles import CycleDetector

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def expand():

    data = json.load(open(sys.argv[2]))

    logger.info("Checking for cycles")
    CycleDetector(data).detect()

    logger.info("Expanding")
    JsonExpandOMatic(path=sys.argv[1]).expand(data, preserve=False)


def contract():

    root_element = sys.argv[2] if len(sys.argv) > 2 else 'root'

    logger.info("Contracting")
    data = JsonExpandOMatic(path=sys.argv[1], logger=logger).contract(root_element=root_element)

    logger.info("Checking for cycles")
    CycleDetector(data).detect()

    logger.info("Saving result")
    with open(sys.argv[3] if len(sys.argv) > 3 else f"{sys.argv[1]}-out.json", 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
