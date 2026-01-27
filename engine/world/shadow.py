"""
Spiegazione dettagliata — come funziona e come integrarlo

RayCaster
cast_ray(origin, direction, max_dist, obstacles) normalizza la direzione, costruisce un endpoint e interseca il segmento ray vs ciascun segmento derivato dagli ostacoli (ogni poligono diventa una serie di segmenti). Restituisce il punto di collisione più vicino.
Utility: cast_ray_to_point, batch_cast. Puoi usare RayCaster per line-of-sight, proiettili, AI perception, ecc.
ShadowCaster.compute_visibility_polygon
Recupera tutti i vertici degli ostacoli (opzionalmente filtrati dal raggio della luce).
Per ogni vertice calcola l’angolo rispetto alla luce, e lancia 3 raggi: angle - eps, angle, angle + eps. Questi piccoli offset permettono di catturare correttamente i bordi e risolvere casi di collinearità.
Se non trovi intersezioni, usa un punto lontano sulla circonferenza del raggio della luce (così la visibilità è limitata al radius).
Infine ordina i punti per angolo attorno al centro luce e costruisce il poligono visibile.

Ombre multiple
Per più luci: calcola vis_poly per ciascuna luce singolarmente, poi combina i risultati: spesso si disegna su una surface oscurante (darkness) e si tolgi (clear) la visibilità di ogni luce. Se disegni le luci in modalità additiva (BLEND_ADD), le aree illuminate da più fonti si sommano (risultato visivamente realistico).
Le ombre si sovrappongono naturalmente: se un'area è illuminata da luce A ma non da B, la luce B non la “riaffetta”; la combinazione delle luci produce la scena corretta.

Performance
O(n_vertices) rays (in pratica 3x vertices) → con molti poligoni grandi può esplodere.
Strategie pratiche:
Filtrare i vertici per radius (solo vertici entro la sfera di influenza della luce).
Limite max_rays e campionamento degli angoli (es. tenere solo 1 ogni N vertici).
Usare un QuadTree o altra struttura spaziale per ottenere solo gli ostacoli rilevanti.
Ridurre eps_angle e max_rays per luci piccole o secondarie.
Rendering
Ci sono diversi approcci; qui propongo il classico: disegnare una surface oscurante su tutta la scena, quindi “tagliare” (rendere trasparente) la polygon area visibile della luce e disegnare un cono di luce (o un gradiente circolare) additivo.
Il rendering è separato dal calcolo della visibilità: ShadowCaster calcola i poligoni, tu decidi come disegnarli nel renderer (puoi disegnare poligoni neri per le ombre, o usare maschere avanzate).
Precisione & Edge cases
L’epsilon angolare aiuta a coprire i casi di vertici collineari e “shadow acne”.
Per oggetti molto piccoli o sottili, potresti aggiungere micro-offset nella direzione del raggio.
Come integrarlo nel tuo World / Scene
Nel sistema di rendering: ogni frame, per ogni luce attiva:
usa ShadowCaster.compute_visibility_polygon(light, relevant_obstacles) (passa solo ostacoli vicini filtrati dal QuadTree)
poi chiama render_light_with_shadows() o una tua routine che disegna la luce e la maschera di ombra su una surface.
Per performance: aggiorna vis_poly solo ogni N frame per luci statiche, o solo quando la luce o ostacoli si muovono.
"""

# shadow.py
"""
2D RayCasting + Shadow casting module for Pygame-friendly games.

Principali classi / funzioni:
- RayCaster: funzioni per intersecare segmenti, cast di un singolo raggio, batch cast.
- Light: oggetto semplice che tiene posizione, radius, color, intensity.
- ShadowCaster: costruisce visibility polygon data per un Light, dato un set di obstacles.
- Utility: polygon helpers, ordering by angle, Pygame rendering helpers.

Obstacles format supported:
- list of polygons: polygon = [(x0,y0), (x1,y1), ...] (closed or open; code tratta come loop)
- optionally a list of segments: segment = ((x1,y1),(x2,y2))

Ottimizzazioni:
- Filtrare gli ostacoli per bounding box vs light radius (opzionale).
- Limitare numero di rays (max_rays).
"""

