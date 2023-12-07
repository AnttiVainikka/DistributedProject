from enum import Enum

class CommandType(Enum):
    Stop = 1
    Resume = 2
    JumpToTimestamp = 3
    Skip = 4

class ApplicationMessage:
    command_type: int
    media_timestamp: int

    def __init__(self, command_type: int, media_timestamp: int):
        self.command_type = command_type
        self.media_timestamp = media_timestamp

class StopMessage(ApplicationMessage):
    def __init__(self, media_timestamp: int = -1):
        super().__init__(CommandType.Stop.value, media_timestamp)

class ResumeMessage(ApplicationMessage):
    def __init__(self, media_timestamp: int = -1):
        super().__init__(CommandType.Resume.value, media_timestamp)

class SkipMessage(ApplicationMessage):
    def __init__(self, media_timestamp: int = -1):
        super().__init__(CommandType.Skip.value, media_timestamp)

class JumpToTimestampMessage(ApplicationMessage):
    destination_timestamp: int

    def __init__(self, media_timestamp: int = -1, destination_timestamp: int = -1):
        super().__init__(CommandType.JumpToTimestamp.value, media_timestamp)
        self.destination_timestamp = destination_timestamp
