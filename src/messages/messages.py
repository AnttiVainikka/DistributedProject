from enum import Enum

from application.state import State

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

    def __init_from_dict__(self, d: dict[str, any]):
        self.command_type = d["command_type"]

    @property
    def __dict__(self) -> dict[str, any]:
        return {
            "command_type": self.command_type
        }
    
    def from_dict(d: dict[str, any]) -> "ApplicationMessage":
        message = None
        match d["command_type"]:
            case CommandType.Stop.value:
                message = StopMessage.__new__(StopMessage)

            case CommandType.Resume.value:
                message = ResumeMessage.__new__(ResumeMessage)
            
            case CommandType.JumpToTimestamp.value:
                message = JumpToTimestampMessage.__new__(JumpToTimestampMessage)

            case CommandType.Set.value:
                message = SetMessage.__new__(SetMessage)

            case CommandType.State.value:
                message = StateMessage.__new__(StateMessage)

        if message is not None:
            message.__init_from_dict__(d)

        return message

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

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.index = d["index"]

    @property
    def __dict__(self) -> dict[str, any]:
        s = super().__dict__
        s["index"] = self.index
        return s

class JumpToTimestampMessage(ApplicationMessage):
    destination_timestamp: int

    def __init__(self, destination_timestamp: int = -1):
        super().__init__(CommandType.JumpToTimestamp.value)
        self.destination_timestamp = destination_timestamp

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.destination_timestamp = d["destination_timestamp"]

    @property
    def __dict__(self) -> dict[str, any]:
        s = super().__dict__
        s["destination_timestamp"] = self.destination_timestamp
        return s

class StateMessage(ApplicationMessage):
    def __init__(self, state: State):
        super().__init__(CommandType.State.value)
        self.state = state

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.state = State(**d["state"])

    @property
    def __dict__(self) -> dict[str, any]:
        s = super().__dict__
        s["state"] = self.state.__dict__
        return s