"""
Tile-based procedural assembly

Ogni tile della mappa viene piazzato con regole (tipo Wave Function Collapse o algoritmi simili).
"""

# wfc_generator.py
# -----------------------------------------------------------------------------
# Wave Function Collapse (Simple Tiled Model) per tilemap 2D
# - Definisci tiles con "socket" sui bordi (N,E,S,W): stringhe che devono combaciare
# - Il solver collassa cella per cella, propagando vincoli finché non è valido
# - Supporta rotazioni (crea varianti) e pesi (probabilità)
# - Ritorna una griglia di indici/nomi/ids e può esportare Tiled JSON
# -----------------------------------------------------------------------------

from __future__ import annotations
import json
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

__all__ = ["rotate_edges", "Tile", "TileVariant", "TileSet", "WFCGrid", "WFCSolver"]

# ----------------------------
# Direzioni e utilità
# ----------------------------
DIRS = ["N", "E", "S", "W"]
DX = {"E": 1, "W": -1, "N": 0, "S": 0}
DY = {"E": 0, "W": 0, "N": -1, "S": 1}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}

def rotate_edges(edges: Tuple[str,str,str,str], k: int) -> Tuple[str,str,str,str]:
    """Ruota (N,E,S,W) di k volte 90° CW → (W,N,E,S) per k=1."""
    N, E, S, W = edges
    for _ in range(k % 4):
        N, E, S, W = (W, N, E, S)
    return (N, E, S, W)

# ----------------------------
# Tiles e Tileset
# ----------------------------
@dataclass(frozen=True)
class Tile:
    """Tile base (senza rotazione)."""
    name: str
    edges: Tuple[str, str, str, str]  # (N, E, S, W)
    weight: float = 1.0
    allow_rotate: bool = True

@dataclass(frozen=True)
class TileVariant:
    """Variante ruotata/specifica di un Tile (nome unico, edges ruotati)."""
    name: str
    base: str
    rotation: int  # 0..3 (numero di rotazioni 90° CW)
    edges: Tuple[str, str, str, str]
    weight: float
    # opzionale: id di tileset per export (se li hai già mappati)
    tile_id: Optional[int] = None

class TileSet:
    """
    Collezione di Tile + generazione varianti (rotazioni), più tabelle di compatibilità.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._tiles: Dict[str, Tile] = {}
        self.variants: List[TileVariant] = []
        # compat[idx][dir] = set(indices compatibili nella direzione dir)
        self.compat: List[Dict[str, Set[int]]] = []

    def add_tile(self, name: str, edges: Tuple[str,str,str,str], weight: float = 1.0, allow_rotate: bool = True):
        assert name not in self._tiles, f"Tile '{name}' duplicato"
        self._tiles[name] = Tile(name=name, edges=edges, weight=weight, allow_rotate=allow_rotate)

    def bake(self, rotations=(0,1,2,3), id_map: Optional[Dict[str,int]] = None):
        """
        Crea varianti ruotate e pre‐calcola compatibilità.
        - rotations: quali rotazioni abilitare globalmente (default tutte)
        - id_map: mapping opzionale {variant_name -> tile_id} per export Tiled
                  Se non dato, potrai mappare dopo con to_tile_id_grid(...)
        """
        # 1) Crea varianti
        variants: List[TileVariant] = []
        for tile in self._tiles.values():
            rots = rotations if tile.allow_rotate else (0,)
            for r in rots:
                vname = f"{tile.name}@r{r}"
                edges_r = rotate_edges(tile.edges, r)
                tile_id = id_map.get(vname) if id_map else None
                variants.append(TileVariant(
                    name=vname,
                    base=tile.name,
                    rotation=r,
                    edges=edges_r,
                    weight=tile.weight,
                    tile_id=tile_id
                ))
        self.variants = variants

        # 2) Pre‐compute compatibilità per direzione:
        # un tile A è compatibile con B a destra se A.E == B.W (socket uguali)
        n = len(self.variants)
        self.compat = [{d: set() for d in DIRS} for _ in range(n)]

        def match(a: TileVariant, b: TileVariant, d: str) -> bool:
            # vuole: a.edges[d] == b.edges[OPPOSITE[d]]
            idx_a = {"N":0,"E":1,"S":2,"W":3}[d]
            idx_b = {"N":0,"E":1,"S":2,"W":3}[OPPOSITE[d]]
            return a.edges[idx_a] == b.edges[idx_b]

        for i, a in enumerate(self.variants):
            for j, b in enumerate(self.variants):
                for d in DIRS:
                    if match(a, b, d):
                        self.compat[i][d].add(j)

    # utilità per pesi
    def weights(self, domain: Set[int]) -> List[float]:
        return [self.variants[i].weight for i in domain]

# ----------------------------
# Griglia WFC (domini per cella)
# ----------------------------
class WFCGrid:
    """
    Griglia di domini (insiemi di indici di varianti possibili).
    """
    def __init__(self, tileset: TileSet, width: int, height: int):
        self.ts = tileset
        self.w = width
        self.h = height
        full = set(range(len(self.ts.variants)))
        self.domains: List[Set[int]] = [set(full) for _ in range(self.w * self.h)]

    def idx(self, x: int, y: int) -> int:
        return y * self.w + x

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def cell_domain(self, x: int, y: int) -> Set[int]:
        return self.domains[self.idx(x,y)]

    def set_domain(self, x: int, y: int, new_domain: Set[int]):
        self.domains[self.idx(x,y)] = set(new_domain)

    def ban_all_except(self, x: int, y: int, keep: int):
        self.set_domain(x, y, {keep})

    def entropy(self, x: int, y: int) -> float:
        d = self.cell_domain(x,y)
        if len(d) <= 1:
            return 0.0
        weights = [self.ts.variants[i].weight for i in d]
        W = sum(weights)
        if W == 0:
            return 0.0
        # Shannon entropy pesata
        H = 0.0
        for w in weights:
            p = w / W
            H -= p * math.log(p + 1e-12)
        # Un piccolo rumore per break dei pareggi
        return H + (1e-6 * random.random())

    def most_constrained_cell(self) -> Optional[Tuple[int,int]]:
        """Ritorna la cella con min #opzioni (>1), cioè min entropy > 0 (heuristic)."""
        best = None
        best_len = 999999
        for y in range(self.h):
            for x in range(self.w):
                L = len(self.cell_domain(x,y))
                if 1 < L < best_len:
                    best_len = L
                    best = (x,y)
        return best

