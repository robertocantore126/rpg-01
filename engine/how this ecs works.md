# How this ECS works

> A concise but thorough guide to the ECS used in this engine — what parts exist, how they interact, how to use them, and best practices.
> Target audience: a developer who opens this project for the first time and needs a practical mental model + recipes to build game logic and rendering using the system.

---

## High-level philosophy

This ECS is a **pragmatic, hybrid ECS** designed to balance developer speed (OOP ergonomics) and runtime performance (component-indexed queries and systems). Key ideas:

* **World is the single source of truth.** The World owns entity IDs, component storage, component indexes, systems scheduling, and ties into the engine (GameContext/services).
* **Entities are lightweight handles.** An `Entity` instance is a convenient handle with an `id` and a reference to its `World`; the actual components live in the World’s component tables.
* **Components are plain data.** Use small classes / dataclasses that only hold state (no heavy logic). Components are referenced by type (class), not by string.
* **Systems are functions with metadata.** Systems are simple functions decorated with `@system(...)` that declare which component types they need, order and whether they are render or parallel-capable. This removes a thin class layer while keeping metadata.
* **Separation: logic vs render.** The World runs logic systems in `update()`. Rendering systems are run in `draw()` (separate phase) to guarantee correct draw order and layering.
* **Scene only coordinates.** A Scene (State) is responsible for configuring which systems are active, spawning initial entities, and scene-level transitions. Scenes do not hold game logic or draw entities directly.

---

## Main parts & responsibilities

### `World`

* Owns:

  * Entities map: `entities: Dict[eid, Entity]`
  * Component storage: `components: Dict[ComponentType, Dict[eid, component_instance]]`
  * Component index: `_component_index: Dict[ComponentType, Set[eid]]` (for fast queries)
  * Systems list: functions registered with `@system` (or active systems for a scene)
* Provides APIs:

  * `create_entity() -> Entity`
  * `destroy_entity(eid)`
  * `add_component(eid, comp_instance)`
  * `remove_component(eid, component_type)`
  * `view(*ComponentTypes)` → generator of `(eid, comp1, comp2, ...)`
  * `update(dt, active_systems=None)` → run logic systems
  * `draw(surface, active_systems=None)` → run render systems
* Emits ECS events to EventBus: `entity_spawned`, `entity_destroyed`, `component_added`, `component_removed`.

### `Entity`

* Lightweight wrapper created by `World.create_entity()`.
* Delegates `add_component`, `remove_component`, `get_component` to the World so the World can keep indexes consistent.
* Example: `e = world.create_entity(); e.add_component(Position(10,20))`

### `Component`

* Plain data classes or dataclasses. Minimal logic. Example:

```py
class Position:
    def __init__(self, x=0.0, y=0.0): self.x = x; self.y = y
```

### `System` (function)

* Declared with a decorator that records required component types, an order, whether it’s parallel, and optionally that it's a render system.
* Example decorator:

```py
@system(Position, Velocity, order=10, parallel=False)
def movement_system(dt, world, ents):
    for eid, pos, vel in ents:
        pos.x += vel.vx * dt
        pos.y += vel.vy * dt
```

* `ents` is produced by `world.view(Position, Velocity)`. Use `yield` to avoid building large lists.

### `Scene` (State)

* Holds `active_systems` (list of system functions) and manages entity spawning/despawning and scene lifecycle (`on_enter`, `on_exit`).
* Does not implement per-entity logic or draw entities directly; it coordinates which world systems run for this scene.

### `EventBus`

* Used to decouple systems and services. The World publishes component/entity lifecycle events. Systems publish game domain events (e.g., `damage_dealt`) that other systems or UI listen to.

---

## System registration and metadata

* Systems are functions annotated with `@system(*ComponentTypes, order=0, parallel=False, render=False)`.
* The decorator stores metadata on the function:

  * `fn._ecs_req` → tuple of component classes
  * `fn._ecs_order` → numeric order
  * `fn._ecs_parallel` → bool
  * `fn._ecs_render` → bool
* The decorator also registers the function in a global `_SYSTEM_REGISTRY` for discovery and ordering.

This pattern is Pythonic and safe: functions are objects and can carry attributes.

---

## The Query DSL: `view(...)`

