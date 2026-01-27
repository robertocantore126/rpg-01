import pygame
from src.settings import *

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, speed, groups):
        super().__init__(groups)
        self.image = pygame.Surface((8, 8))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=pos)
        
        self.direction = direction.normalize() if direction.magnitude() > 0 else pygame.math.Vector2(0, 1)
        self.speed = speed
        self.pos = pygame.math.Vector2(self.rect.center)

    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        
        # Kill if it leaves the screen area or a buffer around it
        if not (-50 < self.rect.x < INTERNAL_WIDTH + 50 and -50 < self.rect.y < INTERNAL_HEIGHT + 50):
            self.kill()
