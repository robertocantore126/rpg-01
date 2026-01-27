"""
Prefab room stitching (stanze prefabbricate cucite)
Hai un set di stanze disegnate a mano (o in .json come dici tu).
L’algoritmo sceglie casualmente quali collegare tra loro, rispettando certe regole (porte, corridoi, ecc).
"""

import random

__all__ = ["RoomInstance", "DungeonGraph", "RoomStitcher"]

class RoomInstance:
    """
    Rappresenta una singola stanza concreta caricata da JSON quando serve.
    """
    def __init__(self, room_id, map_path, doors):
        self.room_id = room_id
        self.map_path = map_path   # es: "assets/tilemaps/room_01.json"
        self.doors = doors         # es: {"N": True, "S": False, ...}
        self.tilemap = None        # sarà caricato dal TilemapManager
        self.entities = []         # nemici, item, ecc
    
    def load(self, tilemap_manager):
        """Carica la tilemap dal file usando il TilemapManager"""
        self.tilemap = tilemap_manager.load_map(self.map_path)
    
    def render(self, surface):
        if self.tilemap:
            self.tilemap.render(surface)


class DungeonGraph:
    """
    Tiene la topologia del dungeon come grafo logico.
    Nodi = stanze, archi = connessioni tramite porte.
    """
    def __init__(self):
        self.rooms = {}   # room_id -> RoomInstance
        self.graph = {}   # room_id -> [room_id connessi]

    def add_room(self, room):
        self.rooms[room.room_id] = room
        self.graph[room.room_id] = []

    def connect_rooms(self, room_a, room_b):
        self.graph[room_a].append(room_b)
        self.graph[room_b].append(room_a)


class RoomStitcher:
    """
    Gestisce il dungeon generato e la stanza attiva.
    """
    def __init__(self, tilemap_manager):
        self.tilemap_manager = tilemap_manager
        self.dungeon = DungeonGraph()
        self.current_room = None

    def generate_dungeon(self, room_pool, n_rooms=5):
        """
        room_pool = lista di prefab (dict con {id, map_path, doors})
        """
        # scegliamo una stanza iniziale
        start = random.choice(room_pool)
        start_room = RoomInstance(start["id"], start["map_path"], start["doors"])
        self.dungeon.add_room(start_room)
        self.current_room = start_room

        # esempio banale: collega alcune stanze random
        for i in range(n_rooms - 1):
            data = random.choice(room_pool)
            room = RoomInstance(data["id"], data["map_path"], data["doors"])
            self.dungeon.add_room(room)
            self.dungeon.connect_rooms(start_room.room_id, room.room_id)

    def load_current_room(self):
        self.current_room.load(self.tilemap_manager) # type: ignore

    def render_current_room(self, surface):
        if self.current_room:
            self.current_room.render(surface)

"""Uso:

# assets/tilemaps/ contiene JSON delle stanze
room_pool = [
    {"id": "room01", "map_path": "assets/tilemaps/room01.json", "doors": {"N": True, "S": True, "E": False, "W": False}},
    {"id": "room02", "map_path": "assets/tilemaps/room02.json", "doors": {"N": False, "S": True, "E": True, "W": False}},
    {"id": "room03", "map_path": "assets/tilemaps/room03.json", "doors": {"N": True, "S": False, "E": False, "W": True}},
]

# setup
tilemap_manager = TilemapManager()
room_manager = RoomManager(tilemap_manager)
room_manager.generate_dungeon(room_pool, n_rooms=3)

# carico la stanza iniziale
room_manager.load_current_room()

# nel game loop:
room_manager.render_current_room(game_surface)


"""