* `world.view(A, B, C)` yields `(eid, a_instance, b_instance, c_instance)` for each entity that has all listed components.
* Implemented as a generator (uses `yield`) to avoid allocating big temporary lists — better memory and cache behavior when iterating many entities.
* Implementation pattern:

  1. For each requested component type, get the set of entity IDs from `_component_index`.
  2. Pick the smallest set as base to iterate.
  3. For each `eid` in base, check membership in the other sets; if present, yield `(eid, components[type][eid], ...)`.
* Example:

```py
for eid, pos, spr in world.view(Position, Sprite):
    # use pos and spr directly
```

---

## Update vs Draw phases (Rendering pipeline)

**We strongly recommend a two-phase per-frame pipeline:**

1. **Update phase (logic)** — `world.update(dt, active_systems)`

   * Run *logic systems only* (systems where `render=False`).
   * Movement, physics, AI, collisions, networking, spawning, etc.
   * Systems may schedule entity/component changes; those changes should be applied in a safe, deferred way (see "deferred modifications").

2. **Draw phase (render)** — `world.draw(surface, active_systems)`

   * Run *render systems* (systems where `render=True`).
   * Systems responsible for drawing do not run during `update()`; this guarantees background, world, FX, UI ordering is controlled by `order` numbers.
   * Example render systems (sorted by order):

     * `background_render_system` (order 0)
     * `shadow_system` (order 10)
     * `sprite_render_system` (order 20)
     * `particle_render_system` (order 30)
     * `ui_render_system` (order 100)

**Where Scene fits:**

* Scene’s `draw()` should not manually blit entities. Instead, Scene can:

  * Option A: call `world.draw(surface, scene.active_systems)` after drawing scene background.
  * Option B (preferred ECS-pure): spawn a background entity and let `background_render_system` draw it; scene only triggers `world.draw()` and configures active systems.
* The `GameContext.draw()` orchestrates: Scene background UI optional → `world.draw(vp.game_surface)` → viewport scaling → `display.flip()`.

---

## Lifecycle & flow of usage (step-by-step)

1. **Define component classes**

```py
class Position:  # data only
    def __init__(self, x=0, y=0): self.x = x; self.y = y
```

2. **Define systems**

```py
@system(Position, Velocity, order=10)
def movement_system(dt, world, ents):
    for eid, pos, vel in ents:
        pos.x += vel.vx * dt
```

For render systems:

```py
@system(Position, Sprite, order=20, render=True)
def sprite_render_system(surface, world, ents):
    for eid, pos, sprite in ents:
        surface.blit(sprite.image, (pos.x - camera.x, pos.y - camera.y))
```

3. **Add systems to registry**

* The decorator does it automatically. The World will read `_SYSTEM_REGISTRY` at initialization and produce order-sorted lists.

4. **Create a Scene**

* Scene defines `active_systems = [movement_system, sprite_render_system, ...]` or leaves it unset to use the entire registry.

5. **Spawn entities in the Scene**

```py
player = world.create_entity()
player.add_component(Position(100,200))
player.add_component(Velocity(0,0))
player.add_component(Sprite(player_image))
```

6. **Game loop**

* `GameContext.get_dt()` → compute dt
* `GameContext.get_events()` → input -> systems that produce input components or events
* `GameContext.update()`:

  * run input service
  * `scene_manager.update(dt)` (scene-level)
  * `world.update(dt, scene.active_systems)` → run logic systems
* `GameContext.draw()`:

  * scene may draw static overlays / background (preferably background is an entity)
  * `world.draw(surface, scene.active_systems)` → run render systems
  * viewport scaling + `pygame.display.flip()`

---

## Important implementation details & best practices

### Component ownership: World-only mutation

* **Do not mutate World component tables directly from Entity methods.** Let `Entity.add_component()` call `world.add_component()` internally. World must update `_component_index` for every addition/removal.
* This ensures consistent queries and prevents stale index issues.

### Deferred additions / removals

* If a system spawns or destroys entities or components while the World is iterating views, you must **defer** those operations until after the current system or frame. Implement:

  * `self._deferred_adds` and `self._deferred_removes` queues in World
  * apply them at the end of `update()` before the next system runs (or between systems if needed)
* This prevents "dictionary changed size" errors and keeps iteration stable.

### Mutability & threading

* Parallel systems are allowed **only** if they do not write the same components concurrently. Typical safe patterns:

  * parallel read-only systems
  * systems that write to distinct component types or disjoint entity sets
* Provide a mechanism to declare `fn._ecs_parallel = True` (via decorator).
* Use `ThreadPoolExecutor` to run parallel systems and await completion before executing sequential systems.

### Ordering & layering

