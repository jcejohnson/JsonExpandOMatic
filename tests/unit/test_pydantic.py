import pytest

from .fixtures import Fixtures

# from json_expand_o_matic import JsonExpandOMatic


PYDANTIC = True
try:
    import pydantic  # type: ignore  # noqa: F401

except Exception:
    PYDANTIC = False


@pytest.mark.skipif(not PYDANTIC, reason="pydantic not available.")
@pytest.mark.unit
@pytest.mark.lazy
@pytest.mark.pydantic
class TestLazyPydantic(Fixtures):
    """Test lazy loading pydantic models during contraction."""

    def test_one(self):
        ...
