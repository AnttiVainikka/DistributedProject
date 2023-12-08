from enum import Enum

class CommandType(Enum):
    Stop = 1
    Resume = 2
    JumpToTimestamp = 3
    Set = 4
    State = 5

class ApplicationMessage:
    command_type: int

    def __init__(self, command_type: int):
        self.command_type = command_type

class StopMessage(ApplicationMessage):
    def __init__(self):
        super().__init__(CommandType.Stop.value)

class ResumeMessage(ApplicationMessage):
    def __init__(self):
        super().__init__(CommandType.Resume.value)

class SetMessage(ApplicationMessage):
    def __init__(self, index: int = -1):
        super().__init__(CommandType.Set.value)
        self.index = index

class JumpToTimestampMessage(ApplicationMessage):
    destination_timestamp: int

    def __init__(self, destination_timestamp: int = -1):
        super().__init__(CommandType.JumpToTimestamp.value)
        self.destination_timestamp = destination_timestamp

class StateMessage(ApplicationMessage):
    def __init__(self, state):
        super().__init__(CommandType.State.value)
        self.state = state