__all__ = ["InputManager"]
import pygame, sys, json, os
from engine.world.constants import EventType, GAME_H, GAME_W, SCREEN_WIDTH, SCREEN_HEIGHT

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "input_config.json")


class InputManager:
    def __init__(self, event_bus, config_path: str | None = None):
        self.event_bus = event_bus
        # explicit config path (override for tests)
        self.config_path = config_path or CONFIG_PATH
        # load config (dict) from file; keep config as dict for runtime use
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception:
            # fallback to empty config to avoid crashing on missing file
            self.config = {"keys": {}, "mouse": {}}

        self.keys = {}
        self.mouse_buttons = {}
        self.mouse_pos = (0, 0)

        self.active_keys = set()

        # stats per salvataggi
        self.stats = {"total": {}, "session": {}}

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.event_bus.publish(EventType.QUIT)
                pygame.quit()
                sys.exit()

            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                key_name = pygame.key.name(event.key)
                action = self.config.get("keys", {}).get(key_name)
                if event.type == pygame.KEYDOWN: 
                    print(f"[input] Pressed key {pygame.key.name(event.key)}")
                    self.active_keys.add(pygame.key.name(event.key))
                else:
                    self.active_keys.discard(pygame.key.name(event.key))
                    
                if action:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                        self.event_bus.publish(EventType.KEY_DOWN, action)
                        self._record_key(action)
                    else:                        
                        self.event_bus.publish(EventType.KEY_UP, action)

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                btn = str(event.button)
                action = self.config.get("mouse", {}).get(btn)
                if action:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.event_bus.publish(EventType.MOUSE_BUTTON_DOWN, {"action": action, "pos": self.get_mouse_pos_game()})
                        # print("[input] Mouse keydown fired")
                        self._record_key(action)
                    else:
                        self.event_bus.publish(EventType.MOUSE_BUTTON_UP, {"action": action, "pos": self.get_mouse_pos_game()})

            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                self.event_bus.publish(EventType.MOUSE_MOVE, {"pos": event.pos})

    def _record_key(self, action):
        self.stats["total"][action] = self.stats["total"].get(action, 0) + 1
        self.stats["session"][action] = self.stats["session"].get(action, 0) + 1

    def get_mouse_pos_game(self):
        mx, my = pygame.mouse.get_pos()
        return int(mx * GAME_W / SCREEN_WIDTH), int(my * GAME_H / SCREEN_HEIGHT)

    def to_game_coords(self, pos):
        mx, my = pos
        return int(mx * GAME_W / SCREEN_WIDTH), int(my * GAME_H / SCREEN_HEIGHT)

    # ---------------- SAVE ----------------
    def export_history(self):
        return self.stats

    def reset_session_history(self):
        self.stats["session"] = {}

    # ---------------- CONFIG ----------------
    def _reload_config(self):
        """
        The saved config is automatically loaded on instantiation.
        This function is meant to be called when the user makes runtime changes to it,
        to reload the saved configuration and update the changes. 
        """
        # reload from path
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception:
            # keep existing config if reload fails
            pass
        return self.config

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            # could log a warning; for now we silently ignore to avoid crashing
            pass

    def update_config(self, input_type, key, action):
        """
        Used to update the config at runtime with user changes.
        The updated config needs to be saved before becoming effective.
        """
        pass
