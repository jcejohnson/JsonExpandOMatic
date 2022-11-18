import json

import jsonref  # type: ignore

from json_expand_o_matic import JsonExpandOMatic, jsonrefkeeper


class TestJsonRefKeeper:
    """Test jsonrefkeeper."""

    # Our raw test data.
    _raw_data1 = """
        {
            "stuff":
            {
                "$ref": "#/foo/bar"
            },
            "foo":
            {
                "bar":
                {
                    "baz": 1234
                }
            }
        }
        """

    def test_expecations(self):
        """Just one big test"""

        # Save some data that contains a $ref
        data = JsonExpandOMatic(path="funk").expand(data=json.loads(TestJsonRefKeeper._raw_data1))
        assert data == {"root": {"$ref": "funk/root.json"}}

        # Load the previously expanded data
        data = JsonExpandOMatic(path="funk").contract(root_element="root")
        assert data == {"foo": {"bar": {"baz": 1234}}, "stuff": {"$ref": "#/foo/bar"}}

        data["foo"]["bar"]["baz"] = -1  # Make a change
        assert data == {"foo": {"bar": {"baz": -1}}, "stuff": {"$ref": "#/foo/bar"}}

        # Use jsonrefkeeper to resolve the $ref entry in data['stuff']
        data = jsonrefkeeper.parse(data)

        # Both jsonref and jsonrefkeeper resolve the $ref such that
        # data['stuff'] and data['foo']['bar'] point to the same object: {'baz': -1}
        # Changing either data['stuff']['baz'] or data['foo']['bar']['baz']
        # will have the same result.
        assert data == {"foo": {"bar": {"baz": -1}}, "stuff": {"baz": -1}}

        data["foo"]["bar"]["baz"] = -2
        assert data == {"foo": {"bar": {"baz": -2}}, "stuff": {"baz": -2}}

        # json.dumps(data, indent=None)  # TypeError: Object of type 'dict' is not JSON serializable
        assert (
            json.dumps(data, indent=2) == ""
            '{\n  "foo": {\n    "bar": {\n      "baz": -2\n    }\n  },\n'
            '  "stuff": {\n    "baz": -2\n  }\n}'
        )

        # Using jsonref to dump the data with no indent will preserve the original $ref.
        assert jsonref.dumps(data, indent=None) == '{"foo": {"bar": {"baz": -2}}, "stuff": {"$ref": "#/foo/bar"}}'

        # However providing an indent will cause the underlying proxy object to be resolved and we lose the $ref.
        assert (
            jsonref.dumps(data, indent=2) == ""
            '{\n  "foo": {\n    "bar": {\n      "baz": -2\n    }\n  },\n'
            '  "stuff": {\n    "baz": -2\n  }\n}'
        )

        # This is equivalent to jsonref.dumps(data, indent=None) & probably a little slower for large data structures.
        assert (
            jsonrefkeeper.dumps(data, indent=None) == ""
            '{"foo": {"bar": {"baz": -2}}, "stuff": {"$ref": "#/foo/bar"}}'
        )

        # This is what jsonrefkeeper was created for. We don't have to choose between
        # keeping the refs and having nicely indented output.
        assert (
            jsonrefkeeper.dumps(data, indent=2) == ""
            '{\n  "foo": {\n    "bar": {\n      "baz": -2\n    }\n  },\n'
            '  "stuff": {\n    "$ref": "#/foo/bar"\n  }\n}'
        )
