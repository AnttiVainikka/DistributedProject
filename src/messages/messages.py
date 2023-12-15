from enum import Enum

from application.state import State

class MessageTypes(Enum):
    LobbyMessage = 1
    HealthCheckMessage = 2
    Election = 3
    ApplicationMessage = 4

class BaseMessage:
    def __init__(self, type: MessageTypes):
        self.type = type.value

    def __init_from_dict__(self, d: dict[str, any]):
        self.type = d['type']

    @property
    def __dict__(self) -> dict[str, any]:
        return {
            'type': self.type
        }
    
    def from_dict(d: dict[str, any]) -> "BaseMessage":
        match d['type']:
            case MessageTypes.LobbyMessage.value:
                return LobbyMessage.from_dict(d)
            
            case MessageTypes.HealthCheckMessage.value:
                return HealthCheckMessage.from_dict(d)
            
            case MessageTypes.Election.value:
                return ElectionMessage.from_dict(d)
            
            case MessageTypes.ApplicationMessage.value:
                return ApplicationMessage.from_dict(d)

##################
# LOBBY MESSAGES #
##################
class LobbyMessageType(Enum):
    RequestJoin = 1
    RequestNewMember = 2
    NewMember = 3
    MemberAccept = 4
    Leave = 5
    MemberLeft = 6

class LobbyMessage(BaseMessage):
    def __init__(self, lobby_message_type: LobbyMessageType, sender: str):
        super().__init__(MessageTypes.LobbyMessage)
        self.lobby_type = lobby_message_type.value
        self.sender = sender

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.lobby_type = d['lobby_type']
        self.sender = d['sender']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['lobby_type'] = self.lobby_type
        d['sender'] = self.sender
        return d

    def from_dict(d: [str, any]) -> "LobbyMessage":
        msg = None
        match d['lobby_type']:
            case LobbyMessageType.RequestJoin.value:
                msg = RequestJoinMessage.__new__(RequestJoinMessage)

            case LobbyMessageType.RequestNewMember.value:
                msg = RequestNewMemberMessage.__new__(RequestNewMemberMessage)

            case LobbyMessageType.NewMember.value:
                msg = NewMemberMessage.__new__(NewMemberMessage)

            case LobbyMessageType.MemberAccept.value:
                msg = MemberAcceptMessage.__new__(MemberAcceptMessage)

            case LobbyMessageType.Leave.value:
                msg = LeaveMessage.__new__(LeaveMessage)

            case LobbyMessageType.MemberLeft.value:
                msg = MemberLeftMessage.__new__(MemberLeftMessage)

        if msg is not None:
            msg.__init_from_dict__(d)

        return msg

class RequestJoinMessage(LobbyMessage):
    def __init__(self, sender: str, target: str, name: str):
        super().__init__(LobbyMessageType.RequestJoin, sender)
        self.target = target # Hack to help the leader
        self.name = name

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.target = d['target']
        self.name = d['name']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['target'] = self.target
        d['name'] = self.name
        return d
    
class RequestNewMemberMessage(LobbyMessage):
    def __init__(self, sender: str, name: str, new_member_address: str):
        super().__init__(LobbyMessageType.RequestNewMember, sender)
        self.name = name
        self.new_member_address = new_member_address

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.name = d['name']
        self.new_member_address = d['new_member_address']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['name'] = self.name
        d['new_member_address'] = self.new_member_address
        return d
    
class NewMemberMessage(LobbyMessage):
    def __init__(self, sender: str, name: str, new_member_address: str, new_member_id: int):
        super().__init__(LobbyMessageType.NewMember, sender)
        self.name = name
        self.new_member_address = new_member_address
        self.new_member_id = new_member_id

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.name = d['name']
        self.new_member_address = d['new_member_address']
        self.new_member_id = d['new_member_id']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['name'] = self.name
        d['new_member_address'] = self.new_member_address
        d['new_member_id'] = self.new_member_id
        return d

class MemberAcceptMessage(LobbyMessage):
    def __init__(self, sender: str, members: dict[str, any]):
        super().__init__(LobbyMessageType.MemberAccept, sender)
        self.members = members

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.members = d['members']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['members'] = self.members
        return d
    
class LeaveMessage(LobbyMessage):
    def __init__(self, sender: str):
        super().__init__(LobbyMessageType.Leave, sender)

class MemberLeftMessage(LobbyMessage):
    def __init__(self, sender: str, member_address: str):
        super().__init__(LobbyMessageType.MemberLeft, sender)
        self.member_address = member_address

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.member_address = d['member_address']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['member_address'] = self.member_address
        return d

###################
# HEALTH MESSAGES #
###################
class HealthCheckMessage(BaseMessage):
    def __init__(self, sender: str):
        super().__init__(MessageTypes.HealthCheckMessage)
        self.sender = sender

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.sender = d['sender']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['sender'] = self.sender
        return d
    
    def from_dict(d: dict[str, any]) -> BaseMessage:
        msg = HealthCheckMessage.__new__(HealthCheckMessage)
        msg.__init_from_dict__(d)
        return msg

#####################
# ELECTION MESSAGES #
#####################
class ElectionMessageType(Enum):
    ElectionStart = 1
    ElectionOk = 2
    IAmLeader = 3

class ElectionMessage(BaseMessage):
    def __init__(self, type: ElectionMessageType, sender: str):
        super().__init__(MessageTypes.Election)
        self.election_type = type.value
        self.sender = sender
    
    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.election_type = d['election_type']
        self.sender = d['sender']

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['election_type'] = self.election_type
        d['sender'] = self.sender
        return d
    
    def from_dict(d: dict[str, any]) -> BaseMessage:
        msg = None
        match d['election_type']:
            case ElectionMessageType.ElectionStart.value:
                msg = ElectionStartMessage.__new__(ElectionStartMessage)

            case ElectionMessageType.ElectionOk.value:
                msg = ElectionOkMessage.__new__(ElectionOkMessage)

            case ElectionMessageType.IAmLeader.value:
                msg = IAmLeaderMessage.__new__(IAmLeaderMessage)

        if msg is not None:
            msg.__init_from_dict__(d)

        return msg

class ElectionStartMessage(ElectionMessage):
    def __init__(self, sender: str):
        super().__init__(ElectionMessageType.ElectionStart, sender)

class ElectionOkMessage(ElectionMessage):
    def __init__(self, sender: str):
        super().__init__(ElectionMessageType.ElectionOk, sender)

class IAmLeaderMessage(ElectionMessage):
    def __init__(self, sender: str):
        super().__init__(ElectionMessageType.IAmLeader, sender)

########################
# APPLICATION MESSAGES #
########################
class CommandType(Enum):
    Stop = 1
    Resume = 2
    JumpToTimestamp = 3
    Set = 4
    State = 5

class ApplicationMessage(BaseMessage):
    command_type: int

    def __init__(self, command_type: int):
        super().__init__(MessageTypes.ApplicationMessage)
        self.command_type = command_type

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.command_type = d["command_type"]

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d['command_type'] = self.command_type
        return d
    
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
        d = super().__dict__
        d["index"] = self.index
        return d

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
        d = super().__dict__
        d["destination_timestamp"] = self.destination_timestamp
        return d

class StateMessage(ApplicationMessage):
    def __init__(self, state: State):
        super().__init__(CommandType.State.value)
        self.state = state

    def __init_from_dict__(self, d: dict[str, any]):
        super().__init_from_dict__(d)
        self.state = State(**d["state"])

    @property
    def __dict__(self) -> dict[str, any]:
        d = super().__dict__
        d["state"] = self.state.__dict__
        return d
