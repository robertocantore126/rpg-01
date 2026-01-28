# engine/world/tilemap.py

import json
import re
import pygame
import os

from engine.core.ecs import component

__all__ = ["TilesetLoader", "Tilemap", "TilemapManager"]

@component
class Tile:
    def __init__(self, tile_id: int, position: tuple[int, int], tileset: str, tile_type: str, variant: str) -> None:
        self.tile_id = tile_id
        self.position = position  # (x, y) in pixel
        self.tileset = tileset  # nome del tileset di appartenenza
        self.type = tile_type
        self.variant = variant

class TilemapFluffy:
    def __init__(self, tile_size: int) -> None:
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = {} # {(x, y): tile_id} -- deco, things you don't interact with


class TilesetLoader:
    """
    Carica tutti i png in assets/tilesets e li taglia in singoli tile.
    Associa ogni tile a un ID locale (0-based) per il rendering.
    E associa ogni tileset a un nome per il riconoscimento.
    data structure --> {nome_tileset: {id_locale: pygame.Surface}}
    """
    def __init__(self):
        self.base_path = "assets/tilesets"
        self.all_tilesets = {} # {"tileset_name": {local_id: pygame.Surface}}

        self.load_tilesets()

    def load_tilesets(self):
        """
        Carica tutti i tileset dalla cartella assets/tilesets.
        Ogni tileset è un PNG che viene diviso in tile.
        """
        try:
            for filename in os.listdir(self.base_path):
                if not filename.lower().endswith(".png"):
                    continue
                name, _ext = os.path.splitext(filename)
                # validate name matches expected pattern e.g. "16x16DungeonSet" or at least starts with digits
                if not name or not any(ch.isdigit() for ch in name):
                    print(f"[TilesetLoader] Skipping tileset with unexpected name: {filename}")
                    continue
                try:
                    self.all_tilesets[name] = self.load_tileset(name, filename)
                except Exception:
                    print(f"[TilesetLoader] Failed to load tileset: {filename}")
                    continue
        except Exception:
            # directory may not exist or be unreadable; keep all_tilesets empty
            print(f"[TilesetLoader] tileset base path '{self.base_path}' not accessible")

    def load_tileset(self, name: str, filename: str) -> dict[int, pygame.Surface]:
        """
        Carica un singolo tileset e lo divide in tile.
        Restituisce un dizionario {id_locale: pygame.Surface}.
        """
        full_path = os.path.join(self.base_path, filename)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Tileset file not found: {full_path}")
        image = pygame.image.load(full_path).convert_alpha()
        
        # Assumiamo che ogni nome di tileset sia nel formato "00x00NomeTileset"
        match = re.match(r"^(\d+)x(\d+)(.+)", name)
        if match:
            tile_width = int(match.group(1))
            tile_height = int(match.group(2))
        else:
            # filename did not match expected pattern; warn and fallback to 16x16
            print(f"[TilesetLoader] Warning: tileset name '{name}' doesn't match '<W>x<H>Name'. Falling back to 16x16.")
            tile_width = 16
            tile_height = 16

        tiles = {}
        for y in range(0, image.get_height(), tile_height):
            for x in range(0, image.get_width(), tile_width):
                rect = pygame.Rect(x, y, tile_width, tile_height)
                tile_surface = image.subsurface(rect).copy()
                tiles[len(tiles)] = tile_surface

        return tiles


