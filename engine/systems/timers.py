__all__ = ["Timer", "TimersManager"]


from typing import Any, Dict, Optional


class Timer:
    def __init__(self, duration: float, repeat: bool = False, event_bus: Any = None, event_type: Any = None, payload: Optional[Dict] = None, ignore_pause: bool = False) -> None:
        """
        duration: durata in secondi
        repeat: True se deve ripartire automaticamente
        event_bus: opzionale, per pubblicare un evento alla fine
        event_type: opzionale, tipo di evento da pubblicare
        payload: opzionale, dati da passare con l'evento
        """
        self.duration = duration
        self.repeat = repeat
        self.event_bus = event_bus
        self.event_type = event_type
        self.payload = payload or {}
        self.remaining = duration
        self.running = False
        self.ignore_pause = ignore_pause
        self.expired = False 

    def start(self) -> None:
        self.remaining = self.duration
        self.running = True
        self.expired = False

    def stop(self):
        self.running = False
        # non segna expired: significa che è stato fermato manualmente

    def reset(self):
        self.remaining = self.duration
        self.running = True
        self.expired = False

    def resume(self):
        if not self.expired:
            self.running = True

    def update(self, dt: float, paused: bool = False) -> None:
        if not self.running:
            return
        if paused and not self.ignore_pause:
            return  

        self.remaining -= dt
        if self.remaining <= 0:
            # publish using EventBus.publish(event_type, data)
            if self.event_bus and self.event_type is not None:
                try:
                    self.event_bus.publish(self.event_type, self.payload)
                except Exception as e:
                    print(f"[Timers] Failed to publish timer event: {e}")
            elif self.event_bus and self.event_type is None:
                print("[Timers] Warning: Timer has event_bus but no event_type specified")

            if self.repeat:
                self.remaining += self.duration
            else:
                self.running = False
                self.expired = True  # <--- solo qui segna scaduto


class TimersManager:
    def __init__(self) -> None:
        self.timers: Dict[str, Timer] = {}

    def add_timer(self, key: str, timer: Timer) -> Timer:
        self.timers[key] = timer
        return timer

    def remove_timer(self, key: str) -> None:
        if key in self.timers:
            del self.timers[key]

    def get_timer(self, key: str) -> Optional[Timer]:
        return self.timers.get(key)

    def update(self, dt: float, paused: bool = False) -> None:
        for key, timer in list(self.timers.items()):
            timer.update(dt, paused)
            if timer.expired:
                del self.timers[key]

    def new_timer(self, duration: float, repeat: bool = False, event_bus: Any = None, event_type: Any = None, payload: Optional[Dict] = None, ignore_pause: bool = False) -> Timer:
        return Timer(
            duration=duration,
            repeat=repeat,
            event_bus=event_bus,
            event_type=event_type,
            payload=payload,
            ignore_pause=ignore_pause
        )



"""Esempio di utilizzo:
from constants import EventType

# Player ha un Timer per il double jump
self.double_jump_cooldown = Timer(
    duration=1.0,  # 1 secondo
    repeat=False,
    event_bus=self.event_bus,
    event_type=EventType.ABILITY_READY,
    payload={"ability": "double_jump"}
)

# Quando il player salta due volte:
if not self.double_jump_cooldown.running:
    self.do_double_jump()
    self.double_jump_cooldown.start()

# nel event_bus.subscribe
def on_ability_ready(self, ability):
    if ability == "double_jump":
        print("Il double jump è pronto di nuovo!")

# Esempio di parry con finestra temporale
# Quando il player preme il tasto parry:
self.is_parrying = True
self.parry_timer = Timer(
    duration=0.3,  # finestra di 300ms
    repeat=False,
    event_bus=self.event_bus,
    event_type=EventType.PARRY_END,
    payload={"player": self}
)
self.parry_timer.start()

# Nel game loop
self.parry_timer.update(dt)

# E nel listener:
def on_parry_end(self, player):
    player.is_parrying = False
    print("Parry finito!")

"""