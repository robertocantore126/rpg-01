"""
Graph / Node-based Generation
Definisci un grafo logico (A → B → boss → tesoro), poi lo trasformi in stanze.
"""

import random

__all__ = ["GraphNode", "DungeonGraph", "RoomPrefab", "RoomInstance", "RoomGrapher"]

class GraphNode:
    """
    Un nodo logico del dungeon (non è ancora una stanza concreta).
    """
    def __init__(self, node_id, node_type="room"):
        self.node_id = node_id
        self.node_type = node_type   # "start", "room", "boss", "treasure"
        self.connections = []

    def connect(self, other_node):
        self.connections.append(other_node)


class DungeonGraph:
    """
    Rappresenta il grafo narrativo: nodi connessi da archi.
    """
    def __init__(self):
        self.nodes = {}

    def add_node(self, node):
        self.nodes[node.node_id] = node

    def connect(self, id_a, id_b):
        self.nodes[id_a].connect(self.nodes[id_b])
        self.nodes[id_b].connect(self.nodes[id_a])  # bidirezionale


class RoomPrefab:
    """
    Definisce le “tipologie di stanze” disponibili (tilemap + metadata).
    """
    def __init__(self, map_path, doors, tags=None):
        self.map_path = map_path
        self.doors = doors   # {"N": True, "S": False, ...}
        self.tags = tags or []  # es: ["boss", "treasure"]


class RoomInstance:
    """
    Collega un nodo logico a un prefab concreto.
    """
    def __init__(self, node, prefab):
        self.node = node          # GraphNode
        self.prefab = prefab      # RoomPrefab
        self.tilemap = None

    def load(self, tilemap_manager):
        self.tilemap = tilemap_manager.load_map(self.prefab.map_path)

    def render(self, surface):
        if self.tilemap:
            self.tilemap.render(surface)


class RoomGrapher:
    """
    Traduce il grafo logico in stanze reali.
    """
    def __init__(self, tilemap_manager, room_pool):
        self.tilemap_manager = tilemap_manager
        self.room_pool = room_pool   # lista di RoomPrefab
        self.graph = DungeonGraph()
        self.instances = {}          # node_id -> RoomInstance
        self.current = None

    def generate_graph(self):
        """
        Esempio di progressione lineare:
        start -> room -> boss -> treasure
        """
        start = GraphNode("start", "start")
        mid   = GraphNode("mid", "room")
        boss  = GraphNode("boss", "boss")
        chest = GraphNode("chest", "treasure")

        self.graph.add_node(start)
        self.graph.add_node(mid)
        self.graph.add_node(boss)
        self.graph.add_node(chest)

        self.graph.connect("start", "mid")
        self.graph.connect("mid", "boss")
        self.graph.connect("boss", "chest")

    def instantiate_rooms(self):
        """Associa ogni nodo a un prefab compatibile"""
        for node_id, node in self.graph.nodes.items():
            if node.node_type == "boss":
                candidates = [p for p in self.room_pool if "boss" in p.tags]
            elif node.node_type == "treasure":
                candidates = [p for p in self.room_pool if "treasure" in p.tags]
            else:
                candidates = [p for p in self.room_pool if "room" in p.tags]

            prefab = random.choice(candidates)
            self.instances[node_id] = RoomInstance(node, prefab)

        # imposta la stanza iniziale
        self.current = self.instances["start"]

    def load_current(self):
        self.current.load(self.tilemap_manager) # type: ignore

    def render_current(self, surface):
        self.current.render(surface) # type: ignore


"""Uso:
room_pool = [
    RoomPrefab("assets/tilemaps/start.json", {"N": True}, tags=["start", "room"]),
    RoomPrefab("assets/tilemaps/room01.json", {"E": True, "W": True}, tags=["room"]),
    RoomPrefab("assets/tilemaps/boss01.json", {"S": True}, tags=["boss"]),
    RoomPrefab("assets/tilemaps/treasure01.json", {"N": True}, tags=["treasure"]),
]

tilemap_manager = TilemapManager()
room_manager = RoomManager(tilemap_manager, room_pool)

room_manager.generate_graph()
room_manager.instantiate_rooms()
room_manager.load_current()

"""