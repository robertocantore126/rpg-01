__all__ = ["SaveManager"]

import json
import os
from typing import Dict, Any
from engine.systems.event_bus import EventBus
from engine.world.constants import EventType

class SaveManager:
    def __init__(self, ctx, filepath=None):
        if filepath is None:
            base_dir = os.path.join(os.path.dirname(__file__), "configs")
            filepath = os.path.join(base_dir, "save.json")
        self.filepath = filepath
        # registry: key -> saveable object (must implement save_state/load_state)
        self._registry: Dict[str, Any] = {}
        # primitives stored directly
        self._primitives: Dict[str, Any] = {}

        # Save manager
        self.eb = ctx.event_bus
        self.tm = ctx.services.get("timers")
        
        self.save_timer = self.tm.new_timer(
            duration=30,
            repeat=True,
            event_bus=self.eb,
            event_type=EventType.SAVE_GAME,
            payload={},
            ignore_pause=True,
        )
        self.tm.add_timer("autosave", self.save_timer).start()
        # subscribe to save event; the callback accepts a single optional event argument
        self.eb.subscribe(EventType.SAVE_GAME, lambda ev=None: self.save())

    def register(self, key: str, obj):
        """
        Registra un oggetto che implementa save_state() e load_state().
        key = sezione del salvataggio, es. "player", "inventory"
        """
        if not hasattr(obj, "save_state") or not hasattr(obj, "load_state"):
            raise ValueError(f"Object {obj} must implement save_state() and load_state()")
        self._registry[key] = obj

    def register_value(self, key: str, value):
        """Register a simple primitive value (int/str/bool/float) to be saved as-is."""
        self._primitives[key] = value

    def save(self):
        """Salva tutti i dati registrati nel file JSON"""
        save_dict = {}
        # primitives first
        for k, v in self._primitives.items():
            save_dict[k] = v
        # then saveable objects
        for k, obj in self._registry.items():
            try:
                save_dict[k] = obj.save_state()
            except Exception:
                # skip problematic entries to avoid losing all data
                pass
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(save_dict, f, indent=4)
            print(f"[SaveManager] Game saved to {self.filepath}")
        except Exception:
            print(f"[SaveManager] Failed to write save file: {self.filepath}")

    def load(self):
        """Carica i dati dal file JSON e li passa agli oggetti registrati"""
        if not os.path.exists(self.filepath):
            print("[SaveManager] No save file found.")
            return
        with open(self.filepath, "r", encoding="utf-8") as f:
            save_dict = json.load(f)
        # load primitives
        for k in list(self._primitives.keys()):
            if k in save_dict:
                self._primitives[k] = save_dict[k]
        # load objects
        for k, obj in self._registry.items():
            if k in save_dict:
                try:
                    obj.load_state(save_dict[k])
                except Exception:
                    pass
        print(f"[SaveManager] Game loaded from {self.filepath}")


""" Esempio di uso:
class Inventory:
    def __init__(self):
        self.items = ["sword", "potion"]

    def save_state(self):
        return {"items": self.items}

    def load_state(self, data):
        self.items = data.get("items", [])

# E in gioco:
player = Player()
inventory = Inventory()

save_manager = SaveManager()
save_manager.register("player", player)
save_manager.register("inventory", inventory)

# Salvataggio
save_manager.save()

# Caricamento
save_manager.load()

"""