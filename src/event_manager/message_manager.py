from typing import Callable

import log

_logger = log.getLogger(__name__)

class MessageManager:
    """
    Base class for managing custom message types in the lobby.

    The MessageManager class serves as a base class for managing custom message types within a lobby. Inherited classes
    can specify and handle their own message types. Other objects can register their message types along with callback
    functions, and when a message of a specified type is received, the associated callback is automatically invoked.
    """
    def __init__(self):
        self._message_types: dict[object, Callable] = {}

    def connect_to_message(self, type: object, callback: Callable):
        """
        Connect a callback function to handle a specific message type.

        This method allows registering a custom message type along with a callback function. When a message of the specified
        type is received, the associated callback function will be automatically called.

        Parameters:
        - type (object): The custom message type to be registered.
        - callback (Callable): The callback function to handle messages of the specified type.
        """
        if type in self._message_types:
            raise RuntimeError(f"Message type {str(type)} already exists")
        
        self._message_types[type] = callback

    def _call_message_handler(self, type: object, *args, **kwargs):
        """
        Invoke the callback function associated with a specific message type.

        This method can be used by the inherited class to invoke the callback function associated with a specific message type.

        Parameters:
        - type (object): The custom message type for which the callback function should be invoked.
        - args: Positional arguments to be passed to the callback function.
        - kwargs: Keyword arguments to be passed to the callback function.
        """
        if type in self._message_types:
            self._message_types[type](*args, **kwargs)
        else:
            _logger.warn(f"Message handler for {str(type)} does not exists!")
            