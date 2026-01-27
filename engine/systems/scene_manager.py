# engine/scene_manager.py

__all__ = ["SceneManager"]

from engine.world.constants import BATTLESHIP_GRAY


class SceneManager:
    """
    Use a .create() and .push() API to add new scene.
    Use other methods to navigate created ones. 
    """
    def __init__(self, ctx):
        self.ctx = ctx
        self._scenes = {}
        self.scene_stack = []
        self.prev_scene = None
        self.next_scene = None

        self._scene_zero()

    def _scene_zero(self):
        class SceneZero:
            def __init__(self, ctx) -> None:
                self.count = 0
                self.ctx = ctx

            def on_enter(self):
                pass

            def update(self, _dt):
                if self.count > 2:
                    return
                print("Updating Scene 0")
                self.count += 1

            def draw(self, screen):
                screen.fill(BATTLESHIP_GRAY)

            def on_pause(self): pass
        self.register("zero", SceneZero)
        zero_scene = self.create("zero", self.ctx)
        self.push(zero_scene)

    def register(self, name, cls):
        self._scenes[name] = cls

    def create(self, name, *args, **kwargs):
        if name not in self._scenes:
            raise KeyError(f"Scene {name} non registrata")
        return self._scenes[name](*args, **kwargs)

    def push(self, scene):
        if self.scene_stack:
            self.scene_stack[-1].on_pause()
        self.scene_stack.append(scene)
        scene.on_enter()

    def pop(self):
        if not self.scene_stack:
            return
        scene = self.scene_stack.pop()
        scene.on_exit()
        self.prev_scene = scene
        if self.scene_stack:
            self.scene_stack[-1].on_resume()

    def switch(self, scene):
        self.pop()
        self.push(scene)    # TODO: ends up calling on pause on 2 scenes prior. may or may not be a problem

    def get_current_scene(self):
        if self.scene_stack:
            return self.scene_stack[-1]
        return None

    def preload_next(self, scene):
        """Precarica una scena (next_scene), senza attivarla subito."""
        self.next_scene = scene

    def activate_next(self):
        """Attiva la scena precaricata."""
        if self.next_scene:
            self.switch(self.next_scene)
            self.next_scene = None

    def update(self, dt):
        if self.scene_stack:
            self.scene_stack[-1].update(dt)

    def draw(self, screen):
        if self.scene_stack:
            self.scene_stack[-1].draw(screen)
        else:
            raise ValueError("Scene stack should not be empty")
