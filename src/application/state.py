from dataclasses import dataclass

@dataclass
class State:
    index: int
    timestamp: int
    playing: int
