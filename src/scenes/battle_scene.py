import pygame
import random
from engine.core.core import Scene, GameContext
from src.settings import *
from src.entities.soul import Soul
from src.entities.bullet import Bullet

class BattleScene(Scene):
    def __init__(self, ctx: GameContext):
        super().__init__(ctx, "battle_scene")
        
        # Battle States
        self.STATE_MENU = "menu"
        self.STATE_DEFENSE = "defense"
        self.current_state = self.STATE_MENU
        
        # Arena Box
        self.arena_rect = pygame.Rect(
            INTERNAL_WIDTH // 2 - 50, 
            INTERNAL_HEIGHT // 2 - 20, 
            100, 100
        )
        self.arena_border = 3
        
        # Groups
        self.visible_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.soul = Soul(self.arena_rect.center, [self.visible_sprites], self.arena_rect)
        
        # Menu Selection
        self.menu_options = ["FIGHT", "ACT", "ITEM", "MERCY"]
        self.current_selection = 0
        
        # Pattern management
        self.spawn_timer = 0
        self.spawn_cooldown = 0.5 # seconds
        
    def on_enter(self, payload=None):
        print("Battle Started!")
        self.soul.pos = pygame.math.Vector2(self.arena_rect.center)
        self.soul.rect.center = self.arena_rect.center
        self.current_state = self.STATE_MENU

    def spawn_bullet(self):
        # Spawning from random side towards center
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            pos = (random.randint(self.arena_rect.left, self.arena_rect.right), self.arena_rect.top - 20)
            dir = pygame.math.Vector2(0, 1)
        elif side == 'bottom':
            pos = (random.randint(self.arena_rect.left, self.arena_rect.right), self.arena_rect.bottom + 20)
            dir = pygame.math.Vector2(0, -1)
        elif side == 'left':
            pos = (self.arena_rect.left - 20, random.randint(self.arena_rect.top, self.arena_rect.bottom))
            dir = pygame.math.Vector2(1, 0)
        else:
            pos = (self.arena_rect.right + 20, random.randint(self.arena_rect.top, self.arena_rect.bottom))
            dir = pygame.math.Vector2(-1, 0)
            
        Bullet(pos, dir, 100, [self.visible_sprites, self.bullet_sprites])

    def update(self, dt: float):
        if self.current_state == self.STATE_DEFENSE:
            self.visible_sprites.update(dt)
            
            # Spawn bullets
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_cooldown:
                self.spawn_timer = 0
                self.spawn_bullet()
                
            # Collision check
            if pygame.sprite.spritecollide(self.soul, self.bullet_sprites, True):
                print("PLAYER HIT!")
                # TODO: Implement HP reduction
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_x]:
                # Clear bullets when leaving defense
                for bullet in self.bullet_sprites:
                    bullet.kill()
                self.current_state = self.STATE_MENU
        else:
            self.handle_menu()

    def handle_menu(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_z] or keys[pygame.K_RETURN]:
            self.current_state = self.STATE_DEFENSE
            self.spawn_timer = 0

    def draw(self, surface):
        surface.fill(BLACK)
        
        # Draw Arena
        pygame.draw.rect(surface, WHITE, self.arena_rect, self.arena_border)
        
        # Draw Menu Buttons
        if self.current_state == self.STATE_MENU:
            for i, option in enumerate(self.menu_options):
                color = YELLOW if i == self.current_selection else WHITE
                btn_rect = pygame.Rect(10 + i * (INTERNAL_WIDTH // 4), INTERNAL_HEIGHT - 30, 60, 20)
                pygame.draw.rect(surface, color, btn_rect, 1)
        
        # Draw All Sprites (Soul and Bullets)
        for sprite in self.visible_sprites:
            # We don't apply camera in battle scene usually
            surface.blit(sprite.image, sprite.rect)
