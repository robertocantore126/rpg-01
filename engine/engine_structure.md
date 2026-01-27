# Engine structure overview

This document summarizes the architecture of the `engine/` package, how its major modules interact, and suggests concrete improvements, missing features, and areas for extension.

## High-level components (table)

| Area | Key modules / classes | Responsibility | Interactions (who depends on who) |
|---|---|---:|---|
| Core / Glue | `core/core.py` (GameContext, ServiceContainer, State) | Bootstraps pygame, holds global services, runs game loop, registers scenes/systems | Creates & registers services from `systems/`, `behaviours/`, `ui/`, `world/`. Uses `SceneManager` to manage scenes.
| Services / Systems | `systems/*` (EventBus, InputManager, TimersManager, SaveManager, SoundManager, SceneManager, etc.) | Game-wide systems: event dispatch, input processing, timing, save, sound, scene/state handling | EventBus is central: many systems publish/subscribe to `EventType`. `InputManager` publishes inputs consumed by `UiManager`, game logic, world. `TimersManager` used by SaveManager. `SceneManager` interacts with `GameContext` and scenes.
| Behaviour | `behaviours/*` (Brain, BehaviourTree, FSM, GOAP, Blackboard) | AI & decision-making abstractions for NPCs/agents | `Brain` registers strategies and is provided as a service in GameContext. Behaviour trees / FSM intended to be used by enemy entities or NPC controllers.
| World / ECS | `world/world.py`, `world/entity.py`, `world/tilemap.py`, `world/*` | Light ECS, spatial indexing (QuadTree), pathfinding, tilemap loading and rendering, entity management | `World` is provided as a service. Systems like CollisionManager should integrate with World components; EntityManager provides higher-level entity wrappers. TilemapManager provides maps/tiles for rendering and collision.
| UI | `ui/ui_manager.py`, `ui/fonts.py` | UI components (Label, Button, Container, HealthBar, DialogBox) and manager that listens to `EventBus` | `UiManager` subscribes to `EventBus` mouse events and publishes UI events (e.g., UI_BUTTON_CLICKED). Ui components call back to EventBus.


## Textual interaction diagram (simplified)

- `GameContext` boots and creates a `ServiceContainer`.
- `_register_default_services` in `GameContext` instantiates services (EventBus, InputManager, TimersManager, World, EntityManager, UiManager, etc.) and registers them in `ServiceContainer`.
- `InputManager` polls `pygame.event.get()` and publishes `EventType` events to `EventBus`.
- `UiManager` subscribes to mouse-related events on `EventBus` and routes input to UI components; UI components publish UI-specific events back to `EventBus`.
- `SceneManager` holds active scene instances; `GameContext.update()` calls `scene_manager.update(dt)` and `scene_manager.draw(...)`.
- `World` holds components and quadtree for spatial queries; collision / physics systems should query `World.quadtree`.
- `Brain` (behaviours) can be used by entities/AI systems; behaviour trees, FSMs and GOAP planner provide different AI paradigms.
- `TimersManager` provides timers that publish events on expiry. `SaveManager` uses TimersManager to schedule autosaves.


## Notable design choices and conventions observed

- ServiceFactory pattern: `GameContext._register_default_services` uses lambdas to lazily instantiate services and register them with keys.
- Event-driven architecture: `EventBus` with typed events (`EventType`) is the primary decoupling mechanism.
- Lightweight ECS: `World` provides component maps and helper `ComponentStore` for entity-component storage, while `entity.py` contains higher-level `Entity` / `EntityManager` wrappers. This results in two parallel ways to manage entities/components (potential duplication).
- UI system assumes events are already translated to "game canvas" coordinates.
- Behaviour package implements multiple paradigms (BT/FSM/GOAP) and includes an utility to build BT from a config.


## Concrete issues, code smells and improvements (grouped)

- Duplication: two component APIs
  - `world.World` (component dicts + ComponentStore) and `EntityManager`/`Entity` both model entities/components. This can confuse ownership and cause duplicated data. Recommendation: pick one authoritative ECS (World/ComponentStore or EntityManager) and adapt others as lightweight facades.

- Singletons enforced by id checks
  - Several classes check `if self.id != 0: raise ValueError("There should only be one GameContext instance")` (EventBus, GameContext.dispatch, etc.). This is brittle for tests and multi-context scenarios. Prefer explicit singletons or allow multiple instances (remove checks) or use a formal Singleton pattern.

- Tight coupling & ordering assumptions
  - `_register_default_services` has many TODOs and commented-out modules; some services assume other services exist and order matters (timers before save). Consider resolving dependencies explicitly (e.g., factory functions receive `ctx` and call `ctx.services.try_get(...)`) and delay some initializations or use lazy properties.

- EventBus dispatch loop
  - `EventBus.dispatch()` iterates subscribers for the specific event, then separately iterates `ALL_EVENTS`. This may be fine but an early return or consolidated iteration would be simpler. Also, dispatch raises ValueError if `self.id != 0` which mirrors the single-instance issue.

- InputManager: config handling and error-prone file operations
  - `CONFIG_PATH` usage and `_reload_config` assume `self.config` is a Path-like or has .exists(). But in __init__ `self.config` is a plain dict. `_reload_config` thus has a bug (calls self.config.exists()). `save_config` writes `self.config` but uses `with open(self.config, "w")` — wrong type. Fix by storing `self.config_path` and `self.config` separately.

