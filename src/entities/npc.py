import pygame
from src.settings import *

class NPC(pygame.sprite.Sprite):
    def __init__(self, pos, groups, name, dialogue):
        super().__init__(groups)
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(GREEN) # Placeholder color for NPC
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)
        
        self.name = name
        self.dialogue = dialogue

    def interact(self, dialogue_box):
        if not dialogue_box.active:
            dialogue_box.start_dialogue(self.dialogue)
