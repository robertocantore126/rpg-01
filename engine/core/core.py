# engine/core/core.py
__all__ = ["ServiceContainer", "GameContext", "Scene"]

# general
import time
import pygame
from abc import ABC, abstractmethod
from itertools import count
from typing import Any, Dict, Optional

# behaviour
from engine.behaviours.brain import Brain

# system
from engine.systems.achievements import AchievementManager
from engine.systems.collision_manager import CollisionManager
from engine.systems.debug_console import DebugConsole
from engine.systems.event_bus import EventBus
from engine.systems.input_manager import InputManager
from engine.systems.multiplayer import MultiplayerManager
from engine.systems.save import SaveManager
from engine.systems.scene_manager import SceneManager
from engine.systems.sounds import SoundManager
from engine.systems.state_manager import StateManager
from engine.systems.timers import TimersManager

# ui
from engine.ui.fonts import FontManager, Font
from engine.ui.ui_manager import UiManager

# world
from engine.world.camera_system import Camera, ViewportManager
from engine.world.chunk_manager import ChunkManager
from engine.world.constants import *
from engine.world.particle_manager import ParticleManager
from engine.world.shadow import ShadowCaster
from engine.world.sprites import SpriteManager
from engine.world.tilemap import TilemapManager
from engine.world.world import World
from engine.core.singleton import SingletonRegistry


