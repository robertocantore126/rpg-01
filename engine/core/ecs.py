# engine/core/ecs.py
__all__ = ["Entity", "component", "system"]

from typing import Type, Dict, Any

# Registri globali
_ENTITY_REGISTRY: Dict[str, Type] = {}
_COMPONENT_REGISTRY: Dict[str, Type] = {}
_SYSTEM_REGISTRY: Dict[str, Dict[str, Any]] = {}


class Entity:
    def __init__(self, eid: int, world):
        self.id = eid
        self._world = world

    def add_component(self, comp):
        """Delegates to World.add_component()."""
        self._world.add_component(self.id, comp)
        return self

    def remove_component(self, comp_type: Type):
        self._world.remove_component(self.id, comp_type)

    def get_component(self, comp_type: Type):
        return self._world.components.get(comp_type, {}).get(self.id, None)

    def has_component(self, comp_type: Type) -> bool:
        return self.id in self._world._component_index.get(comp_type, ())

    def all_components(self):
        """Returns all components belonging to this entity."""
        return [
            comps[self.id]
            for ctype, comps in self._world.components.items()
            if self.id in comps
        ]

    def __repr__(self):
        return f"<Entity id={self.id} comps={[c.__name__ for c in self._world._component_index if self.id in self._world._component_index[c]]}>"


# ----------------------------
# Decorators
# ----------------------------
def entity(cls):
    """Marks a class as an Entity type."""
    _ENTITY_REGISTRY[cls.__name__] = cls
    cls.__is_entity__ = True
    return cls

def component(cls):
    """Marks a class as a Component type."""
    _COMPONENT_REGISTRY[cls.__name__] = cls
    cls.__is_component__ = True
    return cls

def system(*component_types, order: int = 0, parallel: bool = False, render: bool = False):
    def deco(fn):
        fn._ecs_req = tuple(component_types)   # tuple of component classes
        fn._ecs_order = order
        fn._ecs_parallel = parallel
        fn._ecs_render = render
        _SYSTEM_REGISTRY[fn.__name__] = {
            "func": fn,
            "components": component_types,
            "order": order,
            "parallel": parallel,
            "render": render
        }
        return fn
    return deco
