__all__ = ["Event", "EventBus"]

from collections import defaultdict, deque
from engine.world.constants import EventType
from engine.core.singleton import SingletonRegistry


class Event:
    def __init__(self, type_, data=None):
        self.type = type_
        self.data = data or {}


class EventBus:
    def __init__(self, register_singleton: bool = True):
        # subscribers[event_type] = [callback1, callback2, ...]
        self.subscribers = defaultdict(list)
        self.event_queue = deque()
        # register in singleton registry (optional)
        if register_singleton:
            try:
                SingletonRegistry.register(self, name="engine.systems.EventBus")
            except ValueError:
                # If enforcement is enabled and another EventBus exists this will raise;
                # higher-level code can decide whether to allow multiple EventBus instances.
                raise

    def subscribe(self, event_type, callback):
        """Iscrive una funzione/metodo a un certo tipo di evento"""
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        """Rimuove una sottoscrizione"""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)

    def publish(self, event_type, data=None):
        """Aggiunge un evento alla coda"""
        self.event_queue.append(Event(event_type, data))

    def dispatch(self):
        """Distribuisce gli eventi ai subscriber.

        For each event, iterates subscribers only once and calls both the
        subscribers for the specific event type and those registered for
        EventType.ALL_EVENTS.
        """
        while self.event_queue:
            event = self.event_queue.popleft()
            # collect callbacks for the specific type and the ALL_EVENTS
            callbacks = list(self.subscribers.get(event.type, []))
            callbacks_all = list(self.subscribers.get(EventType.ALL_EVENTS, []))
            for callback in callbacks + callbacks_all:
                try:
                    callback(event)
                except Exception:
                    # avoid breaking dispatch loop on subscriber errors
                    # optionally: log exception via a logger (omitted to keep dependency-free)
                    pass
