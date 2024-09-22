from multiprocessing.managers import DictProxy
import queue
from typing import Union

from lymbo.cm import args
from lymbo.cm import expand
from lymbo.cm import test
from lymbo.resource_manager import scope_class
from lymbo.resource_manager import scope_function
from lymbo.resource_manager import scope_global
from lymbo.resource_manager import scope_module

__version__ = "0.2.0"

__all__ = [
    "args",
    "expand",
    "test",
    "scope_class",
    "scope_function",
    "scope_global",
    "scope_module",
]


_local_resources: Union[dict, None] = None
_shared_queue: Union[queue.Queue, None] = None
_shared_scopes: Union[DictProxy, None] = None
