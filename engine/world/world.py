# world.py
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import itertools
import pygame
from typing import Any, Dict, List, Set, Type

from engine.core.ecs import _ENTITY_REGISTRY, _SYSTEM_REGISTRY, Entity
from engine.world.constants import ECSEvent
from engine.world.pathfinding import PathfindingManager
from engine.world.quadtree import QuadTree

__all__ = ["World"]

# ===============================
# ECS Light World
# ===============================
class World:
    def __init__(self, ctx, width, height, quadtree_capacity=4):
        if ctx is None: raise ValueError("World requires a context (ctx) for proper initialization.")
        self.ctx = ctx

        # ecs
        self.entities: Dict[int, Entity] = {}                # id -> entity
        self.components: Dict[Type, Dict[int, Any]] = defaultdict(dict)  # ComponentType -> {eid: comp}
        self._component_index: Dict[Type, Set[int]] = defaultdict(set)  # ComponentType -> set(eid)
        self._next_eid = itertools.count()
        
        self.systems = []
        self._build_systems()

        # Spatial index
        self.quadtree = QuadTree(pygame.Rect(0,0,width,height), capacity=quadtree_capacity)

        # Pathfinding
        self.pathfinding = PathfindingManager()

    # --- Entity & Components ---
    def _build_systems(self):
        """Crea istanze dei sistemi registrati e li ordina."""
        for name, info in _SYSTEM_REGISTRY.items():
            fn = info["func"]
            fn._ecs_req = info["components"]
            fn._ecs_order = info["order"]
            fn._ecs_parallel = info["parallel"]
            self.systems.append(fn)
        self.systems.sort(key=lambda s: getattr(s, "_ecs_order", 0))

    def create_entity(self) -> Entity:
        eid = next(self._next_eid)
        ent = Entity(eid, self)
        self.entities[eid] = ent
        self.ctx.event_bus.publish(ECSEvent.ENTITY_SPAWNED, data=ent)
        return ent

    def add_entity(self) -> Entity:
        """
        self.player = world.add_entity(
            Entity(
                Component1,
                Component2,
                ...
            )
        )
        """
        ...

    def spawn(self, entity_name: str) -> Entity:
        if entity_name not in _ENTITY_REGISTRY:
            raise KeyError(f"Entity type '{entity_name}' not registered.")
        cls = _ENTITY_REGISTRY[entity_name]
        ent = self.create_entity()
        for comp in getattr(cls, "components", []):
            ent.add_component(comp)
        return ent

    def remove_entity(self, eid: int):
        # remove all components
        for ctype in list(self.components.keys()):
            self.remove_component(eid, ctype)
        self.entities.pop(eid, None)
        self.ctx.event_bus.publish(ECSEvent.ENTITY_REMOVED, entity_id=eid)
        self.remove_from_quadtree(eid)

    def add_component(self, eid: int, comp):
        ctype = type(comp)
        self.components[ctype][eid] = comp
        self._component_index[ctype].add(eid)
        self.ctx.event_bus.publish(ECSEvent.COMPONENT_ADDED, data={"entity_id":eid, "component":comp})

    def remove_component(self, eid: int, comp_type: Type):
        self.components[comp_type].pop(eid, None)
        self._component_index[comp_type].discard(eid)
        self.ctx.event_bus.publish(ECSEvent.COMPONENT_REMOVED, entity_id=eid, component_type=comp_type)

    def update(self, dt, active_systems=None):
        systems = active_systems or self.systems
        parallel, sequential = [], []

        for s in systems:
            if getattr(s, "_ecs_parallel", False):
                parallel.append(s)
            else:
                sequential.append(s)

        with ThreadPoolExecutor() as pool:
            [pool.submit(s, dt, self, self.view(*s._ecs_req)) for s in parallel]

        for s in sequential:
            s(dt, self, self.view(*s._ecs_req))

    def draw(self, surface):
        for s in sorted(self.systems, key=lambda s: s._ecs_order):
            if getattr(s, "_ecs_render", False):
                ents = self.view(*s._ecs_req)
                s(surface, self, ents)

    def view(self, *comp_types):

        if not comp_types: raise ValueError("view() requires at least one component type.")
        # start with smallest set for intersection efficiency
        sets = [self._component_index[ct] for ct in comp_types]
        if not sets:
            raise ValueError("No entities with the specified components.")
        base = min(sets, key=len)
        for eid in base:
            if all(eid in s for s in sets):
                yield (eid, *(self.components[ct][eid] for ct in comp_types))

    # --- Spatial Queries ---
    def rebuild_quadtree(self):
        # # Full rebuild
        # self.quadtree = QuadTree(self.quadtree.bounds, self.quadtree.capacity, max_depth=self.quadtree.max_depth)
        # # store rect cache for incremental updates
        # self._spatial_idx = {}
        # for eid in self.get_entities_with("position", "collider"):
        #     pos = self.components["position"][eid]
        #     col = self.components["collider"][eid]
        #     rect = pygame.Rect(pos["x"], pos["y"], col["w"], col["h"])
        #     self.quadtree.insert(eid, rect)
        #     self._spatial_idx[eid] = rect
        pass

    def add_to_quadtree(self, eid: int):
        # """Add a single entity to the quadtree and index it."""
        # pos = self.components["position"].get(eid)
        # col = self.components["collider"].get(eid)
        # if pos and col:
        #     rect = pygame.Rect(pos["x"], pos["y"], col["w"], col["h"])
        #     self.quadtree.insert(eid, rect)
        #     self._spatial_idx[eid] = rect
        pass

    def remove_from_quadtree(self, eid: int):
        # if hasattr(self, "_spatial_idx") and eid in self._spatial_idx:
        #     self.quadtree.remove(eid)
        #     del self._spatial_idx[eid]
        pass

    def update_in_quadtree(self, eid: int):
        # """Update an entity's position in the quadtree incrementally."""
        # if "position" in self.components and "collider" in self.components:
        #     pos = self.components["position"].get(eid)
        #     col = self.components["collider"].get(eid)
        #     if pos and col:
        #         rect = pygame.Rect(pos["x"], pos["y"], col["w"], col["h"])
        #         # check previous rect
        #         prev = getattr(self, "_spatial_idx", {}).get(eid)
        #         # pygame.Rect equality checks all fields (position and size).
        #         # If you only care about position or size changes, adjust the comparison below.
        #         if prev and prev == rect:
        #             return
        #         # check previous rect
        #         prev = self._spatial_idx.get(eid)
        #         if prev and prev == rect:
        #             return
        #         # otherwise remove and insert again
        #         if prev:
        #             self.quadtree.remove(eid)
        #         self.quadtree.insert(eid, rect)
        #         self._spatial_idx[eid] = rect
        pass
    
    def query_area(self, rect: pygame.Rect) -> List[int]:
        return self.quadtree.query(rect)

    # --- Pathfinding ---
    def set_grid_for_pathfinding(self, grid, cell_size):
        self.pathfinding.set_grid(grid, cell_size)

    def set_graph_for_pathfinding(self, graph):
        self.pathfinding.set_graph(graph)

    def find_path(self, start, goal):
        return self.pathfinding.find_path(start, goal)
