from typing import Callable

# Very stupid, but working
class EventManager:
    """
    General class for managing and connecting to events.

    The EventManager class provides a framework for managing events. Inherited classes can register their own events,
    and other objects can connect to these events using callback functions. When a specific event is raised, the
    registered callback functions are automatically invoked.
    """
    def __init__(self):
        self._events: dict[object, list[Callable]] = {}

    def connect_to_event(self, event: object, callback: Callable):
        """
        Connect a callback function to a specified event.

        This method allows connecting a callback function to a specified event. Whenever the event is raised, the provided
        callback function will be automatically called. If the event is not exist a RuntimeError will be raised.

        Parameters:
        - event (object): The event to which the callback function will be connected.
        - callback (Callable): The callback function to be called when the specified event is raised.
        """
        if event not in self._events:
            raise RuntimeError(f"Event {event} does not exist in {type(self).__name__}")
        else:
            self._events[event].append(callback)

    def _raise_event(self, event: object, *args, **kwargs):
        """
        Raise a specified event and call connected callbacks with provided arguments.

        This method can be used by the inherited class to raise a specified event. The provided arguments (args and kwargs)
        will be passed to all connected callbacks associated with the event.

        Parameters:
        - event (object): The event to be raised.
        - args: Positional arguments to be passed to connected callbacks.
        - kwargs: Keyword arguments to be passed to connected callbacks.
        """
        if event not in self._events:
            raise RuntimeError(f"Event {event} is not registered!")
        else:
            for callback in self._events[event]:
                callback(*args, **kwargs)

    def _register_event(self, event: object):
        """
        Register a custom event for the inherited class.

        This method can be used by the inherited class to register its own custom events.

        Parameters:
        - event (object): The custom event to be registered.
        """
        self._events[event] = []
