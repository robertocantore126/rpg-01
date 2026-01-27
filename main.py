import sys
import os

# Add dependencies to path logic if needed, but assuming running from root
sys.path.append(os.getcwd()) 

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
