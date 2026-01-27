from __future__ import annotations

"""
Preparare la funzione is_passable
La A* grid richiede is_passable(x,y,agent_tags) → una funzione che, data la cella (x,y) restituisca se quell'agente (con quei tag) può andarci.
Implementazione suggerita: la Tilemap deve avere metadati per tile (es. tags: ["wall","door","soul_gate"]). is_passable confronta tile tags e agent tags (es. if "wall" in tile.tags and "ghost" not in agent_tags: return False).
Creare GridAStar
costruttore: GridAStar(width,height,is_passable,diagonal=True).
Creare AgentController
controller = AgentController(grid, tile_size=16, agent_tags={'ghost'})
Se l'agente è un fantasma, pass agent_tags={'ghost'} così il pathfinder potrà permettergli di attraversare muri se is_passable è implementata così.
Richiedere un percorso
Quando la AI decide di muovere verso una posizione: controller.move_to(agent.pos, target_pos)
move_to converte a tile coords e lancia A*. Se fallisce ritorna False.
Update fisico (per frame)
In agent.update(dt) chiama: vel, arrived = controller.update(agent.pos, agent.vel, dt, obstacles)
Puoi ottenere gli ostacoli pixel-based dalla tilemap: usa tilemap.get_collision_rects("Walls") vicino all'agente e trasformali in (x,y,w,h).
Integrazione con il Brain
Nel BT/FSM/GOAP, crea Action nodes che:
chiamano controller.move_to(...) e ritornano RUNNING finché agent.moving è True,
o ritornano SUCCESS/FAILURE quando arrivato o fallito.
Per GOAP, considera che le azioni di movimento sono long-running: lo planner deve creare una azione MoveTo(x,y) che ha precondizione (eg. not at target) e effetto (at target=true) — ma l'esecuzione reale è delegata al controller.

JSON config

Puoi mettere parametri steering in un JSON:

{
  "steering": {
    "max_speed": 140,
    "max_force": 700,
    "arrive_radius": 6,
    "weights": {"follow_path": 2.0, "avoid": 3.0, "wander": 0.2}
  }
}


Poi controller.load_from_json("configs/walker_steer.json").

Note pratiche e consigli

Tile vs pixel coords: tieni attenzione a conversioni. A* lavora su tile indices; steering su pixel positions (center of tiles recommended).
Obstacle list: per efficienza non passa tutta la tilemap come ostacoli: usa tilemap.get_collision_rects("Walls") e filtra solo quelle entro un raggio attorno all'agente.
Performance: A* è chiamato una volta quando parte il movimento. Non chiamarlo ogni frame. Ri-calcola solo se il target cambia o path invalido (es. ostacolo dinamico).
Repathing: quando si incontrano ostacoli dinamici (porte chiuse), implementa un piccolo timer di retry per richiamare move_to (es. ogni 0.5s).
Coesione con Physics: se usi un physics engine, applica la nuova vel come velocity del rigidbody invece che spostare direttamente la posizione.
Tuning: i pesi di steering determinano il comportamento: più peso a avoid → agente scarta ostacoli; più peso a follow_path → agente segue strettamente il path.
"""


from dataclasses import dataclass, field
import heapq
import math
import random
import json
from typing import Callable, Dict, List, Optional, Set, Tuple

__all__ = ["GridAStar", "SteeringConfig", "SteeringBehaviour", "AgentController"]

Vec2 = Tuple[float, float]

# ---------------------------
# Utility vector helpers
# ---------------------------
def vec_add(a: Vec2, b: Vec2) -> Vec2: return (a[0] + b[0], a[1] + b[1])
def vec_sub(a: Vec2, b: Vec2) -> Vec2: return (a[0] - b[0], a[1] - b[1])
def vec_mul(a: Vec2, s: float) -> Vec2: return (a[0] * s, a[1] * s)
def vec_len(a: Vec2) -> float: return math.hypot(a[0], a[1])
def vec_norm(a: Vec2) -> Vec2:
    l = vec_len(a)
    return (a[0] / l, a[1] / l) if l > 1e-6 else (0.0, 0.0)
def vec_clamp(a: Vec2, maxlen: float) -> Vec2:
    l = vec_len(a)
    if l <= maxlen: return a
    return vec_mul(vec_norm(a), maxlen)

# ---------------------------
# A* on grid (tiles)
# ---------------------------
@dataclass(order=True)
class _Node:
    f: float
    g: float = field(compare=False)
    x: int = field(compare=False)
    y: int = field(compare=False)
    parent: Optional["_Node"] = field(compare=False, default=None)

