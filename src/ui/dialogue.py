import pygame
from src.settings import *

class DialogueBox:
    def __init__(self):
        self.active = False
        self.text = ""
        self.display_text = ""
        self.char_index = 0
        self.timer = 0
        self.speed = 2 # Characters per tick (or adjust with dt)
        
        # Define box properties (bottom of screen)
        # Scaled coordinates: drawing mainly on Internal Surface
        self.rect = pygame.Rect(10, INTERNAL_HEIGHT - 70, INTERNAL_WIDTH - 20, 60)
        self.font = pygame.font.Font(None, 16) # Placeholder font
        self.bg_color = BLACK
        self.border_color = WHITE
        self.text_color = WHITE

    def start_dialogue(self, text):
        self.active = True
        self.text = text
        self.display_text = ""
        self.char_index = 0
        self.timer = 0

    def update(self, dt):
        if not self.active:
            return
            
        if self.char_index < len(self.text):
            self.timer += 100 * dt # Faster typing
            if self.timer >= 1:
                self.timer = 0
                self.display_text += self.text[self.char_index]
                self.char_index += 1
        
        # In actual Undertale, 'Z' advances and 'X' skips. 
        # For simplicity, 'Z' closes if finish, or 'X' could skip.
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_z] or keys[pygame.K_RETURN]) and self.char_index >= len(self.text):
             self.active = False
             # Small delay to prevent re-triggering immediately
             pygame.time.delay(100)

    def draw(self, surface):
        if not self.active:
            return
            
        pygame.draw.rect(surface, self.bg_color, self.rect)
        pygame.draw.rect(surface, self.border_color, self.rect, 2)
        
        # Simple text wrapping could be added here
        text_surf = self.font.render(self.display_text, False, self.text_color)
        surface.blit(text_surf, (self.rect.x + 5, self.rect.y + 5))
