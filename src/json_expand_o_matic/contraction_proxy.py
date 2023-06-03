class ContractionProxy:
    """
    ContractionProxy is enabled by setting `lazy=True` when creating a Contractor.

    ContractionProxy will delegate to the provided function to load data on initial access.
    This is similar to LazyMaker but may be more appropriate when working with "dict of dicts"
    whereas LazyMaker was created with pydantic models in mind.
    """

    def __init__(self, func) -> None:
        self.func = func
        self.proxied_data = None

    @property  # type: ignore
    def __class__(self):
        return self.data.__class__

    def __getattr__(self, name):
        return getattr(self.data, name)

    def __getitem__(self, name):
        return self.data.__getitem__(name)

    def __iter__(self):
        return self.data.__iter__()

    def __str__(self):
        return self.data.__str__()

    @property
    def data(self):
        if self.proxied_data is None:
            self.proxied_data = self.func()
        return self.proxied_data
