from enum import Enum

class MessageHeader(Enum):
    ApplicationMessage = 1

class CommandType(Enum):
    Stop = 1
    Resume = 2
    JumpToTimestamp = 3

class BaseMessage:
    header: int

    def __init__(self, header: int):
        self.header = header

class ApplicationMessage(BaseMessage):
    command_type: int
    media_timestamp: int

    def __init__(self, command_type: int, media_timestamp: int):
        super().__init__(MessageHeader.ApplicationMessage.value)
        self.command_type = command_type
        self.media_timestamp = media_timestamp

class StopMessage(ApplicationMessage):
    def __init__(self, media_timestamp: int = -1):
        super().__init__(CommandType.Stop.value, media_timestamp)

class ResumeMessage(ApplicationMessage):
    def __init__(self, media_timestamp: int = -1):
        super().__init__(CommandType.Resume.value, media_timestamp)

class JumpToTimestampMessage(ApplicationMessage):
    destination_timestamp: int

    def __init__(self, media_timestamp: int = -1, destination_timestamp: int = -1):
        super().__init__(CommandType.JumpToTimestamp.value, media_timestamp)
        self.destination_timestamp = destination_timestamp
