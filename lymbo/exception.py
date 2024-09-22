class LymboExceptionScopeHierarchy(Exception):
    """A shared resource is initialized in a higher scope than allowed."""

    pass


class LymboExceptionScopeNested(Exception):
    """A shared resource is initialized from another shared resource."""

    pass


class LymboExceptionFilter(Exception):
    """The test collection filter is broken."""

    pass