import math
from typing import List, Tuple, Optional, Iterable, Dict, Any
import pygame

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Polygon = List[Point]

__all__ = ["RayCaster", "Light", "ShadowCaster"]

# --------------------------
# Basic geometry helpers
# --------------------------
def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])

def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])

def _mul(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s)

def _dot(a: Point, b: Point) -> float:
    return a[0]*b[0] + a[1]*b[1]

def _cross(a: Point, b: Point) -> float:
    return a[0]*b[1] - a[1]*b[0]

def _length(a: Point) -> float:
    return math.hypot(a[0], a[1])

def _normalize(a: Point) -> Point:
    l = _length(a)
    if l == 0:
        return (0.0, 0.0)
    return (a[0]/l, a[1]/l)


# --------------------------
# Segment-segment intersection
# Returns (t,u,point) where:
#  - segment A is p + t*r  (t in [0,1])
#  - segment B is q + u*s  (u in [0,1])
# If no intersection returns None
# --------------------------
def segment_intersection(a0: Point, a1: Point, b0: Point, b1: Point, eps=1e-9):
    p = a0
    r = _sub(a1, a0)
    q = b0
    s = _sub(b1, b0)
    rxs = _cross(r, s)
    q_p = _sub(q, p)
    q_pxr = _cross(q_p, r)
    if abs(rxs) < eps:
        # parallel
        return None
    t = _cross(q_p, s) / rxs
    u = _cross(q_p, r) / rxs
    if -eps <= t <= 1+eps and -eps <= u <= 1+eps:
        inter = _add(p, _mul(r, t))
        return (t, u, inter)
    return None


# --------------------------
# RayCaster
# General purpose API:
# - cast_ray(origin, direction, max_dist, obstacles) -> (hit_point, hit_dist, hit_info)
# obstacles: iterable of polygons or segments (see format below)
# Returns nearest intersection or None
# --------------------------
class RayCaster:
    def __init__(self):
        pass

    @staticmethod
    def _segments_from_obstacles(obstacles: Iterable[Any]) -> Iterable[Segment]:
        """
        Normalize obstacles to segments iterator.
        Accepts:
         - Polygon (list of points) -> yields edges
         - Segment ((p0,p1)) -> yields it
        """
        for obs in obstacles:
            if not obs:
                continue
            # if it's a polygon (list-like)
            if isinstance(obs, (list, tuple)) and len(obs) >= 2 and isinstance(obs[0], (list, tuple)):
                # polygon or polyline: yield consecutive pairs, close loop
                pts = list(obs)
                n = len(pts)
                for i in range(n):
                    a = pts[i]
                    b = pts[(i+1) % n]
                    yield (a, b)
            else:
                # assume it's a segment
                yield obs # type: ignore

    def cast_ray(self, origin: Point, direction: Point, max_dist: float, obstacles: Iterable[Any]) -> Optional[Dict]:
        """
        Casts a single ray from origin in direction (normalized or not).
        Returns nearest hit dict: {"point":(x,y), "dist":d, "segment":(a,b), "t":t_on_segment}
        or None if no hit within max_dist.
        """
        dir_n = _normalize(direction)
        ray_end = _add(origin, _mul(dir_n, max_dist))
        nearest = None
        nearest_d = float('inf')
        for seg in self._segments_from_obstacles(obstacles):
            res = segment_intersection(origin, ray_end, seg[0], seg[1])
            if res:
                t, u, pt = res
                # distance from origin
                d = _length(_sub(pt, origin))
                if d < nearest_d:
                    nearest_d = d
                    nearest = {"point": pt, "dist": d, "segment": seg, "t": u}
        return nearest

    def cast_ray_to_point(self, origin: Point, target: Point, obstacles: Iterable[Any]) -> Optional[Dict]:
        return self.cast_ray(origin, _sub(target, origin), _length(_sub(target, origin)), obstacles)

    def batch_cast(self, origin: Point, directions: Iterable[Point], max_dist: float, obstacles: Iterable[Any]) -> List[Optional[Dict]]:
        out = []
        for d in directions:
            out.append(self.cast_ray(origin, d, max_dist, obstacles))
        return out


