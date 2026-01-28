
import pygame
import os

__all__ = ["FontManager", "clip", "Font"]

class FontManager:
    """
    Load two font files, normal and bold, and enables
    fm.draw_text()
    """
    def __init__(self, assets_dir="assets"):
        self.assets_dir = assets_dir
        self.font_dir = os.path.join(self.assets_dir, "fonts")
        
        self.pixel_op_font = self.load_font("PixelOperator8", 14)
        self.pixel_op_bold_font = self.load_font("PixelOperator8-Bold", 18)

    def load_font(self, font_name, size):
        font_path = os.path.join(self.font_dir, f"{font_name}.ttf")
        if os.path.exists(font_path):
            return pygame.font.Font(font_path, size)
        else:
            print(f"[FontManager] Warning: Font {font_name} not found in {self.font_dir}. Falling back to default.")
            return pygame.font.SysFont("Arial", size)


    def draw_text(self, surface, text, color, x, y, alpha=255, bold=False) -> pygame.Rect:
        if bold:
            text_surface = self.pixel_op_bold_font.render(text, True, color)
        else:
            text_surface = self.pixel_op_font.render(text, True, color)
        text_surface.set_colorkey((0, 0, 0))
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

        return text_rect

def clip(surf, x, y, x_size, y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x, y, x_size, y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()

class Font():
    """
    Loads an image with a font from a path
    and enables font.render()
    """
    def __init__(self, path) -> None:
        self.spacing = 1 #pixels between characters in the image
        if os.path.exists(path):
            font_img = pygame.image.load(path).convert()
        else:
            print(f"[Font] Warning: Font image {path} not found. Creating dummy.")
            font_img = pygame.Surface((1, 1))
            font_img.fill((127, 0, 0)) # Grey bar to avoid crash in loop
        current_char_width = 0
        self.characters = {}
        character_count = 0
        self.character_order = ['A','B','C','D','E','F','G','H','I','J','K','L',
                                'M','N','O','P','Q','R','S','T','U','V','W','X',
                                'Y','Z',
                                'a','b','c','d','e','f','g','h','i','j','k','l',
                                'm','n','o','p','q','r','s','t','u','v','w','x',
                                'y', 'z',
                                '.','-',',',':','+','\'','!','?',
                                '0','1','2','3','4','5','6','7','8','9',
                                '(',')','/','_','=','\\','[',']','*','"','<','>',';'
                                ]
        for x in range(font_img.get_width()):
            c = font_img.get_at((x, 0))
            if c[0] == 127: # check the red value of the grey bar
                # when the end of char is found cut it out
                char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
                char_img.set_colorkey((0, 0, 0))    # added transparency on black
                self.characters[self.character_order[character_count]] = char_img.copy()
                current_char_width = 0
                character_count += 1
            else:
                current_char_width += 1

        self.space_width = self.characters['A'].get_width()

        self.cached = {}

    def render(self,surf, text, loc, new_c=None, scale=1):
        x_offset = 0
        for char in text:
            if char != ' ':

                key = str(new_c)+char
                selected_char = self.characters[char]
                if new_c:
                    selected_char = self.cached.get(key, None)
                    if selected_char is None:
                        selected_char = self.palette_swap(self.characters[char], (255, 0, 0), new_c)
                        selected_char.set_colorkey((0, 0, 0))
                        self.cached[key] = selected_char

                if scale != 1:
                    selected_char = pygame.transform.scale(
                        selected_char, 
                        (selected_char.get_rect().width*scale, selected_char.get_rect().height*scale))

                surf.blit(selected_char, (loc[0] + x_offset, loc[1]))
                x_offset += selected_char.get_width() + self.spacing
            else:
                x_offset += self.spacing + self.space_width

    def palette_swap(self, surf, old_c, new_c):
        img_copy = pygame.Surface(surf.get_size())
        img_copy.fill(new_c)
        surf.set_colorkey(old_c)
        img_copy.blit(surf, (0, 0))
        return img_copy

"""Uso:
my_font = Font("small_font.png")

while True:
    my_font.render(screen, "Hello World", (20, 20))
"""