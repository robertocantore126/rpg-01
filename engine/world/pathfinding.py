# ===============================
# Pathfinding Manager
# ===============================
import math
from typing import Dict, List, Tuple


class PathfindingManager:
    def __init__(self, mode="grid"):
        """
        mode = "grid" o "graph"
        """
        self.mode = mode
        self.grid = None
        self.graph = None

    def set_grid(self, grid, cell_size):
        """ grid = matrice 2D (0=walkable,1=blocked) """
        self.grid = grid
        self.cell_size = cell_size

    def set_graph(self, graph: Dict[int, List[Tuple[int,float]]]):
        """ graph = {node: [(neighbor, cost), ...]} """
        self.graph = graph

    def heuristic(self, a, b):
        # Manhattan per grid, Euclidea per graph
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def find_path(self, start, goal):
        if self.mode == "grid":
            return self._a_star_grid(start, goal)
        else:
            return self._dijkstra_graph(start, goal)

    def _a_star_grid(self, start, goal):
        from heapq import heappush, heappop
        open_set = []
        heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        while open_set:
            _, current = heappop(open_set)
            if current == goal:
                return self._reconstruct_path(came_from, current)
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                neighbor = (current[0]+dx, current[1]+dy)
                if not (0 <= neighbor[0] < len(self.grid[0]) and 0 <= neighbor[1] < len(self.grid)): # type: ignore
                    continue
                if self.grid[neighbor[1]][neighbor[0]] == 1: # type: ignore
                    continue
                tentative = g_score[current] + 1
                if tentative < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    f = tentative + self.heuristic(neighbor, goal)
                    heappush(open_set, (f, neighbor))
        return []

    def _dijkstra_graph(self, start, goal):
        from heapq import heappush, heappop
        dist = {start: 0}
        prev = {}
        pq = [(0, start)]
        while pq:
            d, u = heappop(pq)
            if u == goal:
                return self._reconstruct_path(prev, u)
            if d > dist[u]: continue
            for v, cost in self.graph.get(u, []): # type: ignore
                nd = d + cost
                if nd < dist.get(v, math.inf):
                    dist[v] = nd # type: ignore
                    prev[v] = u
                    heappush(pq, (nd, v)) # type: ignore
        return []

    def _reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return path[::-1]
