import pygame
from engine.core.core import Scene, GameContext
from src.settings import *
from src.entities.player import Player
from src.entities.npc import NPC
from src.ui.dialogue import DialogueBox

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(groups)
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(BLUE) # Wall color
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)

class WorldScene(Scene):
    def __init__(self, ctx: GameContext):
        super().__init__(ctx, "world_scene")
        
        # Groups
        self.visible_sprites = pygame.sprite.Group()
        self.obstacle_sprites = pygame.sprite.Group()
        self.interactable_sprites = pygame.sprite.Group()
        
        # Map Setup (Matrix)
        self.map_data = [
            ['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
            ['x','.','.','.','.','.','.','.','.','.','.','.','.','.','x'],
            ['x','.','x','x','.','.','.','.','.','.','.','.','x','.','x'],
            ['x','.','x','x','.','.','.','.','.','.','.','.','x','.','x'],
            ['x','.','.','.','.','.','P','.','.','.','.','.','.','.','x'],
            ['x','.','.','.','.','.','.','.','.','N','.','.','.','.','x'],
            ['x','.','.','.','.','x','x','x','x','x','.','.','.','.','x'],
            ['x','.','.','.','.','.','.','.','.','.','.','.','.','.','x'],
            ['x','x','x','x','x','x','x','x','x','x','x','x','x','x','x'],
        ]
        self.create_map()
        
        # Dialogue
        self.dialogue_box = DialogueBox()
        
        # Camera
        self.camera = self.ctx.services.get("camera")
        self.camera.set_world_bounds(len(self.map_data[0]) * TILESIZE, len(self.map_data) * TILESIZE)
        
    def create_map(self):
        input_manager = self.ctx.services.get("inputs")
        
        for row_index, row in enumerate(self.map_data):
            for col_index, col in enumerate(row):
                x = col_index * TILESIZE
                y = row_index * TILESIZE
                if col == 'x':
                    Tile((x, y), [self.visible_sprites, self.obstacle_sprites])
                if col == 'P':
                    self.player = Player((x, y), [self.visible_sprites], self.obstacle_sprites, input_manager)
                if col == 'N':
                    NPC((x, y), [self.visible_sprites, self.interactable_sprites], "Toriel", "Don't be afraid, my child.")

    def on_enter(self, payload=None):
        print("Entered World Scene")
        self.dialogue_box.start_dialogue("Welcome to the Underground!")

    def on_exit(self): pass
    def on_pause(self): pass
    def on_resume(self): pass

    def update(self, dt: float):
        if not self.dialogue_box.active:
            self.visible_sprites.update(dt)
            
            # Check for interaction
            keys = pygame.key.get_pressed()
            if keys[pygame.K_z] or keys[pygame.K_RETURN]:
                target = self.player.check_interaction(self.interactable_sprites)
                if target:
                    target.interact(self.dialogue_box)
                    
            if keys[pygame.K_b]: # DEBUG: Battle
                self.ctx.scene_manager.push("battle")
        
        self.dialogue_box.update(dt)
        self.camera.update(self.player.rect)

    def draw(self, surface):
        surface.fill(BLACK)
        
        # Draw visible sprites with camera offset
        for sprite in self.visible_sprites:
            offset_rect = self.camera.apply(sprite.rect)
            surface.blit(sprite.image, offset_rect)
            
        self.dialogue_box.draw(surface)
