"""
3. Proprietà dei dati e responsabilità
Questo è il punto più importante:
Gli oggetti di gioco (player, nemici, item, tile) sono proprietari del loro stato logico:
player.rect = posizione reale nella mappa.
enemy.rect = idem.
tile.rect = posizione fissa nella griglia.

Camera = solo trasformazione di rendering
La camera prende i .rect logici e calcola la posizione relativa allo schermo.
Questo avviene dentro Camera.apply(), che restituisce un nuovo Rect già “shiftato”.
Tu lo usi solo al momento del draw.
"""
import pygame

from engine.world.constants import LETTERBOXING_BANDS, SCREEN_HEIGHT, SCREEN_WIDTH

__all__ = ["Camera", "ViewportManager"]

class Camera:
    def __init__(self, width, height, screen_width, screen_height, camera_type="hard"):
        # Dimensioni logiche del mondo visibile
        self.width = width
        self.height = height

        # Dimensioni fisiche dello schermo
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Offset della camera (in mondo)
        self.offset = pygame.Vector2(0, 0)

        # Zoom (1.0 = 1:1 logico→viewport)
        self.zoom = 1.0  

        # Parametri movimento
        self.camera_type = camera_type
        self.smooth_speed = 0.1
        self.spring_strength = 0.2
        self.spring_velocity = pygame.Vector2(0, 0)

        # Clamping (limiti mappa)
        self.world_width = None
        self.world_height = None

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        """Trasforma un rect da mondo a schermo (con offset + zoom)."""
        x = (rect.x - self.offset.x) * self.zoom
        y = (rect.y - self.offset.y) * self.zoom
        w = rect.width * self.zoom
        h = rect.height * self.zoom
        return pygame.Rect(x, y, w, h)

    def world_to_screen(self, pos: pygame.Vector2) -> pygame.Vector2:
        """Coordinate mondo → schermo."""
        return pygame.Vector2(
            (pos.x - self.offset.x) * self.zoom,
            (pos.y - self.offset.y) * self.zoom
        )

    def screen_to_world(self, pos: pygame.Vector2) -> pygame.Vector2:
        """Coordinate schermo → mondo."""
        return pygame.Vector2(
            pos.x / self.zoom + self.offset.x,
            pos.y / self.zoom + self.offset.y
        )

    def update(self, target_rect: pygame.Rect):
        """Aggiorna l'offset in base al target (es. player)."""
        target_pos = pygame.Vector2(
            target_rect.centerx - self.width // 2,
            target_rect.centery - self.height // 2
        )

        if self.camera_type == "hard":
            self.offset = target_pos

        elif self.camera_type == "soft":
            self.offset += (target_pos - self.offset) * self.smooth_speed

        elif self.camera_type == "spring":
            displacement = target_pos - self.offset
            acceleration = displacement * self.spring_strength
            self.spring_velocity += acceleration
            self.spring_velocity *= 0.85
            self.offset += self.spring_velocity

        # Clamping se la mappa è definita
        if self.world_width and self.world_height:
            self.offset.x = max(0, min(self.offset.x, self.world_width - self.width))
            self.offset.y = max(0, min(self.offset.y, self.world_height - self.height))

    def get_viewport_rect(self) -> pygame.Rect:
        """Restituisce il rettangolo visibile in coordinate mondo."""
        return pygame.Rect(self.offset.x, self.offset.y, self.width, self.height)

    def set_world_bounds(self, width, height):
        """Imposta i limiti della mappa (per clamping)."""
        self.world_width = width
        self.world_height = height

    def set_zoom(self, zoom: float):
        """Cambia lo zoom, mantenendo centrata la camera."""
        old_center = self.get_viewport_rect().center
        self.zoom = max(0.1, min(zoom, 5.0))  # evita valori assurdi
        # Re-centra dopo il cambio zoom
        cx, cy = old_center
        self.offset.x = cx - self.width // (2 * self.zoom)
        self.offset.y = cy - self.height // (2 * self.zoom)


class ViewportManager:
    def __init__(self, game_w, game_h, screen_w, screen_h):
        self.game_w = game_w
        self.game_h = game_h
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Calcola il fattore di scala (mantiene aspect ratio)
        self.scale = min(screen_w / game_w, screen_h / game_h)

        # Dimensioni della superficie di rendering scalata
        self.scaled_w = int(game_w * self.scale)
        self.scaled_h = int(game_h * self.scale)

        # Offset per il letterboxing
        self.offset_x = (screen_w - self.scaled_w) // 2
        self.offset_y = (screen_h - self.scaled_h) // 2

        # Superficie logica (dove si disegna tutto il gioco)
        # canvas: superficie logica --- screen: viewport reale
        self.game_surface = pygame.Surface((game_w, game_h))
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    def draw(self, screen):
        """Scala e disegna la superficie di gioco sullo schermo con letterbox."""
        scaled_surface = pygame.transform.scale(
            self.game_surface, (self.scaled_w, self.scaled_h)
        )
        screen.fill(LETTERBOXING_BANDS)  # bande nere
        screen.blit(scaled_surface, (self.offset_x, self.offset_y))

    def screen_to_game(self, pos: tuple[int, int]) -> pygame.Vector2:
        """Converte coordinate schermo → coordinate logiche di gioco."""
        x = (pos[0] - self.offset_x) / self.scale
        y = (pos[1] - self.offset_y) / self.scale
        return pygame.Vector2(x, y)

    def game_to_screen(self, pos: tuple[int, int]) -> pygame.Vector2:
        """Converte coordinate gioco → coordinate schermo."""
        x = pos[0] * self.scale + self.offset_x
        y = pos[1] * self.scale + self.offset_y
        return pygame.Vector2(x, y)
    