# ----------------------------
# Solver WFC (osserva → collassa → propaga) con backtracking leggero
# ----------------------------
class WFCSolver:
    def __init__(self, tileset: TileSet, width: int, height: int, seed: Optional[int] = None):
        self.ts = tileset
        self.grid = WFCGrid(tileset, width, height)
        self.rng = random.Random(seed)
        # stack per backtracking: (snapshot_domains, (x,y), alternative_choices)
        self.branches: List[Tuple[List[Set[int]], Tuple[int,int], List[int]]] = []

    # ------------------------
    # Vincoli opzionali
    # ------------------------
    def constrain_border(self, allowed_variants: Set[int]):
        """Esempio: impone che i bordi usino solo certi tile (o tutti)."""
        for x in range(self.grid.w):
            for y in [0, self.grid.h-1]:
                self.grid.set_domain(x, y, self.grid.cell_domain(x,y) & allowed_variants)
        for y in range(self.grid.h):
            for x in [0, self.grid.w-1]:
                self.grid.set_domain(x, y, self.grid.cell_domain(x,y) & allowed_variants)

    def constrain_cell_to(self, x: int, y: int, variant_indices: Set[int]):
        self.grid.set_domain(x, y, self.grid.cell_domain(x,y) & variant_indices)

    # ------------------------
    # Core WFC
    # ------------------------
    def observe(self) -> Optional[Tuple[int,int]]:
        """Sceglie cella con min dominio (>1), collassa a una scelta pesata."""
        target = self.grid.most_constrained_cell()
        if target is None:
            return None  # già tutto collassato

        x, y = target
        domain = list(self.grid.cell_domain(x, y))
        weights = [self.ts.variants[i].weight for i in domain]
        # scegli una tile secondo i pesi
        choice = self.rng.choices(domain, weights=weights, k=1)[0]
        # salva ramo per backtracking (alternative = domain - {choice})
        alternatives = [t for t in domain if t != choice]
        snapshot = [set(d) for d in self.grid.domains]  # deep copy semplice
        self.branches.append((snapshot, (x,y), alternatives))
        # collassa
        self.grid.ban_all_except(x, y, choice)
        return (x,y)

    def propagate(self) -> bool:
        """Propagazione dei vincoli finché si stabilizza. Ritorna False se contraddizione."""
        queue: List[Tuple[int,int]] = []
        # Inizializza con tutte le celle (opz.) o con l'ultima osservata
        for y in range(self.grid.h):
            for x in range(self.grid.w):
                queue.append((x,y))

        while queue:
            x, y = queue.pop()
            domain_xy = self.grid.cell_domain(x,y)
            if not domain_xy:
                return False  # Contraddizione: nessuna possibilità in (x,y)

            # per ogni vicino, filtra i domini incompatibili
            for d in DIRS:
                nx, ny = x + DX[d], y + DY[d]
                if not self.grid.in_bounds(nx, ny):
                    continue
                before = self.grid.cell_domain(nx, ny)
                after = self._enforce_neighbor_domain(before, domain_xy, OPPOSITE[d], d)
                if after is None:
                    return False  # Contraddizione
                if after != before:
                    self.grid.set_domain(nx, ny, after)
                    queue.append((nx, ny))
        return True

    def _enforce_neighbor_domain(
        self,
        neighbor_domain: Set[int],
        this_domain: Set[int],
        neighbor_side: str,  # es: "W" se il vicino guarda verso questa cella da OPPOSITE[d]
        this_dir: str,       # es: "E" lato di questa cella verso il vicino
    ) -> Optional[Set[int]]:
        """
        Mantiene nel neighbor_domain solo i tile che hanno ALMENO un compatibile
        con uno dei tile in this_domain, dalla prospettiva dei lati indicati.
        """
        allowed: Set[int] = set()
        # Un tile n del vicino è valido se esiste t in this_domain tale che n ∈ compat[t][this_dir]
        # (cioè guardo la compatibilità dalla cella corrente verso il vicino)
        possible_neighbors: Set[int] = set()
        for t in this_domain:
            possible_neighbors |= self.ts.compat[t][this_dir]

        for n in neighbor_domain:
            if n in possible_neighbors:
                allowed.add(n)

        if not allowed:
            return None
        return allowed

    def backtrack(self) -> bool:
        """Ripristina l'ultimo snapshot e prova un'alternativa. Ritorna False se esaurite."""
        while self.branches:
            snapshot, (x,y), alternatives = self.branches.pop()
            if not alternatives:
                continue
            # ripristina lo snapshot
            self.grid.domains = [set(d) for d in snapshot]
            # scegli una alternativa
            choice = alternatives.pop()
            # pusha di nuovo il ramo con le alternative rimanenti
            self.branches.append((snapshot, (x,y), alternatives))
            # collassa a choice
            self.grid.ban_all_except(x, y, choice)
            return True
        return False

    def solve(self, max_steps: int = 100000) -> bool:
        """
        Esegue osserva→propaga finché:
        - successo (nessuna cella con >1 possibilità)
        - contraddizione → backtrack → continua
        """
        steps = 0
        while steps < max_steps:
            steps += 1
            target = self.grid.most_constrained_cell()
            if target is None:
                # tutte le celle sono collassate → success
                return True

            # osserva (collassa una cella)
            self.observe()

            # propaga
            if not self.propagate():
                # contraddizione: backtrack; se non possibile, fallisce
                if not self.backtrack():
                    return False
        # protezione cicli infiniti
        return False

    # ------------------------
    # Export utilities
    # ------------------------
    def to_variant_name_grid(self) -> List[List[str]]:
        """Griglia di nomi variante (string)."""
        out: List[List[str]] = []
        for y in range(self.grid.h):
            row = []
            for x in range(self.grid.w):
                d = self.grid.cell_domain(x,y)
                assert len(d) == 1, "Griglia non completamente collassata"
                idx = next(iter(d))
                row.append(self.ts.variants[idx].name)
            out.append(row)
        return out

    def to_tile_id_grid(self, default_id: int = 0, mapping: Optional[Dict[str,int]] = None) -> List[List[int]]:
        """
        Griglia di tile_id (int) per integrazione diretta con i tuoi loader.
        - mapping opzionale: {variant_name -> tile_id} (se non avevi passato id_map in bake)
        - altrimenti usa variant.tile_id; se entrambi mancanti → default_id
        """
        out: List[List[int]] = []
        for y in range(self.grid.h):
            row = []
            for x in range(self.grid.w):
                d = self.grid.cell_domain(x,y)
                assert len(d) == 1, "Griglia non completamente collassata"
                idx = next(iter(d))
                v = self.ts.variants[idx]
                gid = None
                if v.tile_id is not None:
                    gid = v.tile_id
                elif mapping is not None:
                    gid = mapping.get(v.name, default_id)
                else:
                    gid = default_id
                row.append(gid)
            out.append(row)
        return out

    def to_tiled_json(
        self,
        tilewidth: int,
        tileheight: int,
        tileset_source_tsx: str,
        firstgid: int = 1,
        layer_name: str = "Terrain"
    ) -> Dict:
        """
        Crea un dizionario Tiled Map JSON (1 layer) con i tile_id della griglia.
        Nota: presuppone che i tuoi tile_id (gid) siano allineati al tuo TSX.
        """
        data_rows = self.to_tile_id_grid(default_id=0)
        # Tiled vuole flat array row-major:
        flat = [gid for row in data_rows for gid in row]

        return {
            "compressionlevel": -1,
            "height": self.grid.h,
            "infinite": False,
            "layers": [
                {
                    "data": flat,
                    "height": self.grid.h,
                    "id": 1,
                    "name": layer_name,
                    "opacity": 1,
                    "type": "tilelayer",
                    "visible": True,
                    "width": self.grid.w,
                    "x": 0,
                    "y": 0
                }
            ],
            "nextlayerid": 2,
            "nextobjectid": 1,
            "orientation": "orthogonal",
            "renderorder": "right-down",
            "tiledversion": "1.11.2",
            "tileheight": tileheight,
            "tilesets": [
                { "firstgid": firstgid, "source": tileset_source_tsx }
            ],
            "tilewidth": tilewidth,
            "type": "map",
            "version": "1.10",
            "width": self.grid.w
        }

