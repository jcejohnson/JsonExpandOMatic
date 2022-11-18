"""Keep $ref entries when outputting with indent.

This is a companion for JsonExpandOMatic for use in cases where
your input json has $ref entries other than host JsonExpandOMatic
itself manages and you want to dump the output with a not-None
indent value.

But... it can be used for any json serializable data structure
where you want to preserve $ref entries when outputting with indent.

Typical usage:

    data = JsonExpandOMatic(...).contract(...)
    OR
    data = json.load(open("some.json"))
    OR
    data = <some json serializable data structure>

    # Use jsonrefkeeper to resolve the $ref entry in data['stuff']
    data = jsonrefkeeper.parse(data)

    # Manipulate your data in whatever way you want.
    # Both jsonref and jsonrefkeeper ensure that the source
    # and dest of a $ref point to the same object.

    # Save the data with $ref's preserved _and_ indentation.
    jsonrefkeeper.dumps(data, indent=2)

"""

import functools
import json

import jsonref  # type: ignore
from proxytypes import CallbackProxy  # type: ignore


class JsonRefWrapper(CallbackProxy):

    writer = False

    __notproxied__ = ("__jsonref__",)

    def __init__(self, data):
        self.__jsonref__ = data

    def callback(self):
        return self.__jsonref__.__reference__ if JsonRefWrapper.writer else self.__jsonref__


class JsonRef(jsonref.JsonRef):
    @classmethod
    def replace_refs(cls, obj, _recursive=False, **kwargs):
        return super(JsonRef, cls).replace_refs(obj, _recursive, **kwargs)

    def callback(self):
        return JsonRefWrapper(super(JsonRef, self).callback())


def parse(data, base_uri="", loader=None, jsonschema=False, load_on_repr=True, **kwargs):
    """
    See :func:`jsonref.load`.

    This can be used with any json serializable object to resolve $refs.
    It is handy when you have used JsonExpandOMatic().contract() to load a
    json file that has $refs other than those managed by JsonExpandOMatic.

    """

    if loader is None:
        loader = functools.partial(jsonref.jsonloader, **kwargs)

    return JsonRef.replace_refs(
        data,
        base_uri=base_uri,
        loader=loader,
        jsonschema=jsonschema,
        load_on_repr=load_on_repr,
    )


def load(fp, base_uri="", loader=None, jsonschema=False, load_on_repr=True, **kwargs):
    """
    See :func:`jsonref.load`.
    """

    data = json.load(fp, **kwargs)
    return parse(data, base_uri=base_uri, loader=loader, jsonschema=jsonschema, load_on_repr=load_on_repr, **kwargs)


def loads(s, base_uri="", loader=None, jsonschema=False, load_on_repr=True, **kwargs):
    """
    See :func:`jsonref.load`.
    """

    data = json.loads(s, **kwargs)
    return parse(data, base_uri=base_uri, loader=loader, jsonschema=jsonschema, load_on_repr=load_on_repr, **kwargs)


def dump(obj, fp, **kwargs):
    """
    See :func:`jsonref.dump`.
    """
    fp.write(dumps(obj, **kwargs))


def dumps(obj, **kwargs):
    """
    See :func:`jsonref.dump`.
    """
    JsonRefWrapper.writer = kwargs.pop("preserve_jsonref", True)
    kwargs["cls"] = jsonref._ref_encoder_factory(kwargs.get("cls", json.JSONEncoder))
    return json.dumps(obj, **kwargs)
