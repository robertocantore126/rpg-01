__all__ = [
    "CollisionSide", "EventType", "ASSETS_DIR", "GAME_W", "GAME_H", 
    "SCREEN_WIDTH", "SCREEN_HEIGHT", "SCREEN_CENTER", "FPS", "SCREEN_MID_LEFT",
    "CHUNK_SIZE", "SCREEN_MID_RIGHT", "SCREEN_TOP", "SCREEN_BOTTOM",
    "PLATINUM", "FRENCH_GREY", "ROSE_QUARTZ", "LILAC", "DIM_GRAY", # P1
    "PERWINKLE", "CLARET", "TURQUOISE", "PRUSSIAN_BLUE", "ACQUAMARINE" # P2
    ]

import os 
from enum import Enum, auto

GAME_W = 320 # 540
GAME_H = 240 # 450
SCREEN_WIDTH = GAME_W * 2
SCREEN_HEIGHT = GAME_H * 2

SCREEN_CENTER = (GAME_W // 2, GAME_H // 2)
SCREEN_MID_LEFT = (0, GAME_H // 2)
SCREEN_MID_RIGHT = (GAME_W, GAME_H // 2)
SCREEN_TOP = (GAME_W // 2, 0)
SCREEN_BOTTOM = (GAME_W // 2, GAME_H)

FPS = 60
CHUNK_SIZE = 256

ASSETS_DIR = "assets"
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
TILEMAPS_DIR = os.path.join(ASSETS_DIR, "tilemaps")

# Palette 1
PLATINUM        = (215, 217, 215)
FRENCH_GREY     = (201, 197, 203)
ROSE_QUARTZ     = (186, 172, 189)
LILAC           = (180, 142, 174)
DIM_GRAY        = (100, 110, 104)

# Palette 2
PERWINKLE       = (178, 171, 242)
CLARET          = (137, 4, 61)
TURQUOISE       = (47, 230, 222)
PRUSSIAN_BLUE   = (28, 48, 65)
ACQUAMARINE     = (24, 242, 178)

# Palette 3 (day-night like)
EGGSHELL = (250, 243, 221)
MIDNIGHT_GREEN = (15, 82, 87)
ROSE_QUARTZ_G = (156, 146, 163)
DARK_PURPLE = (42, 31, 45)
WENGE = (79, 70, 81)

# Palette 4 - game palette
EERIE_BLACK = (24, 23, 27)          # Black side
LEMON_CHIFFON = 247, 237, 197       # White side
JET = (45, 43, 38)                  # White side ground
DUN = (205, 194, 169)               # Black side ground
BATTLESHIP_GRAY = (155, 148, 130)   # Text

# also works with:
AMARANTH_PURPLE = (175, 27, 63)
ROSY_BROWN = (201, 157, 163)
PERWINKLE_2 = (201, 201, 238)

LETTERBOXING_BANDS = (0, 0, 0)  # black

# ===============================
# States for the Multiplayer callback
# ===============================
class MultiplayerAction(Enum):
    INPUT = auto()
    GET_STATE = auto()
    UPDATE_STATE = auto()


class CollisionSide(Enum):
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()


class EventType(Enum):
    # --- Input (tastiera) ---
    KEY_DOWN = auto()   # arg: key
    KEY_UP = auto()     # arg: key
    KEY_HELD = auto()   # arg: key (opzionale, se gestisci i "continui")

    # --- Input (mouse) ---
    MOUSE_MOVE = auto()     # arg: pos (x, y)
    MOUSE_BUTTON_DOWN = auto()  # arg: button, pos
    MOUSE_BUTTON_UP = auto()    # arg: button, pos
    MOUSE_WHEEL = auto()        # arg: delta

    # --- Game lifecycle ---
    QUIT = auto()
    SCENE_CHANGE = auto()   # arg: new_scene
    GAME_PAUSE = auto()
    GAME_RESUME = auto()
    GAME_OVER = auto()      # arg: score, reason
    SAVE_GAME = auto()
    LOAD_GAME = auto()

    # --- Collision / Gameplay ---
    COLLISION = auto()         # arg: entity_a, entity_b
    PLAYER_HIT = auto()        # arg: damage, source
    ENEMY_HIT = auto()         # arg: damage, source
    PROJECTILE_FIRED = auto()  # arg: projectile
    PROJECTILE_HIT = auto()    # arg: target

    # --- Entity lifecycle ---
    ENEMY_SPAWNED = auto()  # arg: enemy
    ENEMY_DIED = auto()     # arg: enemy, loot (opzionale)
    PLAYER_RESPAWNED = auto()  # arg: player  

    # --- Combat ---
    BULLET_FIRED = auto()   # arg: bullet
    EXPLOSION = auto()      # arg: position, radius
    MELEE_ATTACK = auto()   # arg: attacker, target

    # --- World events ---
    PICKUP_COLLECTED = auto()  # arg: item, player
    DOOR_OPENED = auto()       # arg: door, player
    TRAP_ACTIVATED = auto()    # arg: trap, player
    ACHIEVEMENT_UNLOCKED = auto()
    ALL_EVENTS = auto()

    # --- UI events ---
    SHOW_MESSAGE = auto()     # arg: message
    INVENTORY_OPENED = auto()  # arg: player
    DIALOG_STARTED = auto()   # arg: dialog_id, npc
    UI_BUTTON_CLICKED = auto()
    UI_FOCUS_CHANGED = auto()
    UI_VALUE_CHANGED = auto()

    # --- Audio events ---
    PLAY_SOUND = auto()      # arg: sound_id, volume
    MUSIC_CHANGED = auto()   # arg: music_id, fade_time

    # --- Custom gameplay ---
    ITEM_PICKUP = auto()   # arg: item
    ITEM_DROP = auto()     # arg: item
    LEVEL_COMPLETE = auto()
    PLAYER_DEAD = auto()


class ECSEvent(Enum):
    ENTITY_SPAWNED = auto()
    ENTITY_REMOVED = auto()
    COMPONENT_ADDED = auto()
    COMPONENT_REMOVED = auto()
    

class BodyType(Enum):
    STATIC = auto()
    DYNAMIC = auto()
    KINEMATIC = auto()
    