# ----------------------------
# ESEMPIO DI UTILIZZO (minimal)
# ----------------------------
if __name__ == "__main__":
    # Esempio didattico di tileset a "strade su prato"
    # Socket: "g" = grass, "r" = road
    ts = TileSet(seed=123)

    # Tile base (senza rotazione); edges = (N,E,S,W)
    # - grass pieno (tutti 'g') → si attacca a qualunque 'g'
    ts.add_tile("grass", ("g","g","g","g"), weight=2.0, allow_rotate=False)

    # Strada "dritta" (N/S = r, E/W = g) — ruotabile per ottenere orizzontale
    ts.add_tile("road_straight", ("r","g","r","g"), weight=1.0, allow_rotate=True)

    # Curva (N/E = r, S/W = g) — ruotabile per tutte le curve
    ts.add_tile("road_curve", ("r","r","g","g"), weight=1.0, allow_rotate=True)

    # T (N,E,S = r, W = g) — ruotabile
    ts.add_tile("road_t", ("r","r","r","g"), weight=0.7, allow_rotate=True)

    # Incrocio (+) (tutti r)
    ts.add_tile("road_cross", ("r","r","r","r"), weight=0.3, allow_rotate=False)

    # Genera varianti ruotate e compatibilità
    # Se già hai GID specifici per ogni variante, passa id_map={ "road_curve@r1": 42, ... }
    ts.bake()

    # Crea solver per una mappa 30x20
    solver = WFCSolver(ts, width=30, height=20, seed=42)

    # Esempio di vincolo: ai bordi non voglio strade (solo 'grass' o comunque socket 'g' su lato esterno)
    # Ricavo i variant con tutti i lati 'g' (qui solo 'grass')
    border_ok = set(i for i,v in enumerate(ts.variants) if all(e=="g" for e in v.edges))
    solver.constrain_border(border_ok)

    # Risolvi
    ok = solver.solve()
    print("Solved:", ok)

    # Export come Tiled JSON (userai il tuo TSX)
    if ok:
        tiled = solver.to_tiled_json(
            tilewidth=16, tileheight=16,
            tileset_source_tsx="dungeon.tsx",
            firstgid=1,
            layer_name="AutoWFC"
        )
        with open("assets/tilemaps/generated_wfc.json", "w") as f:
            json.dump(tiled, f, indent=2)
        print("Salvata mappa Tiled in assets/tilemaps/generated_wfc.json")

"""
Come funziona

Definisci i tile base con i socket sui bordi (N,E,S,W). Due tile sono compatibili affiancati se i socket combaciano (es. r con r, g con g).
TileSet.bake() genera automaticamente varianti ruotate e costruisce una tabella di compatibilità per ogni direzione.

WFCSolver.solve():
sceglie la cella con minor numero di possibilità (min entropy);
collassa a una variante scelta in base ai pesi;
propaga vincoli ai vicini, eliminando varianti incompatibili;
se trova contraddizioni, fa backtracking (ripristina uno snapshot e prova alternative).
to_tiled_json(...) esporta un JSON compatibile con Tiled (puoi metterlo in assets/tilemaps/ e caricarlo col tuo TilemapManager).
"""