- TimersManager: event bus call
  - `Timer.update` calls `self.event_bus.publish(self.event_type, **self.payload)` but `EventBus.publish` expects (event_type, data=None) so this mismatch will break (extra kwargs). Also the conditional `if self.event_bus and not self.event_bus:` is always False; appears to be a mistake.

- SaveManager.register uses objects directly in internal `self.data` and on save iterates expecting either primitives or objects with .save_state; mixing types makes load/save code complicated. Use a dedicated registry mapping keys to objects and exclude primitives or treat primitives as simple values.

- SoundManager: using `pygame.mixer.init()` in constructor can throw if audio isn't available or in headless CI. Wrap init in try/except and defer loading.

- Tilemap/Tileset loader: hard assumptions about filename format and tile dimensions, and eager loading of all tilesets at init could be heavy. Consider adding error handling and lazy loading.

- BehaviourTree/Brain: `Brain.register_enemy` uses `BehaviourTree(Node())` as placeholder for BT; constructing a Node() is abstract. This looks like an incomplete implementation and may raise errors. Also Brain currently stores strategies in a dict but doesn't handle lifecycle (on destroy/unregister cleanup).

- UI: UI code is fairly well-factored, but some inefficiencies exist (Label always re-renders text on every draw; caching is present but not used to skip re-render when text hasn't changed). `FloatingText.update` uses integer millis and `draw` uses alpha conversion each frame — acceptable but could be optimized.

- World.QuadTree: insert stores rects and compares using bounds.colliderect(rect) — okay, but rebuilding quadtree each frame in World.rebuild_quadtree may be expensive if done frequently. Consider incremental updates or marking dirty regions.


## Suggested missing features and extensions

- Automated dependency resolver for services
  - Instead of requiring order in `_register_default_services`, make factories take `ctx` and resolve services lazily (use ctx.services.try_get) and allow marking dependencies. Or use a small DI container that performs topological ordering.

- Tests and type hints
  - Add unit tests for EventBus, TimersManager, QuadTree, Tilemap parsing, InputManager config. Add type hints where missing (some files already use typing). Use `mypy` for type checking.

- Better ECS: unify component model
  - Consolidate to `ComponentStore` + `World` as authoritative ECS and make `EntityManager` a convenience wrapper that uses `World` internals.

- Profiling & debug utilities
  - Add optional profiler hooks (GameContext.debugger is present but unused). Provide toggles to visualize quadtree, FPS, timers, event queue length.

- Robust asset loading
  - Defer asset-heavy operations (tileset slicing, sound loads) and add graceful fallback / missing asset logging.

- Documentation & diagrams
  - Add `engine/engine_structure.md` (this file) and consider adding a small diagram (ASCII or plantuml) for component interactions. Add module-level docstrings to clarify responsibilities.


## Concrete quick fixes (prioritized)

1. Fix `InputManager` config path handling: store `self.config_path` and use it in `_reload_config` / `save_config`. Validate JSON and fallback safely.
2. Fix `Timer.update` publish call signature: `self.event_bus.publish(self.event_type, self.payload)` and fix the nonsensical conditional.
3. Make `EventBus.dispatch` not assert on `self.id` (or remove check) to allow tests and multiple contexts; consider moving single-instance enforcement to GameContext.
4. Fix `Brain.register_enemy` to not instantiate `BehaviourTree(Node())` but require a proper tree or factory. Add validation.
5. Wrap `pygame.mixer.init()` in try/except and make sound loading lazy.
6. Rework `SaveManager` data storage to keep a registry mapping keys to saveable objects, not mixed types.


## Files/areas to inspect or refactor next (recommended roadmap)

- systems/collision_manager.py — integrate with `World.quadtree` and `World.components` and confirm that collision detection/response is correct and efficient.
- behaviours/goap.py and fsm.py — add tests and ensure API parity with Brain expectations (e.g., `update(dt)` method signatures).
- world/proc_gen_* — these modules are referenced but TODO in core: verify they are functional or stubbed.
- ui/fonts.py — ensure font management handles missing fonts and supports both sprite-fonts and system fonts.


## Quick mapping of issues -> remediation effort

- Low effort (1-2 hours): InputManager config bug; Timer publish bug; EventBus dispatch cleanup; SoundManager defensive init.
- Medium effort (1-2 days): Unify ECS patterns, add tests for QuadTree/Pathfinding, add lazy asset loading.
- Large effort (several days+): Full DI container, refactor of systems to use World ECS fully, implement robust save/load lifecycle and migration.


## Final notes

I inspected key modules under `engine/` and assembled this document to explain structure and prioritize fixes.

If you want, I can now:
- apply the quick fixes automatically (I can create small patches for the InputManager, Timer, EventBus, SaveManager and SoundManager),
- or add unit tests for the EventBus and TimersManager to lock behavior before refactors,
- or generate UML/sequence diagrams for the GameContext lifecycle.

**********************

GameContext.update()
 ├─ SceneManager.update()
 ├─ World.update()  ← qui gira anche render_system()
GameContext.draw()
 ├─ SceneManager.draw()  ← background disegnato qui