class GridAStar:
    """
    A* grid pathfinder.

    - width,height: grid size (in tiles)
    - is_passable: function(x:int,y:int, agent_tags:set[str]) -> bool
      used to decide se una cella è percorribile per un dato agente
    - diagonal: allow diagonal movement
    - heuristic: callable(x1,y1,x2,y2) -> float
    """

    def __init__(
        self,
        width: int,
        height: int,
        is_passable: Callable[[int,int,Set[str]], bool],
        diagonal: bool = False,
        heuristic: Optional[Callable[[int,int,int,int], float]] = None
    ):
        self.w = width
        self.h = height
        self.is_passable = is_passable
        self.diagonal = diagonal
        self.heuristic = heuristic if heuristic else self.manhattan

    @staticmethod
    def manhattan(x1,y1,x2,y2): return abs(x1-x2) + abs(y1-y2)
    @staticmethod
    def euclidean(x1,y1,x2,y2): return math.hypot(x1-x2, y1-y2)

    def in_bounds(self, x:int, y:int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def neighbors(self, x:int, y:int) -> List[Tuple[int,int,float]]:
        # Returns list of (nx,ny,move_cost)
        dirs = [(1,0),( -1,0),(0,1),(0,-1)]
        if self.diagonal:
            dirs += [(1,1),(1,-1),(-1,1),(-1,-1)]
        out = []
        for dx,dy in dirs:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                cost = math.hypot(dx,dy) if self.diagonal else 1.0
                out.append((nx,ny,cost))
        return out

    def find_path(self, start_tile: Tuple[int,int], goal_tile: Tuple[int,int], agent_tags: Set[str]) -> Optional[List[Tuple[int,int]]]:
        """A* search on grid. Returns list of tile coords or None."""
        sx, sy = start_tile
        gx, gy = goal_tile

        if not self.in_bounds(gx, gy) or not self.in_bounds(sx, sy):
            return None
        if not self.is_passable(sx, sy, agent_tags) or not self.is_passable(gx, gy, agent_tags):
            # if start or goal not passable, fail
            return None

        open_heap: List[_Node] = []
        start_node = _Node(f=0.0 + self.heuristic(sx,sy,gx,gy), g=0.0, x=sx, y=sy, parent=None)
        heapq.heappush(open_heap, start_node)
        came = {}  # (x,y) -> g
        came[(sx,sy)] = 0.0
        max_iters = (self.w*self.h)*4

        iters = 0
        while open_heap and iters < max_iters:
            iters += 1
            node = heapq.heappop(open_heap)
            if (node.x, node.y) == (gx, gy):
                # reconstruct
                path: List[Tuple[int,int]] = []
                cur = node
                while cur:
                    path.append((cur.x, cur.y))
                    cur = cur.parent
                path.reverse()
                return path

            for nx, ny, move_cost in self.neighbors(node.x, node.y):
                if not self.is_passable(nx, ny, agent_tags):
                    continue
                ng = node.g + move_cost
                key = (nx, ny)
                if key not in came or ng < came[key]:
                    came[key] = ng
                    h = self.heuristic(nx, ny, gx, gy)
                    f = ng + h
                    heapq.heappush(open_heap, _Node(f=f, g=ng, x=nx, y=ny, parent=node))

        return None

# ---------------------------
# Steering behaviours
# ---------------------------
@dataclass
class SteeringConfig:
    max_speed: float = 120.0         # pixel/sec
    max_force: float = 600.0         # acceleration (pixels/sec^2)
    arrive_radius: float = 8.0       # pixels: within this, consider arrived
    slow_radius: float = 48.0        # pixels: start slowing down
    wander_radius: float = 30.0
    wander_distance: float = 40.0
    wander_jitter: float = 120.0     # per second
    avoid_distance: float = 24.0     # lookahead for obstacle avoidance
    avoid_force: float = 400.0
    weights: Dict[str,float] = field(default_factory=lambda: {
        "seek": 1.0,
        "arrive": 1.5,
        "follow_path": 1.8,
        "avoid": 2.0,
        "wander": 0.3,
        "flee": 1.0
    })

class SteeringBehaviour:
    """
    Implements composed steering behaviours. The API:
      compute(agent_pos, agent_vel, target_pos, dt, context) -> desired_velocity

    context: dict with useful info, e.g.:
      - path: list of waypoints [(x_px,y_px),...]
      - obstacles: list of pygame.Rect or polygons to avoid
      - flee_target: pos to flee from
    """
    def __init__(self, cfg: SteeringConfig):
        self.cfg = cfg
        # wander internal state
        self.wander_target = (0.0, 0.0)

    def seek(self, pos: Vec2, target: Vec2) -> Vec2:
        desired = vec_sub(target, pos)
        return vec_mul(vec_norm(desired), self.cfg.max_speed)

    def arrive(self, pos: Vec2, target: Vec2) -> Vec2:
        diff = vec_sub(target, pos)
        dist = vec_len(diff)
        if dist < self.cfg.arrive_radius:
            return (0.0, 0.0)
        if dist > self.cfg.slow_radius:
            return vec_mul(vec_norm(diff), self.cfg.max_speed)
        # scaled speed
        speed = self.cfg.max_speed * (dist / self.cfg.slow_radius)
        return vec_mul(vec_norm(diff), speed)

    def flee(self, pos: Vec2, threat_pos: Vec2) -> Vec2:
        diff = vec_sub(pos, threat_pos)
        return vec_mul(vec_norm(diff), self.cfg.max_speed)

    def wander(self, pos: Vec2, dt: float) -> Vec2:
        """
        Wander using jittered target on a circle in front of agent.
        """
        jitter = self.cfg.wander_jitter * dt
        # random displacement
        self.wander_target = (self.wander_target[0] + random.uniform(-1,1)*jitter,
                              self.wander_target[1] + random.uniform(-1,1)*jitter)
        # reproject to circle
        wt = vec_mul(vec_norm(self.wander_target), self.cfg.wander_radius)
        # project in front of agent as offset
        forward_offset = (self.cfg.wander_distance, 0.0)
        target = vec_add(pos, vec_add(wt, forward_offset))
        return self.seek(pos, target)

    def avoid_obstacles(self, pos: Vec2, vel: Vec2, obstacles: List[Tuple[float,float,float,float]]) -> Vec2:
        """
        Simple obstacle avoidance using feeler (ray) ahead of agent in direction of velocity.
        obstacles: list of rects represented as (x,y,w,h) or pygame.Rect-like
        returns a steering vector (not clamped to max_speed)
        """
        if vec_len(vel) < 1e-3:
            return (0.0, 0.0)
        dir_norm = vec_norm(vel)
        feeler_len = self.cfg.avoid_distance + vec_len(vel) * 0.1
        feeler_end = (pos[0] + dir_norm[0]*feeler_len, pos[1] + dir_norm[1]*feeler_len)

        # find nearest obstacle intersected
        steer = (0.0, 0.0)
        min_t = float("inf")
        for ox,oy,w,h in obstacles:
            # AABB-line intersection (approx)
            # compute closest point on rect to feeler_end
            closest_x = max(ox, min(feeler_end[0], ox + w))
            closest_y = max(oy, min(feeler_end[1], oy + h))
            dx = feeler_end[0] - closest_x
            dy = feeler_end[1] - closest_y
            dist = math.hypot(dx,dy)
            if dist < self.cfg.avoid_distance and dist < min_t:
                min_t = dist
                # steer away from obstacle center
                center = (ox + w/2, oy + h/2)
                away = vec_sub(feeler_end, center)
                steer = vec_mul(vec_norm(away), self.cfg.avoid_force)
        return steer

    def follow_path(self, pos: Vec2, path: List[Vec2], current_wp_idx: int, dt: float) -> Tuple[Vec2,int]:
        """
        Path is sequence of tile centers (pixel coords). current_wp_idx is index of target waypoint.
        Returns (steering_vector (desired vel), new_wp_idx).
        """
        if not path:
            return ((0, 0), current_wp_idx)
        # clamp waypoint index
        wp_idx = min(current_wp_idx, len(path)-1)
        wp = path[wp_idx]
        # if close to this waypoint, advance
        if vec_len(vec_sub(wp, pos)) < self.cfg.arrive_radius*1.2:
            wp_idx = min(wp_idx + 1, len(path)-1)
            wp = path[wp_idx]
        # arrive to waypoint
        desired = self.arrive(pos, wp)
        return (desired, wp_idx)

    def compute(self, pos: Vec2, vel: Vec2, dt: float, context: Dict) -> Vec2:
        """
        Combine behaviours using weights in cfg.weights
        context expected keys: path (list of pixel pos), obstacles (list rect tuples),
                             flee_target (pos) optional
        returns desired velocity (pixels/sec)
        """
        weights = self.cfg.weights
        total = (0.0, 0.0)

        # follow path (highest priority if provided)
        if "path" in context and context["path"]:
            desired_path, wp_idx = self.follow_path(pos, context["path"], context.get("path_idx", 0), dt)
            total = vec_add(total, vec_mul(vec_norm(desired_path) if vec_len(desired_path)>0 else (0,0), weights.get("follow_path",1.0)))
            # store updated index back into context
            context["path_idx"] = wp_idx

        # flee
        if "flee_target" in context and context["flee_target"] is not None:
            desired = self.flee(pos, context["flee_target"])
            total = vec_add(total, vec_mul(vec_norm(desired), weights.get("flee",1.0)))

        # avoidance
        if "obstacles" in context and context["obstacles"]:
            avoid_force = self.avoid_obstacles(pos, vel, context["obstacles"])
            total = vec_add(total, vec_mul(vec_norm(avoid_force) if vec_len(avoid_force)>0 else (0,0), weights.get("avoid",1.0)))

        # wander fallback if no path
        if ("path" not in context or not context["path"]) and weights.get("wander",0) > 0:
            w = self.wander(pos, dt)
            total = vec_add(total, vec_mul(vec_norm(w), weights.get("wander",1.0)))

        # normalize to max_speed
        if vec_len(total) < 1e-6:
            return (0.0, 0.0)
        desired = vec_mul(vec_norm(total), self.cfg.max_speed)
        return desired

# ---------------------------
# AgentController (glue)
# ---------------------------
class AgentController:
    """
    High-level controller for an agent:
      - uses GridAStar to compute path in tile coords
      - converts path to pixel waypoints (center of tiles) via tile_size
      - uses SteeringBehaviour to follow path and avoid obstacles
      - supports per-agent passability tags to customize which tiles are blocked
    """

    def __init__(
        self,
        grid_astar: GridAStar,
        steering_cfg: Optional[SteeringConfig] = None,
        tile_size: int = 16,
        agent_tags: Optional[Set[str]] = None,
    ):
        self.astar = grid_astar
        self.cfg = steering_cfg if steering_cfg else SteeringConfig()
        self.steering = SteeringBehaviour(self.cfg)
        self.tile_size = tile_size
        self.agent_tags = set(agent_tags) if agent_tags else set()
        self.path_tiles: List[Tuple[int,int]] = []
        self.path_px: List[Vec2] = []
        self.path_idx = 0
        self.moving = False
        self.target_px: Optional[Vec2] = None

    # ----------------
    # Configuration helpers
    # ----------------
    def set_agent_tags(self, tags: Set[str]):
        self.agent_tags = set(tags)

    def load_from_json(self, json_path: str):
        with open(json_path, "r") as f:
            data = json.load(f)
        # expect structure with steering params (optional)
        ste = data.get("steering", {})
        if "max_speed" in ste: self.cfg.max_speed = float(ste["max_speed"])
        if "max_force" in ste: self.cfg.max_force = float(ste["max_force"])
        if "arrive_radius" in ste: self.cfg.arrive_radius = float(ste["arrive_radius"])
        # weights
        if "weights" in ste:
            for k,v in ste["weights"].items():
                self.cfg.weights[k] = float(v)

    # ----------------
    # Path API
    # ----------------
    def move_to(self, start_px: Vec2, goal_px: Vec2) -> bool:
        """
        Computes a path from start_px to goal_px and sets internal path to follow.
        Coordinates: pixel space. Will map to tile coords using tile_size.
        Returns True if a path found.
        """
        sx, sy = int(start_px[0] // self.tile_size), int(start_px[1] // self.tile_size)
        gx, gy = int(goal_px[0] // self.tile_size), int(goal_px[1] // self.tile_size)
        path = self.astar.find_path((sx,sy), (gx,gy), self.agent_tags)
        if not path:
            self.path_tiles = []
            self.path_px = []
            self.moving = False
            return False
        self.path_tiles = path
        # convert tiles to pixel centers
        self.path_px = [((tx + 0.5)*self.tile_size, (ty + 0.5)*self.tile_size) for (tx,ty) in path]
        self.path_idx = 0
        self.moving = True
        self.target_px = goal_px
        return True

    def stop(self):
        self.path_tiles = []
        self.path_px = []
        self.moving = False
        self.target_px = None

    # ----------------
    # update loop
    # ----------------
    def update(self, pos_px: Vec2, vel_px: Vec2, dt: float, obstacles: List[Tuple[float,float,float,float]] = []) -> Tuple[Vec2, bool]:
        """
        Call each frame:
          - pos_px, vel_px: current position and velocity in pixels
          - dt: seconds since last frame
          - obstacles: list of rects (x,y,w,h) in pixel space for avoidance
        
        Returns: (new_velocity_px, arrived_bool)
        """
        context = {"path": self.path_px, "path_idx": self.path_idx, "obstacles": obstacles}
        desired = self.steering.compute(pos_px, vel_px, dt, context)
        # simple acceleration integration
        desired_change = vec_sub(desired, vel_px)
        # clamp by max_force * dt
        max_delta = self.cfg.max_force * dt
        accel = vec_clamp(desired_change, max_delta)
        new_vel = vec_add(vel_px, accel)
        # clamp to max_speed
        new_vel = vec_clamp(new_vel, self.cfg.max_speed)

        # check arrival to final target
        arrived = False
        if self.moving and self.target_px:
            if vec_len(vec_sub(self.target_px, pos_px)) < self.cfg.arrive_radius:
                arrived = True
                self.stop()

        # update path_idx from context (steering may change it)
        self.path_idx = context.get("path_idx", self.path_idx)
        return new_vel, arrived
