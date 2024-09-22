class LymboExceptionScopeHierarchy(Exception):
    """A shared resource is initialized in a higher scope than allowed."""

    pass


class LymboExceptionFilter(Exception):
    """The test collection filter is broken."""

    pass
