# engine/systems/state_manager.py
__all__ = ["GameState", "StateManager"]

# engine/systems/state_manager.py
from enum import Enum, auto

class GameState(Enum):
    LOADING = auto()
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    WIN = auto()

class StateManager:
    def __init__(self):
        self.current_state = GameState.LOADING
        self.prev_state = None
        self.next_state = None  # messaggio opzionale per comunicare
        # mappa di transizioni legali
        self.transitions = {
            GameState.LOADING: [GameState.MENU],
            GameState.MENU: [GameState.PLAYING],
            GameState.PLAYING: [GameState.PAUSED, GameState.GAME_OVER, GameState.WIN],
            GameState.PAUSED: [GameState.PLAYING, GameState.MENU],
            GameState.GAME_OVER: [GameState.MENU],
            GameState.WIN: [GameState.MENU],
        }

    def can_transition(self, new_state: GameState) -> bool:
        return new_state in self.transitions.get(self.current_state, [])

    def change_state(self, new_state: GameState, message=None):
        if not self.can_transition(new_state):
            raise ValueError(f"Transizione illegale: {self.current_state} -> {new_state}")
        self.prev_state = self.current_state
        self.current_state = new_state
        self.next_state = message  # opzionale
        print(f"Stato cambiato: {self.prev_state} -> {self.current_state} (msg: {message})")

    def paused(self) -> bool:
        return self.current_state == GameState.PAUSED
    