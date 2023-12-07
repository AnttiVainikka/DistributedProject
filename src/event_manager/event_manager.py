from dataclasses import dataclass
from typing import Callable

# Very stupid, but working
class EventManager:
    def __init__(self):
        self._events: dict[str, list[Callable]] = {}

    def connect_to_event(self, event: str, callback: Callable):
        if event not in self._events:
            raise RuntimeError(f"Event {event} does not exist in {type(self).__name__}")
        else:
            self._events[event].append(callback)

    def _raise_event(self, event: str, *args, **kwargs):
        if event not in self._events:
            raise RuntimeError(f"Event {event} is not registered!")
        else:
            for callback in self._events[event]:
                callback(*args, **kwargs)

    def _register_event(self, event: str):
        self._events[event] = []
