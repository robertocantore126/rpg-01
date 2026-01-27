import pygame
from src.settings import *

class Soul(pygame.sprite.Sprite):
    def __init__(self, pos, groups, arena_rect):
        super().__init__(groups)
        # Placeholder heart: red square (Undertale soul is usually 16x16 or smaller)
        self.image = pygame.Surface((10, 10))
        self.image.fill(RED)
        
        self.rect = self.image.get_rect(center=pos)
        self.arena_rect = arena_rect
        
        self.speed = 150
        self.pos = pygame.math.Vector2(self.rect.center)

    def input(self):
        keys = pygame.key.get_pressed()
        
        direction = pygame.math.Vector2()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction.y = 1
            
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction.x = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction.x = 1
            
        if direction.magnitude() > 0:
            direction = direction.normalize()
            
        return direction

    def update(self, dt):
        direction = self.input()
        
        # Move
        self.pos += direction * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        
        # Constrain to Arena
        if self.rect.left < self.arena_rect.left:
            self.rect.left = self.arena_rect.left
            self.pos.x = self.rect.centerx
        if self.rect.right > self.arena_rect.right:
            self.rect.right = self.arena_rect.right
            self.pos.x = self.rect.centerx
        if self.rect.top < self.arena_rect.top:
            self.rect.top = self.arena_rect.top
            self.pos.y = self.rect.centery
        if self.rect.bottom > self.arena_rect.bottom:
            self.rect.bottom = self.arena_rect.bottom
            self.pos.y = self.rect.centery