* Use `.order` to control execution sequence and draw layering.
* Lower order runs earlier. Rendering: lower order = background, higher order = UI overlays.

### Debugging & tooling

* Provide these debugging aids:

  * `world.dump_components()` to log counts by type
  * `world.query_stats()` to list how many entities match a query
  * system execution profiler to log time spent per system
* Emit events like `component_added` & `entity_spawned` to EventBus to power editors and hot-reloaders.

### Performance tips

* Use `view()` with smallest set as base for intersection.
* Keep components small and POD-like.
* Group frequently-together components to minimize cache miss (later you can implement archetypes).
* Filter spatial queries via QuadTree before calling `view()` for spatial systems.
* Limit dynamic allocations in hot loops (avoid creating small temporary lists).

---

## Example snippets (concise)

**System decorator**

```py
_SYSTEM_REGISTRY = {}

def system(*component_types, order=0, parallel=False, render=False):
    def deco(fn):
        fn._ecs_req = tuple(component_types)
        fn._ecs_order = order
        fn._ecs_parallel = parallel
        fn._ecs_render = render
        _SYSTEM_REGISTRY[fn.__name__] = {
            "func": fn,
            "components": component_types,
            "order": order,
            "parallel": parallel,
            "render": render,
        }
        return fn
    return deco
```

**World.view (generator)**

```py
def view(self, *comp_types):
    if not comp_types: return
    sets = [self._component_index[ct] for ct in comp_types]
    base = min(sets, key=len)
    for eid in base:
        if all(eid in s for s in sets):
            yield (eid, *(self.components[ct][eid] for ct in comp_types))
```

**World.update/draw**

```py
def update(self, dt, active_systems=None):
    systems = active_systems or [info["func"] for info in _SYSTEM_REGISTRY.values()]
    systems = sorted(systems, key=lambda s: getattr(s, "_ecs_order", 0))
    # run logic-only systems
    for s in systems:
        if getattr(s, "_ecs_render", False): continue
        ents = self.view(*getattr(s, "_ecs_req", ()))
        s(dt, self, ents)
    self._apply_deferred()

def draw(self, surface, active_systems=None):
    systems = active_systems or [info["func"] for info in _SYSTEM_REGISTRY.values()]
    systems = sorted(systems, key=lambda s: getattr(s, "_ecs_order", 0))
    for s in systems:
        if not getattr(s, "_ecs_render", False): continue
        ents = self.view(*getattr(s, "_ecs_req", ()))
        s(surface, self, ents)
```

---

## Common pitfalls & FAQs

* **Q: Should components be dataclasses?**
  A: Dataclasses are convenient but keep components light. Use `__slots__` or simple classes if you need memory savings.

* **Q: Where to put camera logic?**
  A: Camera remains a service (because it handles viewport, smoothing, input) but `CameraFollowSystem` (reads `CameraTarget` component) can update it, bridging ECS and service.

* **Q: How to handle UI?**
  A: Model UI as ECS entities (UIElement, Anchor, Button) and create dedicated render and input systems. For complex UI frameworks you can keep a separate UI service that listens to ECS events.

* **Q: Can I mix OOP entities and ECS?**
  A: Avoid dual ownership. Use Entity prefab classes to spawn component sets, but runtime entity data must live in World.

---

## Where to start (quick checklist for a new scene)

1. Create component classes (Position, Sprite, Velocity, Health, etc.).
2. Create and decorate systems you need:

   * logic systems with `render=False`
   * render systems with `render=True`
3. Register scene: scene spawns entities with components.
4. Set `scene.active_systems` (or leave unset to use global defaults).
5. Ensure GameContext calls `world.update(dt, scene.active_systems)` during update and `world.draw(surface, scene.active_systems)` during draw.
6. Use `EventBus` for cross-cutting notifications (component_added etc.).
7. Add debug tools and deferred operation checks.

---

## Final words

This ECS is intentionally pragmatic: it gives you the **component-indexed query performance**, the **system modularity** and the **two-phase rendering pipeline** required for predictable visuals, while keeping development comfortable (systems are functions, components are classes). Start by modeling your gameplay as small components and small systems. Keep each system focused — one responsibility — and the engine will remain fast, flexible and easy to maintain.

If you'd like, I can also generate:

* a printable cheat-sheet with the most-used functions (`create_entity`, `add_component`, `view`, `@system` usage), or
* a minimal working example project (Pygame) that demonstrates a moving sprite, background, and UI drawn with the ECS pipeline.
