"""Singleton registry utility.

This registry provides an opt-in enforcement layer for classes that want to
ensure a single instance exists in a running process. Enforcement can be
disabled globally (useful for tests or multiple contexts) by setting the
environment variable ENGINE_ALLOW_MULTIPLE_SINGLETONS=1 or by calling
SingletonRegistry.set_enforce(False).

Usage:
    from engine.core.singleton import SingletonRegistry
    SingletonRegistry.register(instance, name="EventBus")
"""

__all__ = ["SingletonRegistry"]

import os
from typing import Dict, Optional


class SingletonRegistry:
    _instances: Dict[str, object] = {}
    # default enforcement can be toggled by env var at import time
    ENFORCE: bool = not bool(os.environ.get("ENGINE_ALLOW_MULTIPLE_SINGLETONS"))

    @classmethod
    def register(cls, instance: object, name: Optional[str] = None, enforce: Optional[bool] = None):
        key = name or f"{instance.__class__.__module__}.{instance.__class__.__name__}"
        if enforce is None:
            enforce = cls.ENFORCE
        if enforce and key in cls._instances:
            raise ValueError(f"Singleton instance already registered for '{key}'")
        cls._instances[key] = instance

    @classmethod
    def unregister(cls, name_or_instance: object):
        # Accept either the instance or the name
        if isinstance(name_or_instance, str):
            cls._instances.pop(name_or_instance, None)
            return
        # instance
        for k, v in list(cls._instances.items()):
            if v is name_or_instance:
                cls._instances.pop(k, None)
                return

    @classmethod
    def get(cls, name: str):
        return cls._instances.get(name)

    @classmethod
    def set_enforce(cls, value: bool):
        cls.ENFORCE = bool(value)
