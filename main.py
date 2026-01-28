import sys
import os

# Hide pygame support prompt
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'

import warnings
from pathlib import Path

# Suppress pygame-internal warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")

# Add dependencies to path logic
sys.path.append(os.getcwd())

# Auto-generate assets if missing
from engine.generate_assets_folder import verify_and_generate
verify_and_generate(Path(__file__).resolve().parent)

from engine.core.core import GameContext
from src.scenes.world_scene import WorldScene
from src.scenes.battle_scene import BattleScene
from src.settings import *

class RPGGame(GameContext):
    def __init__(self):
        super().__init__("Undertale Clone")
        
    def _register_default_services(self) -> None:
        super()._register_default_services()
        from engine.world.camera_system import ViewportManager
        self.services.register("viewport", ViewportManager(INTERNAL_WIDTH, INTERNAL_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT))

if __name__ == "__main__":
    game = RPGGame()
    
    # Register Scenes
    game.scenes = {
        "world": WorldScene,
        "battle": BattleScene
    }
    game.register_modules(scenes=game.scenes)
    
    # Run
    game.run()
