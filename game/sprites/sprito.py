"""
Advanced Glitch Creature Generator - Professional Edition
==========================================================

Un generatore procedurale di sprite per creature con effetti glitch artistici.
Supporta creature complesse con anatomia dettagliata, classi, razze e accessori.

Autore: Advanced Glitch System
Versione: 2.0
"""

import random
import os
import json
import math
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from PIL import Image, ImageDraw, ImageChops, ImageEnhance, ImageFilter
from abc import ABC, abstractmethod


# ============================================================================
# CONFIGURAZIONI E COSTANTI
# ============================================================================

class CreatureType(Enum):
    """Tipi di creature disponibili"""
    HUMANOID = "humanoid"
    ORGANIC_MONSTER = "organic_monster"
    MECHANICAL_MONSTER = "mechanical_monster"
    ELDRITCH_MONSTER = "eldritch_monster"


class Race(Enum):
    """Razze disponibili per umanoidi"""
    HUMAN = "human"
    ALIEN = "alien"
    UNDEAD = "undead"
    DEMON = "demon"
    ROBOT = "robot"


class CharacterClass(Enum):
    """Classi per personaggi umanoidi"""
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    PRIEST = "priest"


class GlitchIntensity(Enum):
    """Livelli di intensità glitch"""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    EXTREME = "extreme"


@dataclass
class ColorPalette:
    """Palette di colori per creature"""
    primary: Tuple[int, int, int]
    secondary: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    outline: Tuple[int, int, int] = (0, 0, 0)
    
    def darken(self, color: Tuple[int, int, int], factor: float = 0.6) -> Tuple[int, int, int]:
        """Scurisce un colore"""
        return tuple(int(c * factor) for c in color)
    
    def lighten(self, color: Tuple[int, int, int], factor: float = 1.4) -> Tuple[int, int, int]:
        """Schiarisce un colore"""
        return tuple(min(255, int(c * factor)) for c in color)


@dataclass
class CreatureMetadata:
    """Metadati della creatura generata"""
    creature_type: str
    race: Optional[str] = None
    character_class: Optional[str] = None
    features: List[str] = None
    glitch_effects: List[str] = None
    stats: Optional[Dict[str, int]] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = []
        if self.glitch_effects is None:
            self.glitch_effects = []


class Config:
    """Configurazione globale"""
    DEFAULT_WIDTH = 48
    DEFAULT_HEIGHT = 64
    DEFAULT_SCALE = 8
    OUTPUT_DIR = "output_glitch_pro"
    SPRITE_SHEET_COLUMNS = 5
    
    # Palette predefinite
    SKIN_PALETTES = {
        Race.HUMAN: [(255, 220, 200), (220, 180, 140), (150, 100, 80), (80, 50, 30)],
        Race.ALIEN: [(100, 255, 150), (150, 100, 255), (255, 150, 100), (100, 200, 255)],
        Race.UNDEAD: [(180, 180, 150), (120, 120, 100), (80, 100, 80), (60, 80, 60)],
        Race.DEMON: [(200, 50, 50), (150, 0, 100), (100, 0, 150), (80, 20, 20)],
        Race.ROBOT: [(180, 180, 200), (150, 150, 170), (100, 100, 120), (200, 200, 220)]
    }
    
    CLOTH_PALETTES = {
        CharacterClass.WARRIOR: [(150, 50, 50), (100, 50, 150), (50, 100, 150)],
        CharacterClass.MAGE: [(50, 50, 200), (150, 50, 200), (200, 100, 50)],
        CharacterClass.ROGUE: [(40, 40, 40), (60, 40, 20), (20, 60, 40)],
        CharacterClass.PRIEST: [(255, 255, 255), (200, 200, 150), (150, 150, 200)]
    }


# ============================================================================
# SISTEMA GLITCH AVANZATO
# ============================================================================

class GlitchEffect(ABC):
    """Classe base astratta per effetti glitch"""
    
    @abstractmethod
    def apply(self, img: Image.Image) -> Image.Image:
        """Applica l'effetto glitch all'immagine"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome dell'effetto"""
        pass


