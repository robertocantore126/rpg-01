#!/usr/bin/env python3
"""
Improved Sprite Viewer - Visualizzatore pixel art avanzato con Pygame
Caratteristiche:
- Caricamento multiplo sprite
- Controlli movimento (WASD/Arrow)
- Zoom dinamico (Mouse wheel)
- Griglia opzionale (G key)
- Info sprite (I key)
- Background customizzabile (B key)
- Screenshot (S key)
- FPS counter

affinchè trovi gli sprite quando si esegue, devi cd nella cartella e per cambiare sprite devi cliccà ,. non left n right btw
"""

import pygame
import sys
import os
from pathlib import Path

class SpriteViewer:
    def __init__(self):
        # Configurazione risoluzione
        self.INTERNAL_RES = (320, 240)
        self.WINDOW_RES = (960, 720)  # Più grande per vedere meglio
        self.PIXEL_SCALE = 2  # Scala aggiuntiva per pixel art
        
        # Inizializza Pygame
        pygame.init()
        self.screen = pygame.display.set_mode(self.WINDOW_RES, pygame.RESIZABLE)
        pygame.display.set_caption("Pixel Art Sprite Viewer")
        self.canvas = pygame.Surface(self.INTERNAL_RES)
        self.clock = pygame.time.Clock()
        
        # Font per UI
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        
        # Stato visualizzazione
        self.sprites = []
        self.current_sprite_index = 0
        self.sprite_pos = [100, 100]
        self.sprite_scale = 1.0
        
        # Opzioni UI
        self.show_grid = False
        self.show_info = True
        self.show_help = False
        self.bg_index = 0
        self.backgrounds = [
            (30, 30, 30),      # Grigio scuro
            (50, 50, 50),      # Grigio medio
            (255, 255, 255),   # Bianco
            (0, 0, 0),         # Nero
            (40, 20, 60),      # Viola scuro
            (20, 40, 60),      # Blu scuro
        ]
        
        # Controlli movimento
        self.movement_speed = 2
        
    def load_sprite(self, filepath):
        """Carica uno sprite con gestione errori"""
        try:
            sprite = pygame.image.load(filepath).convert_alpha()
            self.sprites.append({
                'image': sprite,
                'filepath': filepath,
                'filename': Path(filepath).name,
                'size': sprite.get_size(),
                'original': sprite.copy()  # Mantieni originale per rescaling
            })
            print(f"✓ Caricato: {Path(filepath).name} - {sprite.get_size()}")
            return True
        except Exception as e:
            print(f"✗ Errore caricando {filepath}: {e}")
            return False
    
    def load_sprites_from_directory(self, directory="."):
        """Carica tutti i PNG da una directory"""
        loaded = 0
        for file in Path(directory).glob("*.png"):
            if self.load_sprite(str(file)):
                loaded += 1
        
        if loaded == 0:
            print(f"⚠️  Nessuno sprite PNG trovato in {directory}")
        else:
            print(f"✓ Caricati {loaded} sprite totali")
        
        return loaded > 0
    
    def get_current_sprite(self):
        """Ottieni sprite corrente"""
        if not self.sprites:
            return None
        return self.sprites[self.current_sprite_index]
    
    def next_sprite(self):
        """Vai allo sprite successivo"""
        if len(self.sprites) > 1:
            self.current_sprite_index = (self.current_sprite_index + 1) % len(self.sprites)
            self.sprite_scale = 1.0  # Reset zoom
    
    def prev_sprite(self):
        """Vai allo sprite precedente"""
        if len(self.sprites) > 1:
            self.current_sprite_index = (self.current_sprite_index - 1) % len(self.sprites)
            self.sprite_scale = 1.0  # Reset zoom
    
    def zoom_in(self):
        """Aumenta zoom"""
        self.sprite_scale = min(self.sprite_scale + 0.5, 10.0)
    
    def zoom_out(self):
        """Diminuisci zoom"""
        self.sprite_scale = max(self.sprite_scale - 0.5, 0.5)
    
    def reset_zoom(self):
        """Reset zoom a 1:1"""
        self.sprite_scale = 1.0
    
    def cycle_background(self):
        """Cambia colore sfondo"""
        self.bg_index = (self.bg_index + 1) % len(self.backgrounds)
    
    def draw_grid(self, surface):
        """Disegna griglia per riferimento pixel"""
        grid_color = (100, 100, 100, 128)
        width, height = surface.get_size()
        
        # Griglia ogni 8 pixel
        grid_size = 8
        for x in range(0, width, grid_size):
            pygame.draw.line(surface, grid_color, (x, 0), (x, height), 1)
        for y in range(0, height, grid_size):
            pygame.draw.line(surface, grid_color, (0, y), (width, y), 1)
        
        # Linee centrali più spesse
        pygame.draw.line(surface, (150, 150, 150), (width//2, 0), (width//2, height), 2)
        pygame.draw.line(surface, (150, 150, 150), (0, height//2), (width, height//2), 2)
    
    def draw_info(self, surface):
        """Disegna informazioni sprite"""
        if not self.show_info:
            return
        
        sprite_data = self.get_current_sprite()
        if not sprite_data:
            return
        
        info_lines = [
            f"Sprite: {sprite_data['filename']}",
            f"Size: {sprite_data['size'][0]}x{sprite_data['size'][1]}",
            f"Zoom: {self.sprite_scale:.1f}x",
            f"Pos: ({self.sprite_pos[0]}, {self.sprite_pos[1]})",
            f"[{self.current_sprite_index + 1}/{len(self.sprites)}]"
        ]
        
        # Box semi-trasparente
        padding = 5
        line_height = 20
        box_height = len(info_lines) * line_height + padding * 2
        box_width = 200
        
        info_surface = pygame.Surface((box_width, box_height))
        info_surface.set_alpha(200)
        info_surface.fill((0, 0, 0))
        
        # Testo
        for i, line in enumerate(info_lines):
            text = self.font_small.render(line, True, (255, 255, 255))
            info_surface.blit(text, (padding, padding + i * line_height))
        
        surface.blit(info_surface, (5, 5))
    
    def draw_help(self, surface):
        """Disegna pannello aiuto"""
        if not self.show_help:
            return
        
        help_text = [
            "=== CONTROLLI ===",
            "WASD/Arrows: Muovi sprite",
            "Mouse Wheel: Zoom in/out",
            "R: Reset zoom",
            "",
            "Left/Right: Sprite prev/next",
            "Space: Centra sprite",
            "",
            "G: Toggle griglia",
            "I: Toggle info",
            "B: Cambia background",
            "S: Screenshot",
            "H: Toggle help",
            "ESC: Esci"
        ]
        
        padding = 10
        line_height = 22
        box_height = len(help_text) * line_height + padding * 2
        box_width = 280
        
        # Centra il pannello
        x = (self.INTERNAL_RES[0] - box_width) // 2
        y = (self.INTERNAL_RES[1] - box_height) // 2
        
        help_surface = pygame.Surface((box_width, box_height))
        help_surface.set_alpha(230)
        help_surface.fill((20, 20, 40))
        pygame.draw.rect(help_surface, (100, 100, 150), help_surface.get_rect(), 2)
        
        for i, line in enumerate(help_text):
            if line.startswith("==="):
                text = self.font_large.render(line, True, (255, 255, 100))
            else:
                text = self.font_small.render(line, True, (255, 255, 255))
            help_surface.blit(text, (padding, padding + i * line_height))
        
        surface.blit(help_surface, (x, y))
    
    def draw_fps(self, surface):
        """Disegna FPS counter"""
        fps = int(self.clock.get_fps())
        color = (0, 255, 0) if fps >= 50 else (255, 255, 0) if fps >= 30 else (255, 0, 0)
        text = self.font_small.render(f"FPS: {fps}", True, color)
        surface.blit(text, (self.INTERNAL_RES[0] - 80, 5))
    
    def center_sprite(self):
        """Centra lo sprite nel canvas"""
        sprite_data = self.get_current_sprite()
        if sprite_data:
            w, h = sprite_data['size']
            self.sprite_pos[0] = (self.INTERNAL_RES[0] - w * self.sprite_scale) // 2
            self.sprite_pos[1] = (self.INTERNAL_RES[1] - h * self.sprite_scale) // 2
    
    def save_screenshot(self):
        """Salva screenshot del canvas"""
        timestamp = pygame.time.get_ticks()
        filename = f"screenshot_{timestamp}.png"
        pygame.image.save(self.canvas, filename)
        print(f"📸 Screenshot salvato: {filename}")
    
    def handle_input(self):
        """Gestisci input utente"""
        keys = pygame.key.get_pressed()
        
        # Movimento sprite
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.sprite_pos[1] -= self.movement_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.sprite_pos[1] += self.movement_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.sprite_pos[0] -= self.movement_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.sprite_pos[0] += self.movement_speed
        
        # Eventi
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                    print(f"Griglia: {'ON' if self.show_grid else 'OFF'}")
                
                elif event.key == pygame.K_i:
                    self.show_info = not self.show_info
                
                elif event.key == pygame.K_h:
                    self.show_help = not self.show_help
                
                elif event.key == pygame.K_b:
                    self.cycle_background()
                
                elif event.key == pygame.K_r:
                    self.reset_zoom()
                    print("Zoom reset a 1.0x")
                
                elif event.key == pygame.K_SPACE:
                    self.center_sprite()
                    print("Sprite centrato")
                
                elif event.key == pygame.K_s and keys[pygame.K_LCTRL]:
                    self.save_screenshot()
                
                elif event.key == pygame.K_PERIOD or event.key == pygame.K_RIGHTBRACKET:
                    self.next_sprite()
                
                elif event.key == pygame.K_COMMA or event.key == pygame.K_LEFTBRACKET:
                    self.prev_sprite()
            
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self.zoom_in()
                elif event.y < 0:
                    self.zoom_out()
            
            elif event.type == pygame.VIDEORESIZE:
                self.WINDOW_RES = (event.w, event.h)
                self.screen = pygame.display.set_mode(self.WINDOW_RES, pygame.RESIZABLE)
        
        return True
    
    def render(self):
        """Renderizza frame"""
        # Background
        self.canvas.fill(self.backgrounds[self.bg_index])
        
        # Griglia (se attiva)
        if self.show_grid:
            self.draw_grid(self.canvas)
        
        # Sprite
        sprite_data = self.get_current_sprite()
        if sprite_data:
            # Scala sprite se necessario
            if self.sprite_scale != 1.0:
                w, h = sprite_data['size']
                new_size = (int(w * self.sprite_scale), int(h * self.sprite_scale))
                scaled_sprite = pygame.transform.scale(sprite_data['original'], new_size)
            else:
                scaled_sprite = sprite_data['image']
            
            # Disegna sprite
            self.canvas.blit(scaled_sprite, self.sprite_pos)
            
            # Bordo attorno allo sprite per visibilità
            rect = pygame.Rect(
                self.sprite_pos[0] - 1,
                self.sprite_pos[1] - 1,
                scaled_sprite.get_width() + 2,
                scaled_sprite.get_height() + 2
            )
            pygame.draw.rect(self.canvas, (255, 255, 0), rect, 1)
        
        # UI Overlay
        self.draw_info(self.canvas)
        self.draw_fps(self.canvas)
        self.draw_help(self.canvas)
        
        # Scala canvas → window
        scaled_surface = pygame.transform.scale(self.canvas, self.WINDOW_RES)
        self.screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
    
    def run(self):
        """Main loop"""
        if not self.sprites:
            print("❌ Nessuno sprite caricato. Caricando sprite di esempio...")
            # Crea uno sprite di test se non ce ne sono
            self.create_test_sprite()
        
        # Centra il primo sprite
        self.center_sprite()
        
        print("\n🎮 Sprite Viewer avviato!")
        print("Premi H per vedere i controlli\n")
        
        running = True
        while running:
            running = self.handle_input()
            self.render()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()
        print("👋 Sprite Viewer chiuso")
    
    def create_test_sprite(self):
        """Crea uno sprite di test se non ci sono file"""
        # Crea un piccolo sprite colorato
        test_sprite = pygame.Surface((32, 32), pygame.SRCALPHA)
        
        # Pattern a scacchiera
        for x in range(32):
            for y in range(32):
                if (x // 4 + y // 4) % 2 == 0:
                    color = (255, 100, 100)
                else:
                    color = (100, 100, 255)
                test_sprite.set_at((x, y), color)
        
        # Aggiungi bordo giallo
        pygame.draw.rect(test_sprite, (255, 255, 0), test_sprite.get_rect(), 2)
        
        self.sprites.append({
            'image': test_sprite,
            'filepath': 'test_sprite',
            'filename': 'TEST SPRITE',
            'size': (32, 32),
            'original': test_sprite.copy()
        })
        print("✓ Sprite di test creato")


def main():
    """Entry point"""
    print("=" * 60)
    print("🎨 Pixel Art Sprite Viewer - Versione Migliorata")
    print("=" * 60)
    
    viewer = SpriteViewer()
    
    # Prova a caricare sprite dalla directory corrente
    viewer.load_sprites_from_directory(".")
    
    # Prova anche le directory degli sprite generati
    if os.path.exists("/mnt/user-data/outputs/rpg_sprites"):
        viewer.load_sprites_from_directory("/mnt/user-data/outputs/rpg_sprites")
    
    if os.path.exists("/mnt/user-data/outputs/yume_nikki_sprites"):
        viewer.load_sprites_from_directory("/mnt/user-data/outputs/yume_nikki_sprites")
    
    if os.path.exists("/mnt/user-data/outputs/random_characters"):
        viewer.load_sprites_from_directory("/mnt/user-data/outputs/random_characters")
    
    if os.path.exists("/mnt/user-data/outputs/ophanim"):
        viewer.load_sprites_from_directory("/mnt/user-data/outputs/ophanim")
    
    # Avvia viewer
    viewer.run()


if __name__ == "__main__":
    main()
