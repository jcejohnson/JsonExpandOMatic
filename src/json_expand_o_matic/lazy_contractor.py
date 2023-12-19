import enum
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, List, Type, Union

from peak.util.proxies import LazyProxy  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from .contractor import Contractor

"""
Simplified theory of operation

app_func_1

    data = jeom.contract(..., lazy=True)

        Contractor.execute

            Contractor._contract

                Contractor._lazy_contraction
                    - create DefaultContractionProxyContext
                    - return DefaultContractionProxyContext.proxy -> DefaultContractionProxy

app_func_2

    data.some_attribute

        ContractionContext.proxy.some_attribute

            DefaultContractionProxyContext._delayed_contraction
                - manage state
                - data = self._contract_now() (i.e. -- Contractor._eager_contraction)
                - replace proxy instance in parent collection with data if possible
                - manage state
                - return data -> Union[List[Any], Dict[Any, Any], ContractionProxy]
"""


class ContractionProxy:
    # Marker class for alternate contraction proxy implementations.
    ...


class ContractionProxyState(enum.Enum):
    waiting = 1
    loading = 2
    ready = 3


@dataclass
class ContractionProxyContext:
    """
    Instances of ContractionProxyContext subclasses are created by Contractor._lazy_contraction()

    The attributes of ContractionProxyContext capture the contraction state at the point where
    eager contraction would load the next bit of data and invoke Contractor._contract() to recurse.
    """

    # The Contractor instance that created us.
    contractor: "Contractor"

    # ContractionProxy that will be returned by .proxy()
    # Provided by Contractor.lazy_contraction.
    # May be ignored by subclasses.
    contraction_proxy_class: Type[ContractionProxy]

    # The callback created by proxy()
    callback: partial = field(init=False)

    # Parameters to Contractor._*_contraction()
    path: List[str]
    value: Any
    data: Any
    parent: Union[list, dict]
    parent_key: Any

    state: ContractionProxyState = ContractionProxyState.waiting

    def proxy(self) -> ContractionProxy:
        """
        Returns an instance of ContractionProxy.

        The returned instance is intended to create a LazyProxy or something similar
        that will invoke self._delayed_contraction() when it is appropriate to invoke
        Contractor._eager_contraction().
        """
        raise NotImplementedError()

    def _delayed_contraction(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        """
        Typically invoked by the ContractionProxy instance returned by self.proxy()

        This is intended to do what would have been done by an eager Contractor as is done
        by DefaultContractionProxyContext. Alternate implementations may want to return a
        representation of the data to be loaded (e.g. - a jsonref-compliant dict) and let
        some other application-specific mechanism perform the actual loading at an even
        later point in time.

        Canonical implementation:

            def _delayed_contraction(self):
                manage state
                result = self._contract_now()
                finalize state
                return result
        """
        raise NotImplementedError()

    def _contract_now(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        """
        Intended to be invoked by _delayed_contraction()

        This lets _delayed_contraction() handle state management which allows
        subclasses of DefaultContractionProxyContext to focus on just the data
        load mechanics.

        Canonical implementation:

            def _contract_now(self):
                lazy_data = self.contractor._eager_contraction(...)
        """
        raise NotImplementedError()


# Default Implementations


class DefaultContractionProxy(LazyProxy, ContractionProxy):
    """ """

    def __init__(self, *, callback):
        # callback should be a partial function that will delegate to
        # ContractionProxyContext._delayed_contraction()

        context = callback.func.__self__
        assert isinstance(context, ContractionProxyContext)

        # print(f"{type(self)} parent_key=[{context.parent_key}] path=[{context.path}]")
        assert context.state == ContractionProxyState.waiting
        super().__init__(callback)


class DefaultContractionProxyContext(ContractionProxyContext):
    """ """

    def proxy(self) -> ContractionProxy:
        """
        Returns a ContractionProxy instance whose callback is `partial(self._delayed_contraction)`
        """

        self.callback = partial(self._delayed_contraction)
        proxy = self.contraction_proxy_class(callback=self.callback)
        return proxy

    def _delayed_contraction(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        """
        Uses our superclass' context to invoke Contractor._eager_contraction()
        """

        # print(f"_lazy_delayed_contraction parent_key=[{self.parent_key}] path=[{self.path}]")

        assert self.state == ContractionProxyState.waiting
        self.state = ContractionProxyState.loading

        lazy_data = self._contract_now()

        # Replace the ContractionProxy instance with the lazy-loaded data.
        if self.parent:
            self.parent[self.parent_key] = lazy_data

        self.state = ContractionProxyState.ready
        assert not isinstance(lazy_data, ContractionProxy)
        # print(f"_lazy_delayed_contraction parent_key=[{self.parent_key}] path=[{self.path}] DONE")

        return lazy_data

    def _contract_now(self) -> Union[List[Any], Dict[Any, Any], ContractionProxy]:
        lazy_data = self.contractor._eager_contraction(
            data=self.data,
            parent_key=self.parent_key,
            parent=self.parent,
            path=self.path,
            value=self.value,
        )

        return lazy_data