class RGBSplitEffect(GlitchEffect):
    """Effetto separazione RGB con aberrazione cromatica"""
    
    def __init__(self, offset: Optional[int] = None):
        self.offset = offset or random.randint(2, 5)
    
    def apply(self, img: Image.Image) -> Image.Image:
        if img.mode != 'RGBA':
            return img
        
        r, g, b, a = img.split()
        r = ImageChops.offset(r, -self.offset, random.randint(-1, 1))
        b = ImageChops.offset(b, self.offset, random.randint(-1, 1))
        g = ImageChops.offset(g, 0, random.randint(-self.offset//2, self.offset//2))
        
        return Image.merge("RGBA", (r, g, b, a))
    
    @property
    def name(self) -> str:
        return "rgb_split"


class HorizontalSliceEffect(GlitchEffect):
    """Effetto slice orizzontali con dislocazione"""
    
    def __init__(self, severity: Optional[int] = None):
        self.severity = severity or random.randint(3, 8)
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        source_pixels = img.load()
        
        num_slices = random.randint(5, 12)
        
        for _ in range(num_slices):
            y_start = random.randint(0, h - 1)
            height = random.randint(1, 6)
            shift = random.randint(-self.severity * 2, self.severity * 2)
            
            for y in range(y_start, min(y_start + height, h)):
                for x in range(w):
                    new_x = (x + shift) % w
                    pixels[new_x, y] = source_pixels[x, y]
        
        return output
    
    @property
    def name(self) -> str:
        return "horizontal_slice"


class PixelCorruptionEffect(GlitchEffect):
    """Effetto corruzione pixel con cluster"""
    
    def __init__(self, density: Optional[float] = None):
        self.density = density or random.uniform(0.02, 0.08)
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        
        num_clusters = random.randint(2, 6)
        
        for _ in range(num_clusters):
            cx = random.randint(0, w-1)
            cy = random.randint(0, h-1)
            radius = random.randint(2, 8)
            
            for y in range(max(0, cy-radius), min(h, cy+radius)):
                for x in range(max(0, cx-radius), min(w, cx+radius)):
                    if pixels[x, y][3] > 0 and random.random() < self.density * 3:
                        mode = random.choices(
                            ['static', 'acid', 'void', 'invert', 'bright'],
                            weights=[0.3, 0.25, 0.15, 0.2, 0.1]
                        )[0]
                        
                        pixels[x, y] = self._get_corruption_color(pixels[x, y], mode)
        
        return output
    
    def _get_corruption_color(self, original: Tuple[int, int, int, int], mode: str) -> Tuple[int, int, int, int]:
        """Genera colore corrotto basato sulla modalità"""
        if mode == 'static':
            val = random.randint(180, 255)
            return (val, val, val, 255)
        elif mode == 'acid':
            return (random.randint(0, 255), random.randint(0, 100), random.randint(150, 255), 255)
        elif mode == 'void':
            return (0, 0, 0, 255)
        elif mode == 'invert':
            r, g, b, a = original
            return (255-r, 255-g, 255-b, a)
        else:  # bright
            return (255, 255, 255, 255)
    
    @property
    def name(self) -> str:
        return "pixel_corruption"


class MeltGhostingEffect(GlitchEffect):
    """Effetto scioglimento/ghosting"""
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        
        direction = random.choice(['down', 'up'])
        
        for x in range(w):
            if random.random() < 0.35:
                melt_len = random.randint(3, 15)
                
                if direction == 'down':
                    for y in range(h - 1, 0, -1):
                        if pixels[x, y][3] > 0:
                            color = pixels[x, y]
                            for k in range(1, melt_len):
                                if y + k < h:
                                    alpha = int(255 * (1 - k/melt_len))
                                    pixels[x, y + k] = (*color[:3], alpha)
        
        return output
    
    @property
    def name(self) -> str:
        return "melt_ghosting"


class ChromaticAberrationEffect(GlitchEffect):
    """Aberrazione cromatica avanzata"""
    
    def __init__(self, strength: Optional[int] = None):
        self.strength = strength or random.randint(1, 4)
    
    def apply(self, img: Image.Image) -> Image.Image:
        if img.mode != 'RGBA':
            return img
        
        r, g, b, a = img.split()
        
        r = r.transform(r.size, Image.AFFINE, 
                       (1 + self.strength*0.01, 0, -self.strength, 0, 1, 0))
        b = b.transform(b.size, Image.AFFINE, 
                       (1 - self.strength*0.01, 0, self.strength, 0, 1, 0))
        
        return Image.merge("RGBA", (r, g, b, a))
    
    @property
    def name(self) -> str:
        return "chromatic_aberration"


class DatabendEffect(GlitchEffect):
    """Simulazione databending"""
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        
        rows_to_repeat = random.sample(range(h), k=min(random.randint(2, 5), h))
        
        for row in rows_to_repeat:
            repeat_count = random.randint(1, 4)
            for offset in range(1, repeat_count + 1):
                if row + offset < h:
                    for x in range(w):
                        pixels[x, row + offset] = pixels[x, row]
        
        return output
    
    @property
    def name(self) -> str:
        return "databend"


class ScanLinesEffect(GlitchEffect):
    """Linee di scansione CRT"""
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        
        for y in range(0, h, 2):
            for x in range(w):
                if pixels[x, y][3] > 0:
                    r, g, b, a = pixels[x, y]
                    pixels[x, y] = (int(r*0.7), int(g*0.7), int(b*0.7), a)
        
        return output
    
    @property
    def name(self) -> str:
        return "scan_lines"


class ColorBleedEffect(GlitchEffect):
    """Effetto sanguinamento colori"""
    
    def apply(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        output = img.copy()
        pixels = output.load()
        source_pixels = img.load()
        
        for y in range(h):
            for x in range(1, w-1):
                if random.random() < 0.1 and source_pixels[x, y][3] > 0:
                    prev_color = source_pixels[x-1, y]
                    curr_color = source_pixels[x, y]
                    blended = tuple(int((p + c) / 2) for p, c in zip(prev_color[:3], curr_color[:3]))
                    pixels[x, y] = (*blended, curr_color[3])
        
        return output
    
    @property
    def name(self) -> str:
        return "color_bleed"


class GlitchEngine:
    """Engine per applicare effetti glitch"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.effects: List[GlitchEffect] = [
            RGBSplitEffect(),
            HorizontalSliceEffect(),
            PixelCorruptionEffect(),
            MeltGhostingEffect(),
            ChromaticAberrationEffect(),
            DatabendEffect(),
            ScanLinesEffect(),
            ColorBleedEffect()
        ]
    
    def apply_glitch(self, img: Image.Image, 
                    intensity: GlitchIntensity = GlitchIntensity.MEDIUM) -> Tuple[Image.Image, List[str]]:
        """Applica effetti glitch con intensità specificata"""
        
        intensity_config = {
            GlitchIntensity.LIGHT: {'num_effects': (1, 2), 'probability': 0.4},
            GlitchIntensity.MEDIUM: {'num_effects': (2, 4), 'probability': 0.6},
            GlitchIntensity.HEAVY: {'num_effects': (3, 6), 'probability': 0.8},
            GlitchIntensity.EXTREME: {'num_effects': (4, 7), 'probability': 1.0}
        }
        
        config = intensity_config[intensity]
        num_effects = random.randint(*config['num_effects'])
        
        selected_effects = random.sample(self.effects, k=min(num_effects, len(self.effects)))
        
        glitched = img.copy()
        applied_effects = []
        
        for effect in selected_effects:
            if random.random() < config['probability']:
                try:
                    glitched = effect.apply(glitched)
                    applied_effects.append(effect.name)
                except Exception as e:
                    print(f"⚠️  Errore applicando {effect.name}: {e}")
        
        return glitched, applied_effects


# ============================================================================
# SISTEMA DI RENDERING CREATURE
# ============================================================================

class CreatureRenderer(ABC):
    """Classe base astratta per renderer di creature"""
    
    def __init__(self, width: int = Config.DEFAULT_WIDTH, 
                 height: int = Config.DEFAULT_HEIGHT):
        self.width = width
        self.height = height
        self.metadata = CreatureMetadata(creature_type="unknown")
    
    @abstractmethod
    def render(self) -> Image.Image:
        """Renderizza la creatura"""
        pass
    
    def get_metadata(self) -> CreatureMetadata:
        """Restituisce i metadati della creatura"""
        return self.metadata


class BodyPartRenderer:
    """Renderer per parti del corpo condivise"""
    
    @staticmethod
    def draw_gradient_ellipse(draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int],
                             color1: Tuple[int, int, int], 
                             color2: Tuple[int, int, int]):
        """Disegna ellisse con gradiente"""
        x1, y1, x2, y2 = bbox
        for i in range(y2 - y1):
            ratio = i / (y2 - y1) if (y2 - y1) > 0 else 0
            color = tuple(int(c1 + (c2 - c1) * ratio) for c1, c2 in zip(color1, color2))
            draw.ellipse([x1, y1 + i, x2, y1 + i + 1], fill=color)
    
    @staticmethod
    def draw_eyes(draw: ImageDraw.Draw, head_bbox: Tuple[int, int, int, int], 
                  eye_type: str = 'normal') -> None:
        """Disegna occhi con diversi stili"""
        x1, y1, x2, y2 = head_bbox
        center_y = (y1 + y2) // 2
        
        eye_configs = {
            'normal': {
                'positions': [(x1 + 4, center_y - 1, x1 + 7, center_y + 2),
                            (x2 - 7, center_y - 1, x2 - 4, center_y + 2)],
                'color': (255, 255, 255),
                'pupil_color': (0, 0, 0),
                'pupil_size': 1
            },
            'alien': {
                'positions': [(x1 + 3, center_y - 2, x1 + 8, center_y + 3),
                            (x2 - 8, center_y - 2, x2 - 3, center_y + 3)],
                'color': (0, 255, 0),
                'pupil_color': (0, 0, 0),
                'pupil_size': 2
            },
            'demon': {
                'positions': [(x1 + 4, center_y - 1, x1 + 7, center_y + 2),
                            (x2 - 7, center_y - 1, x2 - 4, center_y + 2)],
                'color': (255, 0, 0),
                'pupil_color': (100, 0, 0),
                'pupil_size': 1
            },
            'robot': {
                'positions': [(x1 + 4, center_y, x1 + 6, center_y + 2),
                            (x2 - 6, center_y, x2 - 4, center_y + 2)],
                'color': (0, 255, 255),
                'pupil_color': (0, 200, 200),
                'pupil_size': 0
            },
            'cyclops': {
                'positions': [((x1 + x2) // 2 - 3, center_y - 2, 
                             (x1 + x2) // 2 + 3, center_y + 3)],
                'color': (255, 200, 0),
                'pupil_color': (0, 0, 0),
                'pupil_size': 2
            }
        }
        
        config = eye_configs.get(eye_type, eye_configs['normal'])
        
        for eye_pos in config['positions']:
            draw.ellipse(eye_pos, fill=config['color'], outline=(0, 0, 0))
            
            if config['pupil_size'] > 0:
                cx = (eye_pos[0] + eye_pos[2]) // 2
                cy = (eye_pos[1] + eye_pos[3]) // 2
                ps = config['pupil_size']
                draw.ellipse([cx-ps, cy-ps, cx+ps, cy+ps], fill=config['pupil_color'])
    
    @staticmethod
    def draw_hair(draw: ImageDraw.Draw, head_bbox: Tuple[int, int, int, int], 
                  style: str = 'short') -> None:
        """Disegna capelli/cresta/corna"""
        x1, y1, x2, y2 = head_bbox
        
        hair_colors = [(0, 0, 0), (100, 50, 0), (200, 150, 50), (150, 0, 0), (255, 255, 255)]
        color = random.choice(hair_colors)
        
        if style == 'short':
            draw.rectangle([x1 + 2, y1, x2 - 2, y1 + 4], fill=color)
        
        elif style == 'long':
            draw.rectangle([x1 + 1, y1, x2 - 1, y1 + 8], fill=color)
            draw.rectangle([x1 - 1, y1 + 4, x1 + 2, y2 + 2], fill=color)
            draw.rectangle([x2 - 2, y1 + 4, x2 + 1, y2 + 2], fill=color)
        
        elif style == 'spiky':
            for i in range(3):
                x = x1 + 3 + i * 4
                draw.polygon([(x, y1), (x + 1, y1 - 3), (x + 2, y1)], fill=color)
        
        elif style == 'mohawk':
            cx = (x1 + x2) // 2
            for i in range(6):
                y = y1 - i
                draw.rectangle([cx - 1, y, cx + 1, y + 1], fill=color)
        
        elif style == 'horns':
            horn_color = (150, 0, 0)
            draw.polygon([(x1 + 2, y1 + 2), (x1, y1 - 4), (x1 + 3, y1)], 
                        fill=horn_color, outline=(100, 0, 0))
            draw.polygon([(x2 - 2, y1 + 2), (x2, y1 - 4), (x2 - 3, y1)], 
                        fill=horn_color, outline=(100, 0, 0))
        
        elif style == 'antenna':
            cx = (x1 + x2) // 2
            draw.line([(cx - 2, y1), (cx - 3, y1 - 5)], fill=color, width=1)
            draw.line([(cx + 2, y1), (cx + 3, y1 - 5)], fill=color, width=1)
            draw.ellipse([cx - 4, y1 - 7, cx - 2, y1 - 5], fill=(255, 200, 0))
            draw.ellipse([cx + 2, y1 - 7, cx + 4, y1 - 5], fill=(255, 200, 0))


class HumanoidRenderer(CreatureRenderer):
    """Renderer per creature umanoidi"""
    
    def __init__(self, race: Race = Race.HUMAN, 
                 char_class: CharacterClass = CharacterClass.WARRIOR,
                 width: int = Config.DEFAULT_WIDTH,
                 height: int = Config.DEFAULT_HEIGHT):
        super().__init__(width, height)
        self.race = race
        self.char_class = char_class
        self.metadata = CreatureMetadata(
            creature_type=CreatureType.HUMANOID.value,
            race=race.value,
            character_class=char_class.value,
            stats=self._generate_stats()
        )
    
    def _generate_stats(self) -> Dict[str, int]:
        """Genera statistiche basate su classe e razza"""
        base_stats = {
            'strength': random.randint(5, 15),
            'intelligence': random.randint(5, 15),
            'agility': random.randint(5, 15),
            'vitality': random.randint(5, 15)
        }
        
        # Bonus per classe
        class_bonuses = {
            CharacterClass.WARRIOR: {'strength': 5, 'vitality': 3},
            CharacterClass.MAGE: {'intelligence': 5, 'agility': 2},
            CharacterClass.ROGUE: {'agility': 5, 'strength': 2},
            CharacterClass.PRIEST: {'intelligence': 3, 'vitality': 4}
        }
        
        bonuses = class_bonuses.get(self.char_class, {})
        for stat, bonus in bonuses.items():
            base_stats[stat] += bonus
        
        return base_stats
    
    def render(self) -> Image.Image:
        """Renderizza umanoide completo"""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Colori basati su razza e classe
        skin = random.choice(Config.SKIN_PALETTES[self.race])
        cloth = random.choice(Config.CLOTH_PALETTES[self.char_class])
        
        # Proporzioni
        head_y, head_h = 8, 14
        body_y, body_h = head_y + head_h, 18
        leg_y, leg_h = body_y + body_h, 14
        
        # Testa
        head_bbox = (12, head_y, 36, head_y + head_h)
        draw.ellipse(head_bbox, fill=skin, outline=(0, 0, 0))
        
        # Occhi
        eye_type = self._get_eye_type()
        BodyPartRenderer.draw_eyes(draw, head_bbox, eye_type)
        self.metadata.features.append(f"eyes_{eye_type}")
        
        # Capelli
        hair_style = self._get_hair_style()
        BodyPartRenderer.draw_hair(draw, head_bbox, hair_style)
        self.metadata.features.append(f"hair_{hair_style}")
        
        # Corpo
        body_bbox = (14, body_y, 34, body_y + body_h)
        draw.rectangle(body_bbox, fill=cloth, outline=(0, 0, 0))
        
        # Cintura
        belt_y = body_y + body_h - 4
        draw.rectangle([14, belt_y, 34, belt_y + 2], fill=(80, 50, 20))
        
        # Braccia
        arm_color = skin if random.random() > 0.5 else cloth
        draw.rectangle([10, body_y + 4, 14, body_y + 14], fill=arm_color, outline=(0, 0, 0))
        draw.rectangle([34, body_y + 4, 38, body_y + 14], fill=arm_color, outline=(0, 0, 0))
        
        # Mani
        draw.rectangle([8, body_y + 12, 12, body_y + 16], fill=skin)
        draw.rectangle([36, body_y + 12, 40, body_y + 16], fill=skin)
        
        # Gambe
        leg_color = random.choice([(50, 50, 100), (80, 50, 20), (100, 100, 100)])
        draw.rectangle([18, leg_y, 22, leg_y + leg_h], fill=leg_color, outline=(0, 0, 0))
        draw.rectangle([26, leg_y, 30, leg_y + leg_h], fill=leg_color, outline=(0, 0, 0))
        
        # Scarpe
        boot_color = (40, 20, 10)
        draw.rectangle([16, leg_y + leg_h - 3, 24, leg_y + leg_h], fill=boot_color)
        draw.rectangle([24, leg_y + leg_h - 3, 32, leg_y + leg_h], fill=boot_color)
        
        # Accessori
        self._add_class_accessories(draw, body_bbox)
        
        # Caratteristiche razziali
        self._add_racial_features(draw, body_bbox)
        
        return img
    
    def _get_eye_type(self) -> str:
        """Determina tipo di occhi basato sulla razza"""
        eye_map = {
            Race.HUMAN: 'normal',
            Race.ALIEN: random.choice(['alien', 'cyclops']),
            Race.UNDEAD: 'normal',
            Race.DEMON: 'demon',
            Race.ROBOT: 'robot'
        }
        return eye_map.get(self.race, 'normal')
    
    def _get_hair_style(self) -> str:
        """Determina stile capelli basato sulla razza"""
        if self.race == Race.DEMON:
            return random.choice(['horns', 'spiky', 'mohawk'])
        elif self.race == Race.ALIEN:
            return random.choice(['antenna', 'short', 'mohawk'])
        elif self.race == Race.ROBOT:
            return random.choice(['antenna', 'short'])
        else:
            return random.choice(['short', 'long', 'spiky', 'mohawk'])
    
    def _add_class_accessories(self, draw: ImageDraw.Draw, 
                              body_bbox: Tuple[int, int, int, int]) -> None:
        """Aggiunge accessori basati sulla classe"""
        x1, y1, x2, y2 = body_bbox
        
        accessories = {
            CharacterClass.WARRIOR: self._draw_warrior_gear,
            CharacterClass.MAGE: self._draw_mage_gear,
            CharacterClass.ROGUE: self._draw_rogue_gear,
            CharacterClass.PRIEST: self._draw_priest_gear
        }
        
        accessor_func = accessories.get(self.char_class)
        if accessor_func:
            accessor_func(draw, body_bbox)
    
    def _draw_warrior_gear(self, draw: ImageDraw.Draw, 
                          body_bbox: Tuple[int, int, int, int]) -> None:
        """Equipaggiamento guerriero"""
        x1, y1, x2, y2 = body_bbox
        
        # Spada
        sword_x = x2 + 1
        draw.line([(sword_x, y1 + 2), (sword_x, y2 - 2)], fill=(180, 180, 200), width=2)
        draw.rectangle([sword_x - 2, y1 - 2, sword_x + 2, y1], fill=(150, 100, 0))
        
        # Armatura
        draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y1 + 4], fill=(180, 180, 180))
        self.metadata.features.append("sword")
        self.metadata.features.append("armor")
    
    def _draw_mage_gear(self, draw: ImageDraw.Draw, 
                       body_bbox: Tuple[int, int, int, int]) -> None:
        """Equipaggiamento mago"""
        x1, y1, x2, y2 = body_bbox
        
        # Bastone
        staff_x = x2 + 2
        draw.line([(staff_x, y1), (staff_x, y2 + 8)], fill=(100, 50, 0), width=2)
        draw.ellipse([staff_x - 2, y1 - 3, staff_x + 2, y1 + 1], fill=(100, 50, 255))
        
        # Mantello
        draw.polygon([
            (x1, y1 + 2), (x1 - 3, y2), (x1, y2 + 4),
            (x2, y2 + 4), (x2 + 3, y2), (x2, y1 + 2)
        ], fill=(50, 0, 100), outline=(30, 0, 60))
        
        self.metadata.features.append("staff")
        self.metadata.features.append("cape")
    
    def _draw_rogue_gear(self, draw: ImageDraw.Draw, 
                        body_bbox: Tuple[int, int, int, int]) -> None:
        """Equipaggiamento ladro"""
        x1, y1, x2, y2 = body_bbox
        
        # Mantello scuro
        draw.polygon([
            (x1, y1 + 2), (x1 - 2, y2 - 2), (x1, y2),
            (x2, y2), (x2 + 2, y2 - 2), (x2, y1 + 2)
        ], fill=(20, 20, 20), outline=(10, 10, 10))
        
        self.metadata.features.append("dark_cape")
    
    def _draw_priest_gear(self, draw: ImageDraw.Draw, 
                         body_bbox: Tuple[int, int, int, int]) -> None:
        """Equipaggiamento sacerdote"""
        x1, y1, x2, y2 = body_bbox
        
        # Simbolo sacro
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        draw.line([(cx, cy - 3), (cx, cy + 3)], fill=(255, 215, 0), width=2)
        draw.line([(cx - 2, cy), (cx + 2, cy)], fill=(255, 215, 0), width=2)
        
        self.metadata.features.append("holy_symbol")
    
    def _add_racial_features(self, draw: ImageDraw.Draw, 
                           body_bbox: Tuple[int, int, int, int]) -> None:
        """Aggiunge caratteristiche razziali speciali"""
        if self.race == Race.DEMON and random.random() > 0.6:
            # Coda demoniaca
            x1, y1, x2, y2 = body_bbox
            cx = (x1 + x2) // 2
            points = [(cx, y2), (cx - 2, y2 + 4), (cx - 1, y2 + 8),
                     (cx, y2 + 10), (cx + 1, y2 + 8), (cx + 2, y2 + 4)]
            draw.polygon(points, fill=(200, 50, 50), outline=(150, 0, 0))
            self.metadata.features.append("demon_tail")


class MonsterRenderer(CreatureRenderer):
    """Renderer base per mostri"""
    
    def __init__(self, monster_type: str, 
                 width: int = Config.DEFAULT_WIDTH,
                 height: int = Config.DEFAULT_HEIGHT):
        super().__init__(width, height)
        self.monster_type = monster_type
        self.metadata = CreatureMetadata(
            creature_type=monster_type,
            stats=self._generate_monster_stats()
        )
    
    def _generate_monster_stats(self) -> Dict[str, int]:
        """Genera statistiche casuali per mostri"""
        return {
            'power': random.randint(10, 20),
            'defense': random.randint(5, 15),
            'speed': random.randint(3, 12),
            'threat_level': random.randint(1, 10)
        }
    
    def render(self) -> Image.Image:
        """Metodo di rendering da sovrascrivere"""
        raise NotImplementedError("Subclasses must implement render()")


class OrganicMonsterRenderer(MonsterRenderer):
    """Renderer per mostri organici"""
    
    def __init__(self, width: int = Config.DEFAULT_WIDTH, 
                 height: int = Config.DEFAULT_HEIGHT):
        super().__init__(CreatureType.ORGANIC_MONSTER.value, width, height)
    
    def render(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Colori
        base_colors = [(100, 200, 50), (200, 50, 200), (50, 100, 200), (200, 100, 0)]
        main_color = random.choice(base_colors)
        dark_color = tuple(int(c * 0.6) for c in main_color)
        
        center_x, center_y = self.width // 2, self.height // 2 + 5
        radius = min(self.width, self.height) // 3
        
        # Corpo blob
        num_points = random.randint(6, 10)
        points = []
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            r = radius + random.randint(-radius//3, radius//3)
            x = int(center_x + r * math.cos(angle))
            y = int(center_y + r * math.sin(angle))
            points.append((x, y))
        
        draw.polygon(points, fill=main_color, outline=dark_color)
        self.metadata.features.append("blob_body")
        
        # Tentacoli
        num_tentacles = random.randint(3, 6)
        for i in range(num_tentacles):
            angle = (2 * math.pi * i) / num_tentacles + random.uniform(-0.5, 0.5)
            start_x = int(center_x + (radius * 0.8) * math.cos(angle))
            start_y = int(center_y + (radius * 0.8) * math.sin(angle))
            
            prev_x, prev_y = start_x, start_y
            for j in range(5):
                offset_x = random.randint(-3, 3)
                offset_y = random.randint(2, 6)
                next_x, next_y = prev_x + offset_x, prev_y + offset_y
                width = max(1, 4 - j)
                draw.line([(prev_x, prev_y), (next_x, next_y)], fill=dark_color, width=width)
                prev_x, prev_y = next_x, next_y
        
        self.metadata.features.append(f"tentacles_x{num_tentacles}")
        
        # Occhi multipli
        num_eyes = random.randint(2, 6)
        for _ in range(num_eyes):
            ex = center_x + random.randint(-radius//2, radius//2)
            ey = center_y + random.randint(-radius//2, radius//2)
            eye_size = random.randint(2, 4)
            
            draw.ellipse([ex - eye_size, ey - eye_size, ex + eye_size, ey + eye_size], 
                        fill=(255, 200, 0))
            draw.ellipse([ex - 1, ey - 1, ex + 1, ey + 1], fill=(0, 0, 0))
        
        self.metadata.features.append(f"eyes_x{num_eyes}")
        
        return img


class MechanicalMonsterRenderer(MonsterRenderer):
    """Renderer per mostri meccanici"""
    
    def __init__(self, width: int = Config.DEFAULT_WIDTH, 
                 height: int = Config.DEFAULT_HEIGHT):
        super().__init__(CreatureType.MECHANICAL_MONSTER.value, width, height)
    
    def render(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        metal_colors = [(180, 180, 200), (150, 150, 170), (100, 100, 120)]
        main_color = random.choice(metal_colors)
        dark_metal = tuple(int(c * 0.5) for c in main_color)
        
        # Corpo
        body_x1, body_y1 = self.width // 2 - 12, 20
        body_x2, body_y2 = self.width // 2 + 12, 45
        draw.rectangle([body_x1, body_y1, body_x2, body_y2], fill=main_color, outline=dark_metal)
        
        # Testa
        head_y = 10
        draw.rectangle([body_x1 + 4, head_y, body_x2 - 4, body_y1], 
                      fill=main_color, outline=dark_metal)
        
        # LED Eyes
        draw.rectangle([body_x1 + 6, head_y + 4, body_x1 + 9, head_y + 7], fill=(0, 255, 255))
        draw.rectangle([body_x2 - 9, head_y + 4, body_x2 - 6, head_y + 7], fill=(0, 255, 255))
        
        # Antenna
        draw.line([(self.width // 2, head_y), (self.width // 2, head_y - 4)], 
                 fill=dark_metal, width=2)
        draw.ellipse([self.width // 2 - 2, head_y - 6, self.width // 2 + 2, head_y - 4], 
                    fill=(255, 0, 0))
        
        self.metadata.features.extend(["led_eyes", "antenna", "metal_body"])
        
        return img


class EldritchMonsterRenderer(MonsterRenderer):
    """Renderer per mostri lovecraftiani"""
    
    def __init__(self, width: int = Config.DEFAULT_WIDTH, 
                 height: int = Config.DEFAULT_HEIGHT):
        super().__init__(CreatureType.ELDRITCH_MONSTER.value, width, height)
    
    def render(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        colors = [(100, 0, 100), (0, 100, 100), (100, 100, 0), (150, 0, 150)]
        main_color = random.choice(colors)
        
        center_x, center_y = self.width // 2, self.height // 2
        
        # Forme impossibili stratificate
        layers = random.randint(3, 5)
        for layer in range(layers):
            radius = 15 - layer * 3
            num_points = 7 + layer
            
            points = []
            for i in range(num_points):
                angle = (2 * math.pi * i) / num_points + layer * 0.5
                r = radius + random.randint(-2, 2)
                x = int(center_x + r * math.cos(angle))
                y = int(center_y + r * math.sin(angle))
                points.append((x, y))
            
            layer_color = tuple(int(c * (1 - layer * 0.15)) for c in main_color)
            draw.polygon(points, fill=layer_color, outline=(0, 0, 0))
        
        # Occhi multipli in cerchio
        num_eyes = random.randint(5, 9)
        eye_radius = 12
        for i in range(num_eyes):
            angle = (2 * math.pi * i) / num_eyes
            ex = int(center_x + eye_radius * math.cos(angle))
            ey = int(center_y + eye_radius * math.sin(angle))
            
            draw.ellipse([ex - 3, ey - 3, ex + 3, ey + 3], fill=(255, 255, 200), outline=(0, 0, 0))
            draw.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=(200, 0, 0))
            draw.ellipse([ex - 1, ey - 1, ex + 1, ey + 1], fill=(0, 0, 0))
        
        self.metadata.features.append(f"eldritch_eyes_x{num_eyes}")
        
        return img


# ============================================================================
# SISTEMA DI ESPORTAZIONE
# ============================================================================

class CreatureExporter:
    """Gestisce l'esportazione di creature e sprite sheets"""
    
    def __init__(self, output_dir: str = Config.OUTPUT_DIR):
        self.output_dir = output_dir
        self.metadata_dir = os.path.join(output_dir, "metadata")
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def export_creature(self, creature: Image.Image, 
                       metadata: CreatureMetadata,
                       filename: str,
                       scale: int = Config.DEFAULT_SCALE) -> str:
        """Esporta singola creatura con metadati"""
        # Scala e salva immagine
        scaled = creature.resize(
            (creature.width * scale, creature.height * scale),
            Image.NEAREST
        )
        
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        scaled.save(filepath)
        
        # Salva metadati
        metadata_path = os.path.join(self.metadata_dir, f"{filename}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def export_sprite_sheet(self, creatures: List[Image.Image],
                          filename: str = "sprite_sheet",
                          columns: int = Config.SPRITE_SHEET_COLUMNS,
                          scale: int = Config.DEFAULT_SCALE) -> Optional[str]:
        """Crea sprite sheet da lista di creature"""
        if not creatures:
            return None
        
        sprite_w = creatures[0].width * scale
        sprite_h = creatures[0].height * scale
        
        rows = (len(creatures) + columns - 1) // columns
        sheet = Image.new("RGBA", (sprite_w * columns, sprite_h * rows), (0, 0, 0, 0))
        
        for i, creature in enumerate(creatures):
            row = i // columns
            col = i % columns
            scaled = creature.resize((sprite_w, sprite_h), Image.NEAREST)
            sheet.paste(scaled, (col * sprite_w, row * sprite_h))
        
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        sheet.save(filepath)
        return filepath
    
    def export_batch_metadata(self, all_metadata: List[CreatureMetadata],
                            filename: str = "batch_metadata") -> str:
        """Esporta metadati batch"""
        filepath = os.path.join(self.metadata_dir, f"{filename}.json")
        
        data = {
            'total_creatures': len(all_metadata),
            'creatures': [asdict(m) for m in all_metadata]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath


# ============================================================================
# FACTORY PATTERN
# ============================================================================

class CreatureFactory:
    """Factory per creare diverse tipologie di creature"""
    
    @staticmethod
    def create_humanoid(race: Optional[Race] = None,
                       char_class: Optional[CharacterClass] = None) -> HumanoidRenderer:
        """Crea umanoide con parametri opzionali"""
        race = race or random.choice(list(Race))
        char_class = char_class or random.choice(list(CharacterClass))
        return HumanoidRenderer(race, char_class)
    
    @staticmethod
    def create_monster(monster_type: Optional[CreatureType] = None) -> MonsterRenderer:
        """Crea mostro casuale o specifico"""
        if monster_type is None:
            monster_type = random.choice([
                CreatureType.ORGANIC_MONSTER,
                CreatureType.MECHANICAL_MONSTER,
                CreatureType.ELDRITCH_MONSTER
            ])
        
        renderers = {
            CreatureType.ORGANIC_MONSTER: OrganicMonsterRenderer,
            CreatureType.MECHANICAL_MONSTER: MechanicalMonsterRenderer,
            CreatureType.ELDRITCH_MONSTER: EldritchMonsterRenderer
        }
        
        renderer_class = renderers.get(monster_type, OrganicMonsterRenderer)
        return renderer_class()
    
    @staticmethod
    def create_random() -> CreatureRenderer:
        """Crea creatura completamente casuale"""
        if random.random() < 0.5:
            return CreatureFactory.create_humanoid()
        else:
            return CreatureFactory.create_monster()


# ============================================================================
# INTERFACCIA UTENTE
# ============================================================================

class GeneratorUI:
    """Interfaccia utente per il generatore"""
    
    def __init__(self):
        self.glitch_engine = GlitchEngine()
        self.exporter = CreatureExporter()
    
    def print_header(self):
        """Stampa intestazione"""
        print("\n" + "=" * 70)
        print("  🎨 ADVANCED GLITCH CREATURE GENERATOR - PROFESSIONAL EDITION")
        print("=" * 70)
    
    def print_menu(self):
        """Stampa menu opzioni"""
        print("\n📋 MODALITÀ DI GENERAZIONE:")
        print("  1. Umanoidi (Scegli razza e classe)")
        print("  2. Mostri Organici")
        print("  3. Mostri Meccanici")
        print("  4. Mostri Eldritch")
        print("  5. Mix Casuale")
        print("  6. Batch Completo (tutte le varianti)")
    
    def get_user_choice(self) -> Dict[str, Any]:
        """Raccoglie input utente"""
        self.print_header()
        self.print_menu()
        
        choice = input("\n👉 Scegli modalità (1-6) [default: 5]: ").strip() or "5"
        num_sprites = int(input("👉 Numero di sprite [default: 10]: ").strip() or "10")
        
        intensity_input = input("👉 Intensità glitch (light/medium/heavy/extreme) [default: medium]: ").strip() or "medium"
        try:
            intensity = GlitchIntensity(intensity_input.lower())
        except ValueError:
            intensity = GlitchIntensity.MEDIUM
        
        create_sheet = input("👉 Creare sprite sheet? (s/n) [default: s]: ").lower() != 'n'
        
        return {
            'mode': choice,
            'count': num_sprites,
            'intensity': intensity,
            'create_sheet': create_sheet
        }
    
    def generate_creatures(self, config: Dict[str, Any]) -> Tuple[List[Image.Image], List[CreatureMetadata]]:
        """Genera creature secondo configurazione"""
        creatures = []
        all_metadata = []
        
        print(f"\n🎨 Generazione di {config['count']} creature...")
        print("-" * 70)
        
        for i in range(config['count']):
            # Crea renderer
            renderer = self._create_renderer(config['mode'])
            
            # Renderizza creatura base
            base_creature = renderer.render()
            
            # Applica glitch
            glitched_creature, effects = self.glitch_engine.apply_glitch(
                base_creature, 
                config['intensity']
            )
            
            # Aggiorna metadati
            metadata = renderer.get_metadata()
            metadata.glitch_effects = effects
            
            creatures.append(glitched_creature)
            all_metadata.append(metadata)
            
            # Salva singola creatura
            filename = f"creature_{i:03d}_{metadata.creature_type}"
            if metadata.character_class:
                filename += f"_{metadata.character_class}"
            
            filepath = self.exporter.export_creature(
                glitched_creature,
                metadata,
                filename
            )
            
            # Progress
            self._print_progress(i + 1, config['count'], metadata, filepath)
        
        return creatures, all_metadata
    
    def _create_renderer(self, mode: str) -> CreatureRenderer:
        """Crea renderer basato sulla modalità"""
        if mode == "1":
            return CreatureFactory.create_humanoid()
        elif mode == "2":
            return CreatureFactory.create_monster(CreatureType.ORGANIC_MONSTER)
        elif mode == "3":
            return CreatureFactory.create_monster(CreatureType.MECHANICAL_MONSTER)
        elif mode == "4":
            return CreatureFactory.create_monster(CreatureType.ELDRITCH_MONSTER)
        elif mode == "6":
            # Batch: cicla tra tutte le varianti
            return CreatureFactory.create_random()
        else:  # mode == "5" o default
            return CreatureFactory.create_random()
    
    def _print_progress(self, current: int, total: int, 
                       metadata: CreatureMetadata, filepath: str):
        """Stampa progresso generazione"""
        type_str = metadata.creature_type
        if metadata.character_class:
            type_str += f"-{metadata.character_class}"
        
        print(f"  ✓ [{current:2d}/{total}] {type_str:30s} → {os.path.basename(filepath)}")
    
    def finalize(self, creatures: List[Image.Image], 
                all_metadata: List[CreatureMetadata],
                create_sheet: bool):
        """Finalizza generazione con sprite sheet e riepilogo"""
        
        # Sprite sheet
        if create_sheet:
            sheet_path = self.exporter.export_sprite_sheet(creatures)
            print(f"\n📄 Sprite sheet: {sheet_path}")
        
        # Batch metadata
        batch_metadata_path = self.exporter.export_batch_metadata(all_metadata)
        print(f"📊 Metadata batch: {batch_metadata_path}")
        
        # Statistiche
        print("\n" + "=" * 70)
        print("📈 STATISTICHE GENERAZIONE:")
        print(f"  • Creature totali: {len(creatures)}")
        
        type_counts = {}
        for meta in all_metadata:
            type_counts[meta.creature_type] = type_counts.get(meta.creature_type, 0) + 1
        
        for ctype, count in type_counts.items():
            print(f"  • {ctype}: {count}")
        
        print(f"\n✨ Completato! File salvati in '{self.exporter.output_dir}/'")
        print("=" * 70)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Entry point principale"""
    try:
        ui = GeneratorUI()
        config = ui.get_user_choice()
        creatures, metadata = ui.generate_creatures(config)
        ui.finalize(creatures, metadata, config['create_sheet'])
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Generazione interrotta dall'utente")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()