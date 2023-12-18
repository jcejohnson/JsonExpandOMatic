import enum
from dataclasses import dataclass
from typing import Any, Union

from peak.util.proxies import LazyProxy  # type: ignore[import-untyped]


class ContractionProxy:
    # Marker class for alternate contraction proxy implementations.
    ...


class ContractionProxyState(enum.Enum):
    waiting = 1
    loading = 2
    ready = 3


@dataclass
class ContractionProxyContext:
    data: Any
    parent_key: Any
    parent: Union[list, dict]
    path: str
    value: Any
    state: ContractionProxyState = ContractionProxyState.waiting


class DefaultContractionProxy(LazyProxy, ContractionProxy):
    def __init__(self, *, callback):
        context: ContractionProxyContext = callback.keywords["context"]
        assert context.state == ContractionProxyState.waiting
        super().__init__(callback)