# --------------------------
# ShadowCaster
# Compute visibility polygon for a point light by casting rays towards obstacle vertices
# Algorithm:
# 1) collect relevant vertices (optionally filtered by bounding box/radius)
# 2) for each vertex compute angle, create three rays: angle-eps, angle, angle+eps
# 3) cast rays and collect intersection points
# 4) sort intersection points by angle -> visibility polygon
# Notes:
# - max_rays: cap number of rays (if too many vertices), we sample
# - obstacle format same as RayCaster
# --------------------------
class Light:
    def __init__(self, pos: Point, radius: float, color=(255,200,180), intensity: float = 1.0):
        self.x, self.y = pos
        self.radius = radius
        self.color = color
        self.intensity = intensity


class ShadowCaster:
    def __init__(self, raycaster: Optional[RayCaster] = None, eps_angle: float = 1e-3):
        self.raycaster = raycaster or RayCaster()
        self.eps_angle = eps_angle  # small angle offset to catch edges
        self.max_rays = 2000  # safety cap; can be tuned

    @staticmethod
    def _collect_vertices(obstacles: Iterable[Any], center: Point, radius: Optional[float] = None):
        verts = []
        cx, cy = center
        for obs in obstacles:
            if not obs:
                continue
            if isinstance(obs, (list, tuple)) and len(obs) >= 2 and isinstance(obs[0], (list, tuple)):
                # polygon
                for p in obs:
                    # optional radius filter
                    if radius is not None:
                        if (p[0]-cx)**2 + (p[1]-cy)**2 > radius*radius:
                            continue
                    verts.append(p)
            else:
                # segment
                a, b = obs # type: ignore
                if radius is not None:
                    if (a[0]-cx)**2 + (a[1]-cy)**2 <= radius*radius:
                        verts.append(a)
                    if (b[0]-cx)**2 + (b[1]-cy)**2 <= radius*radius:
                        verts.append(b)
                else:
                    verts.append(a); verts.append(b)
        return verts

    def compute_visibility_polygon(self, light: Light, obstacles: Iterable[Any], max_rays: Optional[int] = None, radius: Optional[float] = None) -> List[Point]:
        """
        Returns a list of points forming the visibility polygon (in order).
        - light: Light object with pos and radius
        - obstacles: iterable of polygons/segments
        - max_rays: optional cap
        - radius: optional filter radius (defaults to light.radius)
        """
        cx, cy = (light.x, light.y)
        rad = radius if radius is not None else light.radius
        verts = list(self._collect_vertices(obstacles, (cx,cy), radius=rad))
        # if no obstacle vertices, return circle approx? we can return empty or simple fan
        if not verts:
            # simple circle fan sample (coarse)
            steps = 24
            poly = []
            for i in range(steps):
                ang = (i / steps) * 2*math.pi
                poly.append((cx + math.cos(ang)*rad, cy + math.sin(ang)*rad))
            return poly

        # compute unique angles to vertices
        angles = []
        unique = set()
        for v in verts:
            ang = math.atan2(v[1]-cy, v[0]-cx)
            # normalize
            if ang in unique:
                continue
            unique.add(ang)
            angles.append(ang)
        # optionally limit number of angles
        angles.sort()
        if max_rays is None:
            max_rays = self.max_rays
        if len(angles)*3 > max_rays:
            # sample angles to fit max_rays (we request 3 rays per angle)
            step = max(1, int(math.ceil(len(angles)*3 / max_rays)))
            angles = angles[::step]

        # create rays for angle-eps, angle, angle+eps
        cast_angles = []
        for ang in angles:
            cast_angles.append(ang - self.eps_angle)
            cast_angles.append(ang)
            cast_angles.append(ang + self.eps_angle)

        # cast rays, collect intersections
        inters = []
        for ang in cast_angles:
            dx = math.cos(ang)
            dy = math.sin(ang)
            res = self.raycaster.cast_ray((cx,cy), (dx,dy), rad, obstacles)
            if res:
                pt = res["point"]
                dist = res["dist"]
            else:
                # no hit: use far point on circle
                pt = (cx + dx*rad, cy + dy*rad)
                dist = rad
            inters.append((ang, pt, dist))

        # sort intersections by angle and remove duplicates by small threshold
        inters.sort(key=lambda x: math.atan2(x[1][1]-cy, x[1][0]-cx))
        poly = []
        last = None
        for ang, pt, dist in inters:
            if last is None:
                poly.append(pt); last = pt
            else:
                # deduplicate near-equal points
                if (pt[0]-last[0])**2 + (pt[1]-last[1])**2 > 1e-6:
                    poly.append(pt); last = pt
        return poly

    # Compute shadow polygons (the parts outside visibility):
    # For drawing shadows: usually render the dark full-screen and then cut out visibility polygon.
    # For convenience we also return shadow polygons as triangles from light to each visibility edge
    def compute_shadow_mesh(self, light: Light, obstacles: Iterable[Any], **kwargs) -> List[Polygon]:
        vis = self.compute_visibility_polygon(light, obstacles, **kwargs)
        # produce triangles fan light -> consecutive vis points
        cx, cy = (light.x, light.y)
        tris = []
        if len(vis) < 2:
            return []
        for i in range(len(vis)):
            a = vis[i]
            b = vis[(i+1)%len(vis)]
            tris.append([(cx,cy), a, b])
        return tris

    # obstacles = sc.obstacles_from_quadtree(my_quadtree, light)
    # vis_poly = sc.compute_visibility_polygon(light, obstacles)
    def obstacles_from_quadtree(self, quadtree, light: "Light") -> list:
        """
        Query ostacoli dalla quadtree in base al bounding box della luce.
        Assumiamo che ogni nodo della quadtree abbia una proprietà .bounds e .items (o simile).
        """
        cx, cy, r = light.x, light.y, light.radius
        bbox = (cx - r, cy - r, r*2, r*2)  # bounding box [x,y,w,h]
        # API generica: supponiamo che quadtree.query(bbox) ritorni entità con attributo .polygon
        candidates = quadtree.query(bbox)
        return [c.polygon for c in candidates if hasattr(c, "polygon")]

    def compute_shadow_polygons(self, light: "Light", obstacles, **kwargs) -> List[Polygon]:
        """
        Ritorna la lista di poligoni che rappresentano le ombre (fuori dalla visibility polygon).
        In pratica: un triangolo-fan dal bordo del vis_poly verso il bordo del raggio massimo.
        """
        cx, cy = (light.x, light.y)
        rad = light.radius
        vis_poly = self.compute_visibility_polygon(light, obstacles, **kwargs)

        shadows = []
        if len(vis_poly) < 2:
            return shadows

        for i in range(len(vis_poly)):
            a = vis_poly[i]
            b = vis_poly[(i+1) % len(vis_poly)]

            # punto esteso verso il bordo del raggio
            dir_a = _normalize(_sub(a, (cx, cy)))
            dir_b = _normalize(_sub(b, (cx, cy)))
            far_a = _add((cx, cy), _mul(dir_a, rad))
            far_b = _add((cx, cy), _mul(dir_b, rad))

            poly = [a, b, far_b, far_a]  # quadrilatero ombra
            shadows.append(poly)
        return shadows

    def compute_soft_visibility(self, light: "Light", obstacles, samples: int = 5, jitter: float = 0.02) -> List[Point]:
        """
        Calcola una visibility polygon con 'soft edges' campionando più raggi intorno ad ogni angolo.
        samples: numero di raggi per lato
        jitter: offset in radianti intorno all'angolo base
        """
        cx, cy = light.x, light.y
        verts = self._collect_vertices(obstacles, (cx, cy), light.radius)
        if not verts:
            return []

        cast_angles = []
        for v in verts:
            ang = math.atan2(v[1]-cy, v[0]-cx)
            # genera vari sample intorno all'angolo
            for s in range(-samples, samples+1):
                cast_angles.append(ang + s * jitter)

        inters = []
        for ang in cast_angles:
            dx, dy = math.cos(ang), math.sin(ang)
            res = self.raycaster.cast_ray((cx,cy), (dx,dy), light.radius, obstacles)
            if res:
                inters.append((ang, res["point"]))
            else:
                inters.append((ang, (cx+dx*light.radius, cy+dy*light.radius)))

        # ordina per angolo e ritorna
        inters.sort(key=lambda x: x[0])
        return [pt for _,pt in inters]

