#engine/core/__init__.py
from .core import *
from .ecs import *
from .singleton import *

__all__ = []
__all__ += core.__all__
__all__ += ecs.__all__
__all__ += singleton.__all__