class Tilemap:
    """
    Rappresenta una singola tilemap Tiled.
    - Mantiene i layer distinti
    - Legge dimensioni tile e mappa dal JSON
    - Gestisce il rendering layer per layer
    """
    def __init__(self, json_path: str):
        self.layers: list[dict] = []  # ogni layer contiene {"name": str, "tiles": list[int]}
        self.tilewidth = 0
        self.tileheight = 0
        self.map_width = 0
        self.map_height = 0

        self.used_tileset = ""  # nome del tileset usato per questa mappa
        self.tileset = TilesetLoader()

        self.load_from_json(json_path)

    def load_from_json(self, json_path: str):
        with open(json_path, "r") as f:
            file_data = json.load(f)

        # Leggo dimensioni generali della mappa
        self.tilewidth = file_data.get("tilewidth", 0)
        self.tileheight = file_data.get("tileheight", 0)
        self.map_width = file_data.get("width", 0)
        self.map_height = file_data.get("height", 0)

        assert all([self.tilewidth, self.tileheight, self.map_width, self.map_height]), \
            "Tilemap JSON non contiene dimensioni valide."

        # Carico ogni layer separatamente
        for layer in file_data["layers"]:
            if layer["type"] == "tilelayer":
                self.layers.append({
                    "name": layer["name"],
                    "tiles": layer["data"],
                    "width": layer["width"],
                    "height": layer["height"],
                    "visible": layer["visible"],
                })

    def render(self, surface: pygame.Surface):
        """
        Renderizza tutti i layer nell'ordine definito da Tiled.
        """
        for layer in self.layers:
            if not layer["visible"]:
                continue  # salta i layer nascosti
            self.render_layer(surface, layer)

    def render_layer(self, surface: pygame.Surface, layer: dict):
        """
        Renderizza un singolo layer.
        """
        for i, tile_id in enumerate(layer["tiles"]):
            if tile_id <= 0:
                continue
            # Calcolo posizione del tile
            x = (i % layer["width"]) * self.tilewidth
            y = (i // layer["width"]) * self.tileheight
            
            # Ottengo il tile dal tileset
            tile_surface = self.tileset.all_tilesets[self.used_tileset].get(tile_id - 1)  # -1 per convertire a 0-based index
            # print(f"Rendering tile {tile_id} at ({x}, {y})")  # Debug output
            if not tile_surface:
                # print(f"Warning: Tile ID {tile_id} not found in tileset '{self.used_tileset}'")
                continue
            surface.blit(tile_surface, (x, y))

    def get_tile(self, tile_id: int) -> pygame.Surface | None:
        """
        Restituisce il tile specificato dal tileset.
        """
        if self.used_tileset not in self.tileset.all_tilesets:
            print(f"Error: Tileset '{self.used_tileset}' not loaded.")
            return None
        return self.tileset.all_tilesets[self.used_tileset].get(tile_id - 1)

    # ----------------------------
    #   🧱 COLLISIONI
    # ----------------------------
    def get_collision_rects(self, layer_name: str) -> list[pygame.Rect]:
        """
        Restituisce una lista di pygame.Rect per tutti i tile NON VUOTI
        del layer con nome `layer_name`.
        """
        rects = []
        for layer in self.layers:
            if layer["name"] == layer_name:
                for i, tile_id in enumerate(layer["tiles"]):
                    if tile_id <= 0:
                        continue
                    x = (i % layer["width"]) * self.tilewidth
                    y = (i // layer["width"]) * self.tileheight
                    rects.append(pygame.Rect(x, y, self.tilewidth, self.tileheight))
        return rects


class TilemapManager:
    """
    Gestisce un insieme di Tilemap caricate dalla cartella assets/tilemaps.
    On creation: loads tilemaps and tilesets
    On function call: returns Tilemap by name and attaches tileset for correct rendering
    """
    def __init__(self):
        self.tilemaps: dict[str, Tilemap] = {}  # {"room1": Tilemap, "room2": Tilemap}
        self.map_set_pairs: dict[str, str] = {}  # {"room1": "16x16DungeonSet", ...}
        self.load_tilemaps()

    def load_tilemaps(self):
        """
        Carica tutte le tilemap (JSON) dalla cartella assets/tilemaps.
        """
        tilemap_dir = os.path.join("assets", "tilemaps")
        if not os.path.exists(tilemap_dir):
            print(f"[TilemapManager] Warning: tilemap directory '{tilemap_dir}' not found.")
            return

        for filename in os.listdir(tilemap_dir):
            if filename.endswith(".json"):
                name, _ext = os.path.splitext(filename)
                json_path = os.path.join(tilemap_dir, filename)
                tilemap = Tilemap(json_path=json_path)
                self.tilemaps[name] = tilemap

    def get_tilemap(self, name: str, tileset: str) -> Tilemap | None: 
        self.map_set_pairs[name] = tileset # TODO: fix the adding of tileset
        requested_map = self.tilemaps.get(name)
        requested_map.used_tileset = tileset #type: ignore
        return requested_map

