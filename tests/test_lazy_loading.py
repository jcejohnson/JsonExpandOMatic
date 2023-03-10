import json
import os

import jsonref  # type: ignore
import pytest

from json_expand_o_matic import JsonExpandOMatic
from tests.testresources.model import LazyModelParser, Model


class TestLazyLoading:
    """
    Teach pydantic how to lazy-load an expanded json.
    """

    @pytest.fixture
    def raw_data(self, resource_path_root):
        return json.loads((resource_path_root / "actor-data.json").read_text())

    @pytest.fixture
    def model(self, resource_path_root):
        return Model.parse_file((resource_path_root / "actor-data.json"))

    @pytest.fixture
    def expansion(self, tmpdir, raw_data):
        expanded = JsonExpandOMatic(path=tmpdir).expand(raw_data, root_element="root", preserve=True)
        return tmpdir, expanded

    def test_load_model(self, resource_path_root):
        """
        Load a normal json file into the model.
        """

        model = Model.parse_file((resource_path_root / "actor-data.json"))

        assert "charlie_chaplin" in model.actors
        assert "dwayne_johnson" in model.actors

    def test_expand(self, tmpdir, model):
        """
        Expand a model into a directory of files.
        """

        data = model.dict(exclude_defaults=True, by_alias=True)
        expanded = JsonExpandOMatic(path=tmpdir).expand(data, root_element="root", preserve=True)

        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        assert os.path.exists(f"{tmpdir}/root.json")
        assert os.path.exists(f"{tmpdir}/root")

    def test_load_lazy_model(self, expansion):
        """
        Lazy-load a model from a directory of files.
        """

        tmpdir, expanded = expansion
        assert expanded == {"root": {"$ref": f"{tmpdir.basename}/root.json"}}

        with open(f"{tmpdir}/root.json") as f:
            root = json.load(f)

        assert root == {"actors": {"$ref": "root/actors.json"}}

        # root.update({
        #     # $ref is ignored. It is the file that causes Model to exist.
        #     "$ref": f"{tmpdir.basename}/root.json",
        #     # $type is also ignored, it is the non-lazy object in root.json.
        #     "$type": Model,
        #     # $base is required so that the fields of Model have an anchor
        #     # for their referenced json files.
        #     "$base": str(tmpdir)
        # })

        model = LazyModelParser[Model].lazy_load(
            ref="root.json",
            model_clazz=Model,
            base=tmpdir
        )

        charlie_chaplin = model.actors["charlie_chaplin"]
        print(charlie_chaplin)
