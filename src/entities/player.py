import pygame
from src.settings import *
from engine.systems.input_manager import InputManager

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacle_sprites, input_manager: InputManager):
        super().__init__(groups)
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(RED) # Placeholder
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10) # Smaller hitbox for depth

        self.direction = pygame.math.Vector2()
        self.speed = 200 # pixels per second
        self.pos = pygame.math.Vector2(self.rect.center)

        self.obstacle_sprites = obstacle_sprites
        self.input_manager = input_manager
        
        # Placeholder for asset loading
        # self.import_assets()

    def import_assets(self):
        # TODO: Load .png files for animations
        # self.animations = {'up': [], 'down': [], 'left': [], 'right': [], ...}
        pass

    def input(self):
        keys = pygame.key.get_pressed()
        
        # Movement
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.direction.y = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.direction.y = 1
        else:
            self.direction.y = 0

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction.x = 1
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction.x = -1
        else:
            self.direction.x = 0

    def check_interaction(self, interactable_sprites):
        # Look for the sprite in front of the player
        # For simplicity, we check a small area around the player
        interaction_rect = self.hitbox.inflate(20, 20)
        for sprite in interactable_sprites:
            if hasattr(sprite, 'interact') and sprite.hitbox.colliderect(interaction_rect):
                return sprite
        return None

    def move(self, dt):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.collision('horizontal')
        self.rect.centerx = self.hitbox.centerx

        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.collision('vertical')
        self.rect.centery = self.hitbox.centery

    def collision(self, direction):
        if direction == 'horizontal':
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0: # Moving right
                        self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0: # Moving left
                        self.hitbox.left = sprite.hitbox.right
                    self.pos.x = self.hitbox.centerx 

        if direction == 'vertical':
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0: # Moving down
                        self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0: # Moving up
                        self.hitbox.top = sprite.hitbox.bottom
                    self.pos.y = self.hitbox.centery

    def update(self, dt):
        self.input()
        self.move(dt)
