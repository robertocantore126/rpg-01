Engine TODOs and Known Issues

This file lists the immediate known problems, rationale, and planned next steps. Keep it concise and actionable.

1) ECS / Entity ownership
 - Issue: Entities are duplicated between `EntityManager` and `World` when both exist. `EntityManager` has a facade mode but some systems may still directly use `EntityManager.entities`.
 - Plan: Continue to make `World` authoritative. Replace any direct `EntityManager.entities` access across the codebase with `world` queries. Add deprecation warnings on EntityManager when used without a world.

2) Initialization ordering & wiring
 - Issue: Several systems have implicit ordering requirements (Timers -> Save, Viewport -> UiManager).
 - Plan: Document the order in `engine_usage.txt` (done). Implement a small dependency graph in `GameContext` to refuse inconsistent wiring if needed.

3) QuadTree / spatial index
 - Issue: Full rebuilds are expensive if called every frame.
 - Plan: Expose and use incremental operations: `add_to_quadtree`, `remove_from_quadtree`, `update_in_quadtree`. Add 'dirty' batching option to apply updates at frame-end.

4) Sound & audio fallbacks
 - Issue: Headless or misconfigured systems crash on pygame.mixer init.
 - Plan: Keep current try/except and an `audio_available` flag; add a concise warning log on init failure and fallback no-op implementations for play functions.

5) SaveManager registry
 - Issue: Mixed primitive/object saves made save format confusing.
 - Plan: Keep the `_registry` for objects and `_primitives` for simple values. Add migration helper to adopt older save files.

6) PhysicsEntity and movement model (planned work)
 - Issue: Current PhysicsEntity is minimal. We need a robust physics-capable entity supporting separated X/Y movement and multiple force inputs (gravity, applied forces, impulses, friction, drag).
 - Plan: Implement a `Physics` component (or merge into Entity) that provides:
    - velocity (vx, vy), acceleration, forces accumulator
    - apply_force(vec), apply_impulse(vec), apply_friction(coef)
    - integrate(dt) using semi-implicit Euler (integrate velocity from acceleration, then position from velocity)
    - separate axis resolution helpers so horizontal and vertical movement can be handled independently in collision resolution

7) Tests
 - Issue: Existing tests were under `tests/engine` and not organized within the package.
 - Plan: Continue expanding tests under `engine/tests` with clear subfolders: `systems/`, `world/`, `behaviours/`, `ui/`. Add unit tests for SaveManager, SoundManager (using audio_available mock), and input flow.

8) Type hints
 - Issue: Partial type hints added; more coverage required across modules.
 - Plan: Perform a sweep to add argument/return type hints to public functions and classes. Prioritize `engine/` modules and tests, then expand to `game/`.

9) Misc / Low priority
 - Improve logging (use Python logging module instead of prints)
 - Add a lightweight CI script and requirements file
 - Create small sample scene (player + input) for manual smoke testing

If you want, I can start implementing item 6 (PhysicsEntity) next. I will implement it as a Physics component tightly integrated with `Entity` and update `EntityManager`/`World` usage to support either plain Entity or physics-enabled Entity.