# --------------------------
# Pygame render helpers
# --------------------------
def draw_visibility_polygon(surface: pygame.Surface, poly: List[Point], color=(255,255,255,128)):
    if not poly:
        return
    s = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
    pts = [(int(x), int(y)) for (x,y) in poly]
    # fill polygon
    pygame.draw.polygon(s, color, pts)
    surface.blit(s, (0,0))


def render_light_with_shadows(base_surface: pygame.Surface, light: Light, vis_poly: List[Point],
                              shadow_color=(0,0,0,200)):
    """
    Typical pattern:
    - create a darkness surface (same size) filled with shadow_color
    - clear the visibility polygon (set alpha = 0) to represent illuminated area
    - then add the colored light (optional) with additive blending
    """
    w,h = base_surface.get_size()
    dark = pygame.Surface((w,h), flags=pygame.SRCALPHA)
    # fill with shadow color
    dark.fill(shadow_color)

    # create mask of visibility polygon and punch hole
    if vis_poly:
        mask = pygame.Surface((w,h), flags=pygame.SRCALPHA)
        mask.fill((0,0,0,0))
        pts = [(int(x), int(y)) for (x,y) in vis_poly]
        pygame.draw.polygon(mask, (0,0,0,0), pts)
        # To cut hole we draw polygon with fully transparent using special flag
        # But pygame doesn't support direct subtract; we use mask blending:
        # method: draw polygon on dark with BLEND_RGBA_SUB of full opacity -> easier: use per-pixel alpha manipulation
        # Simpler approach: create a surface for lit area and blit it with SRCALPHA and set alpha=0 in poly area.
        hole = pygame.Surface((w,h), flags=pygame.SRCALPHA)
        hole.fill((0,0,0,0))
        pygame.draw.polygon(hole, (0,0,0,0), pts)
        # Instead of complex bitops, we use polygon to clear by drawing polygon with (0,0,0,0) directly onto dark:
        pygame.draw.polygon(dark, (0,0,0,0), pts)
    base_surface.blit(dark, (0,0))

    # optionally draw colored light additively inside vis poly
    # build light surface
    lx, ly = int(light.x), int(light.y)
    radius = int(light.radius)
    light_surf = pygame.Surface((radius*2, radius*2), flags=pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        alpha = int(255 * (light.intensity * (1 - (r / radius))))
        col = (light.color[0], light.color[1], light.color[2], alpha)
        pygame.draw.circle(light_surf, col, (radius, radius), r)
    # blit additive
    base_surface.blit(light_surf, (lx - radius, ly - radius), special_flags=pygame.BLEND_ADD)


# --------------------------
# Example usage snippet (for documentation)
# --------------------------
_example_usage = """
# Example (to be used inside your Pygame loop)
from shadow import RayCaster, ShadowCaster, Light, render_light_with_shadows

# obstacles: list of polygons
obstacles = [
    [(100,100),(200,100),(200,200),(100,200)],
    [(300,120),(360,100),(420,160),(360,200)]
]

ray = RayCaster()
sc = ShadowCaster(ray)
light = Light((250,250), radius=300, color=(255,220,160), intensity=1.0)

# in your update loop:
vis_poly = sc.compute_visibility_polygon(light, obstacles)
# create a surface 'lighting' same as screen
lighting = pygame.Surface(screen.get_size(), flags=pygame.SRCALPHA)
# render darkness and light:
render_light_with_shadows(lighting, light, vis_poly)
# blit lighting to screen (it will darken area and add light)
screen.blit(lighting, (0,0))
"""
