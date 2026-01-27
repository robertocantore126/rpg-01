"""
Gestione grafica e risorse - SpriteManager
Carica e memorizza sprite in un dizionario { "player": Surface, "enemy": Surface, … }
"""
import os
import pygame

__all__ = ["SpriteManager", "palette_swap"]

class SpriteManager:
    def __init__(self, base_dir="assets/sprites", scale=1):
        """
        SpriteManager centralizza il caricamento e caching delle immagini.
        
        :param base_dir: cartella base in cui cercare gli sprite.
        :param scale: fattore di scala (1 = dimensioni originali).
        """
        self.base_dir = base_dir
        self.scale = scale
        self.cache: dict[str, pygame.Surface | list[pygame.Surface]] = {}  # { "key_name": pygame.Surface }

        self.assets_dir = os.path.join("assets")
        self.sprite_dir = os.path.join(self.assets_dir, "sprites")
    
    # ----------------------------
    # Metodo base per caricare un'immagine
    # ----------------------------
    def load(self, name: str, path: str) -> pygame.Surface:
        """
        Carica un'immagine da path e la salva in cache con la chiave 'name'.
        Se già presente in cache, restituisce quella.
        """
        if name not in self.cache:
            full_path = os.path.join(self.base_dir, path)
            image = pygame.image.load(full_path).convert_alpha()
            image.set_colorkey((0, 0, 0))  # trasparente

            # Applica scaling se richiesto
            if self.scale != 1:
                w, h = image.get_size()
                image = pygame.transform.scale(image, (int(w * self.scale), int(h * self.scale)))

            self.cache[name] = image
        return self.cache[name] # type: ignore

    def get(self, name: str) -> pygame.Surface | None | list[pygame.Surface]:
        """ Restituisce l'immagine dalla cache. """
        return self.cache.get(name, None) # type: ignore

    # ----------------------------
    # Caricamento di una cartella intera
    # ----------------------------
    def load_folder(self, folder_name: str, prefix: str = ""):
        """
        Carica tutte le immagini da una cartella (es. 'player', 'enemies').
        Ogni file diventa accessibile come prefix+nomefile.
        """
        folder_path = os.path.join(self.base_dir, folder_name)
        for filename in os.listdir(folder_path):
            if filename.endswith(".png"):
                key = prefix + os.path.splitext(filename)[0]
                self.load(key, os.path.join(folder_name, filename))

    # ----------------------------
    # Gestione sprite sheet (per animazioni)
    # ----------------------------
    def load_spritesheet(self, name: str, path: str, frame_width: int, frame_height: int) -> list[pygame.Surface]:
        """
        Carica uno spritesheet e lo divide in frame.
        Ritorna una lista di Surface.
        """
        sheet = self.load(f"{name}_sheet", path)  # cache con chiave unica
        sheet_width, sheet_height = sheet.get_size()

        frames: list[pygame.Surface] = []
        for y in range(0, sheet_height, frame_height):
            for x in range(0, sheet_width, frame_width):
                frame = sheet.subsurface(pygame.Rect(x, y, frame_width, frame_height)).copy()

                if self.scale != 1:
                    frame = pygame.transform.scale(
                        frame,
                        (int(frame_width * self.scale), int(frame_height * self.scale))
                    )
                frames.append(frame)

        self.cache[name] = frames  # type: ignore # salva la lista di frame
        return frames

    def get_animation(self, name):
        """
        Restituisce una lista di frame da cache (se caricata con load_spritesheet).
        """
        return self.cache.get(name, [])

    def load_spritesheet_slice(
            self, name: str, path: str,
            frame_width: int, frame_height: int,
            start_x: int, start_y: int, count: int
            ) -> list[pygame.Surface]:
        """
        Carica una porzione di uno spritesheet a partire da start_x, start_y.
        Ritorna una lista di Surface.
        """
        sheet = self.load(name, path)
        sheet_width, sheet_height = sheet.get_size()
        frames: list[pygame.Surface] = []

        # Assume a 2D grid, grab the next on the same row until count is reached
        # If count is not reached and we reach the end of the row, continue on the next row
        for i in range(count):
            # find top-left corner of the frame
            x = start_x * frame_width + i * frame_width
            y = start_y * frame_height
            # print(f"Loading frame {i}: ({x}, {y})")
            
            if x >= sheet_width or y >= sheet_height:
                print(f"Warning: Frame {i} out of bounds ({x}, {y}) in sheet size ({sheet_width}, {sheet_height})")
                break
            frame = sheet.subsurface(pygame.Rect(x, y, frame_width, frame_height)).copy()
            if self.scale != 1:
                frame = pygame.transform.scale(
                    frame,
                    (int(frame_width * self.scale), int(frame_height * self.scale))
                )
            frames.append(frame)
        self.cache[name] = frames # type: ignore # salva la lista di frame
        assert len(frames) == count, f"Expected {count} frames, got {len(frames)}"
        return frames

    # masks: https://www.youtube.com/watch?v=7qcnB5fYsIs&list=PLX5fBCkxJmm3s5GL0Cebm59m1GkAhCFoM
    # method 1
    @staticmethod
    def outline_mask(img, loc):
        mask = pygame.mask.from_surface(img)
        mask_outline = mask.outline()
        n = 0
        for point in mask_outline:
            mask_outline[n] = (point[0] + loc[0], point[1] + loc[1])
            n += 1
        # pygame.draw.polygon(screen, (255,0,0), mask_outline, 3)
        return mask_outline

    # method 2
    @staticmethod
    def perfect_outline(screen, img, loc):
        mask = pygame.mask.from_surface(img)
        mask_surf = mask.to_surface()
        mask_surf.set_colorkey((0, 0, 0))
        # mask_surf.set_alpha(100)
        screen.blit(mask_surf, (loc[0]-1, loc[1]))
        screen.blit(mask_surf, (loc[0]+1, loc[1]))
        screen.blit(mask_surf, (loc[0], loc[1]-1))
        screen.blit(mask_surf, (loc[0], loc[1]+1))
        return mask_surf

    # method 3
    @staticmethod
    def perfect_outline2(screen, img, loc):
        mask = pygame.mask.from_surface(img)
        mask_outline = mask.outline()
        mask_surf = pygame.Surface((img.get_size()))
        for pixel in mask_outline:
            mask_surf.set_at(pixel, (255, 255, 255))
        mask_surf.set_colorkey((0, 0, 0))
        # mask_surf.set_alpha(100)
        screen.blit(mask_surf, (loc[0]-1, loc[1]))
        screen.blit(mask_surf, (loc[0]+1, loc[1]))
        screen.blit(mask_surf, (loc[0], loc[1]-1))
        screen.blit(mask_surf, (loc[0], loc[1]+1))
        return mask_surf


@staticmethod
def palette_swap(surf, old_c, new_c):
    img_copy = pygame.Surface(surf.get_size())
    img_copy.fill(new_c)
    surf.set_colorkey(old_c)
    img_copy.blit(surf, (0, 0))
    return img_copy
    