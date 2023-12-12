from dataclasses import dataclass

@dataclass
class State:
    """
    Simple data class representing the current state of a media player.

    The State class is a simple data class used to encapsulate and send the current state
    of a media player over the network.
    """
    index: int # The index of the media currently played
    timestamp: int # The timestamp of the currently played media
    playing: int # The media is currently in play state