class ServiceContainer:
    """
    Componenti opzionali da instanziare con dependecy injection (dal punto di vista di una scena)
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, key: str, instance: Any) -> None:
        """Register a service instance by key.

        Keyed services are available via `get` or `try_get`.
        """
        self._services[key] = instance

    def get(self, key: str) -> Any:
        """Return the registered service for `key`. Raises KeyError if missing."""
        return self._services[key]

    def try_get(self, key: str, default: Any = None) -> Any:
        """Return service or `default` if not present."""
        return self._services.get(key, default)
    

class GameContext:
    """
    Componenti basilari (necessari in ogni scena/state)
    """
    _ids = count(0)
    def __init__(self, game_name: str):
        pygame.init()
        pygame.display.set_caption(game_name)

        # Basic services
        self.services: ServiceContainer = ServiceContainer()
        self.event_bus: EventBus = EventBus()  # puoi anche registrarlo come servizio
        self.debugger: Optional[DebugConsole] = None # DebugConsole()
        self.scene_manager: SceneManager = SceneManager(self)
        self.state_manager: StateManager = StateManager()
        self.game_name: str = game_name

        # Global game data
        self.running, self.playing = True, True
        self.clock = pygame.time.Clock()
        self.dt, self.prev_time = 0, time.time()

        # Game specific
        self.scenes = {}
        self.id = next(self._ids)
        print(f"Game Context created with id: {self.id}")
        # register GameContext as an optionally-enforced singleton
        try:
            SingletonRegistry.register(self, name="engine.core.GameContext")
        except ValueError:
            # propagate so caller is aware if they intended strict singleton enforcement
            raise

        self._register_default_services()
        # after services are registered we may need to perform wiring between them
        self._post_service_wiring()

        # self.get_events = self.debugger.profile("GameContext.get_events")(self.get_events)
        # self.update = self.debugger.profile("GameContext.update")(self.update)
        # self.draw = self.debugger.profile("GameContext.draw")(self.draw)

    def get_dt(self) -> float:
        now = time.time()
        self.dt = now - self.prev_time
        self.prev_time = now
        self.clock.tick(FPS)
        return self.dt

    def get_events(self) -> None:
        """Invoke input handling for the current frame."""
        self.services.get("inputs").update()

    def update(self) -> None:
        # Inputs, events, scenes and timers run every tick
        self.services.get("inputs").update()    # InputManager
        self.event_bus.dispatch()               # EventBus
        self.scene_manager.update(self.dt)      # SceneManager
        self.services.get("timers").update(     # TimersManager
            self.dt,
            self.state_manager.paused())

        self.services.get("world")\
            .update(self.dt, self.scene_manager.get_current_scene().active_systems)  # type: ignore # World (ECS systems)

        if self.debugger:
            self.debugger.log("FPS", self.clock.get_fps())
            self.debugger.log("Ticks", self.clock.get_rawtime()) 
            self.debugger.mark_frame()   # this should probably be in the game_loop and not in update
    
    def draw(self) -> None:
        vp = self.services.get("viewport")
        self.scene_manager.draw(vp.game_surface)            # Each scene draw-call (scene)
        self.services.get("world").draw(vp.game_surface)    # World (ECS render systems)

        vp.draw(vp.screen)                                  # final scale step

        if self.debugger:
            self.debugger.render_overlay(vp.game_surface)   # Debug view (inactive)

        pygame.display.flip()

    def game_loop(self) -> None:
        """Main game loop. Blocks until `playing` becomes False."""
        while self.playing:
            self.get_dt()
            self.get_events()
            self.update()
            self.draw()
            
    def register_modules(self, **kwargs) -> None:
        """
        Registra moduli del gioco in blocco.
        Accetta: scenes, entities, systems, constants, assets
        """
        self.scenes.update(kwargs.get("scenes", {}))

        # registra tutte le scene annotate
        for name, cls in self.scenes.items():
            self.scene_manager.register(name, cls)
            print(f"[core] Registered scene: {name}, {cls}")
        
        name, cls = next(iter(self.scenes.items()))
        instance = self.scene_manager.create(name, ctx=self)
        self.scene_manager.push(instance)

    def _register_default_services(self) -> None:
        """
        Registra servizi iniziali usando factory per gestione di dipendenze/config.
        Ogni factory è una callable che riceve il context self e restituisce il servizio.
        """
        DEFAULT_SERVICES = {
            # Behaviours
            "brain":        lambda ctx: Brain(self.event_bus),

            # Systems
            "achievement":  lambda ctx: AchievementManager(self.event_bus),
            "collisions":   lambda ctx: CollisionManager(self.event_bus),           # TODO: fix module, integrate with World
            # "cutscenes":    lambda ctx: CutsceneManager(),                        # TODO: fix module, may need to be initialized after World
            "inputs":       lambda ctx: InputManager(self.event_bus),
            "multiplayer":  lambda ctx: MultiplayerManager(),                       # TODO: fix module, needs testing
            "timers":       lambda ctx: TimersManager(), # needs to be before the SaveManager
            "save":         lambda ctx: SaveManager(ctx),
            "sounds":       lambda ctx: SoundManager(),

            # World
            "camera":       lambda ctx: Camera(GAME_W, GAME_H, SCREEN_WIDTH, SCREEN_HEIGHT, camera_type="soft"),
            "viewport":     lambda ctx: ViewportManager(GAME_W, GAME_H, SCREEN_WIDTH, SCREEN_HEIGHT),
            "chunks":       lambda ctx: ChunkManager(CHUNK_SIZE),                   # TODO: fix module, integrate with world
            # "navigation":   lambda ctx: AgentController(),                        # TODO: fix module
            "particles":    lambda ctx: ParticleManager(),
            # "pg_assembly":  lambda ctx: WFCSolver(),                              # TODO: fix module
            # "pg_graph":     lambda ctx: RoomManager(),                            # TODO: fix module
            # "pg_stitching": lambda ctx: RoomStitcher(),                           # TODO: fix module
            "shadows":      lambda ctx: ShadowCaster(),                             # TODO: fix module, needs testing
            "sprites":      lambda ctx: SpriteManager(),
            "tilemap":      lambda ctx: TilemapManager(),
            "world":        lambda ctx: World(ctx, GAME_W, GAME_H),

            # UI - needs .convert(), is created after Viewport where we pygame.display.setmode(...)
            "font_manager": lambda ctx: FontManager(),
            "small_font":   lambda ctx: Font("assets/fonts/small_font_dfp.png"),
            "large_font":   lambda ctx: Font("assets/fonts/large_font_dfp.png"),
            "ui_manager":   lambda ctx: UiManager(self.event_bus),                  # TODO: fix module
        }

        for key, factory in DEFAULT_SERVICES.items():
            instance = factory(self)
            self.services.register(key, instance)

    def _post_service_wiring(self) -> None:
        """Hook to perform wiring between services after registration."""
        pass

    def run(self) -> None:
        print(f"[core] Running {self.game_name}...")
        # qui avvii loop principale, inizializzi scene ecc.
        while self.running:
            self.game_loop()

        pygame.quit()
        sys.exit()


class Scene(ABC):
    def __init__(self, ctx: GameContext, name: str = ""):
        self.name = name
        self.ctx = ctx

    @abstractmethod
    def on_enter(self, payload=None): pass
    @abstractmethod
    def update(self, dt: float): pass
    @abstractmethod
    def draw(self, surface): pass
    @abstractmethod
    def on_exit(self): pass
    @abstractmethod
    def on_pause(self): pass
    @abstractmethod
    def on_resume(self): pass


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
