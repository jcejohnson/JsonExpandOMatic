import json
import os
from urllib.parse import urlparse


class Contractor:
    def __init__(self, *, logger, path, root_element):
        self.logger = logger
        self.path = path
        self.root_element = root_element

    def execute(self):

        return self._contract(path=[self.path], data=self._slurp(self.path, f"{self.root_element}.json"))

    def _contract(self, *, path, data):

        if isinstance(data, list):
            for k, v in enumerate(data):
                data[k] = self._contract(path=path, data=v)

        elif isinstance(data, dict):

            for k, v in data.items():
                if self._something_to_follow(k, v):
                    return self._contract(path=path + [os.path.dirname(v)], data=self._slurp(*path, v))
                data[k] = self._contract(path=path, data=v)

        return data

    def _something_to_follow(self, k, v):

        if k != "$ref":
            return False

        url_details = urlparse(v)
        return not (url_details.scheme or url_details.fragment)

    def _slurp(self, *args):
        with open(os.path.join(*args)) as f:
            return json.load(f)
