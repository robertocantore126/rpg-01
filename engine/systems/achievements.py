__all__ = ["Achievement", "AchievementManager"]

"""
1. I vari sistemi del gioco emettono eventi ("nemico ucciso", "missione completata", "tot monete raccolte").
2. L'AchievementManager ascolta questi eventi → aggiorna lo stato degli achievements.
3. Quando uno è completato → emette a sua volta un evento (“achievement sbloccato”) → la UI mostra un popup.

🏗️ Struttura del sistema

EventBus → centro di comunicazione (publish/subscribe).
AchievementManager → contiene la lista di achievements e ascolta gli eventi.
Achievement → oggetto singolo che sa quali condizioni deve soddisfare.
UiManager/NotificationSystem → si iscrive all'evento “achievement sbloccato” e mostra il popup.
"""

from engine.world.constants import EventType

class Achievement:
    def __init__(self, id_, name, description, condition):
        self.id = id_
        self.name = name
        self.description = description
        self.condition = condition  # funzione che valuta l'evento
        self.unlocked = False

    def check(self, event_type, data):
        if not self.unlocked and self.condition(event_type, data):
            self.unlocked = True
            return True
        return False

class AchievementManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.achievements = []

        # ascolta *tutti* gli eventi di gioco
        self.event_bus.subscribe(EventType.ALL_EVENTS, self.on_event)

        self.register_achievements()

    def add_achievement(self, achievement):
        self.achievements.append(achievement)

    def on_event(self, event):
        if not event: return
        event_type, data = event.type, event.data

        for ach in self.achievements:
            if ach.check(event_type, data):
                # quando si sblocca → notifica la UI
                self.event_bus.publish(EventType.ACHIEVEMENT_UNLOCKED, ach)

    def register_achievements(self):
        pass

""" Esempio d'uso:
class UiNotifications:
    def __init__(self, event_bus):
        event_bus.subscribe("achievement_unlocked", self.show_popup)

    def show_popup(self, achievement):
        print(f"🏆 Achievement Unlocked: {achievement.name} - {achievement.description}")
        # qui poi lo disegnerai come popup su schermo

# E poi:

# Setup
bus = EventBus()
ach_manager = AchievementManager(bus)
ui = UiNotifications(bus)

# Definizione achievements
ach_manager.add_achievement(
    Achievement("kill10", "Cacciatore", "Uccidi 10 nemici",
                lambda ev, data: ev == "enemy_killed" and data.get("count") >= 10)
)
ach_manager.add_achievement(
    Achievement("first_gold", "Ricco!", "Ottieni la tua prima moneta",
                lambda ev, data: ev == "coin_collected" and data.get("total") >= 1)
)

# Simulazione eventi
bus.publish("*", {"type": "enemy_killed", "data": {"count": 10}})
bus.publish("*", {"type": "coin_collected", "data": {"total": 1}})

"""