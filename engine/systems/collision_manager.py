__all__ = ["CollisionManager"]

import pygame
from typing import List
from engine.world.constants import EventType, CollisionSide
from engine.systems.event_bus import EventBus


class CollisionManager:
    def __init__(self, event_bus: EventBus, pixel_perfect=False):
        self.pixel_perfect = pixel_perfect
        self.event_bus = event_bus
        self.objects: List[object] = []  # lista di game objects registrati

    def register_object(self, obj):
        """Aggiunge un oggetto alla lista di quelli monitorati"""
        if not hasattr(obj, "rect"):
            raise AttributeError(f"{obj} non ha un attributo 'rect'")
        if obj not in self.objects:
            self.objects.append(obj)

    def unregister_object(self, obj):
        """Rimuove un oggetto dalla lista"""
        if obj in self.objects:
            self.objects.remove(obj)

    def clear(self):
        """Svuota la lista (es: quando cambio scena)"""
        self.objects.clear()

    def update(self):
        for i in range(len(self.objects)):
            for j in range(i + 1, len(self.objects)):
                obj1 = self.objects[i]
                obj2 = self.objects[j]

                if self._check_collision(obj1, obj2):
                    side = self.get_CollisionSide(obj1.rect, obj2.rect) # type: ignore
                    self.event_bus.publish(EventType.COLLISION, {
                        "a": obj1,
                        "b": obj2,
                        "side": side
                    })

    def _check_collision(self, obj1, obj2):
        if self.pixel_perfect:
            return self._pixel_perfect_collision(obj1, obj2)
        else:
            return self._aabb_collision(obj1, obj2)

    def _aabb_collision(self, obj1, obj2):
        return obj1.rect.colliderect(obj2.rect)

    def _pixel_perfect_collision(self, obj1, obj2):
        if not obj1.rect.colliderect(obj2.rect):
            return False
        mask1 = pygame.mask.from_surface(obj1.image)
        mask2 = pygame.mask.from_surface(obj2.image)
        offset = (obj2.rect.x - obj1.rect.x, obj2.rect.y - obj1.rect.y)
        overlap = mask1.overlap(mask2, offset)
        return overlap is not None
    
    def get_CollisionSide(self, rect1: pygame.Rect, rect2: pygame.Rect):
        """Ritorna il lato della collisione di rect1 rispetto a rect2"""
        # Intersezione
        intersection = rect1.clip(rect2)
        if intersection.width == 0 or intersection.height == 0:
            return None  # nessuna collisione

        # Centri
        cx1, cy1 = rect1.center
        cx2, cy2 = rect2.center

        # Determina se l'asse dominante è X o Y
        if intersection.width < intersection.height:
            # Collisione orizzontale
            if cx1 < cx2:
                return CollisionSide.RIGHT  # rect1 ha colpito rect2 da sinistra
            else:
                return CollisionSide.LEFT   # rect1 ha colpito rect2 da destra
        else:
            # Collisione verticale
            if cy1 < cy2:
                return CollisionSide.BOTTOM # rect1 ha colpito rect2 da sopra
            else:
                return CollisionSide.TOP    # rect1 ha colpito rect2 da sotto
