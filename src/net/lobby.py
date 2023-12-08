import base64
import json
import log
import random
import pickle
from net.backend import IpAddress, NetBackend, TcpBackend

from messages.messages import *

from event_manager.event_manager import EventManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from application.player import EpicMusicPlayer

_logger = log.getLogger(__name__)

class NetLobby(EventManager):
    """
    A network lobby.
    """
    EVENT_MEMBERS_CHANGED = "members_changed"
    
    _APPLICATION_MESSAGE_TYPE = 'application' # typo

    _port: int
    _backend: NetBackend

    _identity: IpAddress = None
    _leader: IpAddress = None
    _members: set[IpAddress] = None

    _pending_leader_msgs: list = []

    _player: "EpicMusicPlayer"

    def __init__(self) -> None:
        super().__init__()
        self._register_event(self.EVENT_MEMBERS_CHANGED)

        self._port = random.randint(10000, 30000)
        _logger.info(f'Listening on port {self._port}')
        self._backend = TcpBackend(self._port)
        self._members = []

    def register_player(self, player: "EpicMusicPlayer"):
        self._player = player
        self._player.lobby = self

    def remove_player(self):
        if self._player is not None:
            if self.is_leader():
                pass # TODO: Send a leader election initiation and then leave or just leave idk
            else:
                pass # TODO: Send leave message to leader

    def create_lobby(self) -> None:
        """Starts a new lobby."""
        # Actual initialization happens when first node joins
        _logger.info('Created a new lobby')

    def join_lobby(self, name_of_member: IpAddress) -> None:
        """Attempts to join a lobby using name of one of its members."""
        _logger.info(f'Joining a lobby at {name_of_member}...')
        # Ask the given member to join the lobby
        self.send_to(name_of_member, {'type': 'request_join', 'return_port': self._port, 'target': name_of_member})

    def handle_msg(self):
        source, data = self._backend.receive()
        msg = _read_message(data)
        _logger.info(f'Received message: {msg}')

        if 'to_leader' in msg and not self.is_leader():
            raise RuntimeError('not a leader') # TODO handle this by redirecting to leader?

        match msg['type']:
            case 'request_join':
                # A node has requested to join the lobby
                if self._identity == None:
                    # This is the first node joining this lobby -> we are the leader
                    self._identity = msg['target'] # Out public IP address is now known
                    self._leader = self._identity
                    self._members = set([self._identity])
                    _logger.info(f'Initialized lobby, I am leader {self._identity}')
                _logger.info(f'Forwarding new member request to leader')
                self.send_to_leader({'type': 'request_new_member', 'port': msg['return_port'], 'identity': source.split(':')[0]})
            case 'request_new_member':
                # A lobby member has requested that another node is added to the lobby
                name = f'{msg["identity"]}:{msg["port"]}'
                _logger.info(f'Approving new member {name}')
                self._members.add(name)
                # Tell them about the lobby
                self.send_to(name, {
                    'type': 'lobby_info',
                    'identity': msg['identity'],
                    'leader': self._leader,
                    'members': list(self._members)
                    # TODO currently playing music?
                })
                # Tell everyone in the lobby about them
                self.broadcast({'type': 'new_member', 'name': name})
            case 'new_member':
                # Leader is telling us about the new member
                _logger.info(f'New lobby member: {msg["name"]}')
                self._members.add(msg['name'])
                self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
            case 'i_am_leader':
                # A new leader has appeared
                self._leader = msg['name']
                # Send messages that were waiting for leader election to finish
                # TODO this assumes that newly appointed leader will not IMMEDIATELY fail
                for msg in self._pending_leader_msgs:
                    self.send_to_leader(msg)
                self._pending_leader_msgs = []
            case 'lobby_info':
                self._identity = f'{msg["identity"]}:{self._port}'
                self._leader = msg['leader']
                self._members = set(msg['members'])
                _logger.info(f'Joined lobby, I am {self._identity} (leader: {self._leader})')
            case 'start_election':
                #TODO start an election for a new leader
                pass
            case 'election_OK':
                #TODO ACK ongoing election, inform nodes with higher ID about the election
                pass
            case 'audio_file':
                #TODO send audio file to a member
                pass
            case 'status_ready':
                #TODO audio downloaded and ready to play
                pass
            case 'current_status':
                #TODO send current timestamp and playing/paused status to member
                pass
            case 'health_check':
                #TODO check client responsiveness
                pass
            case self._APPLICATION_MESSAGE_TYPE:
                self._process_application_message(pickle.loads(base64.b64decode(msg['message'])))

    def is_leader(self) -> bool:
        return self._identity == self._leader

    def send_to(self, name: IpAddress, msg) -> None:
        return self._backend.send(name, _write_message(msg))

    def send_to_leader(self, msg) -> None:
        msg['to_leader'] = True
        success = self.send_to(self._leader, msg)
        if not success:
            # Leader offline? Try to elect a new one
            _logger.warn('Leader unavailable, starting election...')
            self._pending_leader_msgs.append(msg) # Send this when we have a leader
            self._start_leader_election()

    def broadcast(self, msg) -> None:
        if not self.is_leader():
            raise RuntimeError('only the leader can broadcast')
        for member in self._members:
            if member == self._identity:
                continue
            success = self.send_to(member, msg)
            if not success:
                pass # TODO remove member?
    
    def application_request(self, message: ApplicationMessage):
        print('app_request', self.is_leader())
        if self.is_leader():
            self.broadcast(self._create_application_message(message))
            self._execute_application_message(message)
        else:
            self.send_to_leader(self._create_application_message(message))

    def request_stop(self, current_timestamp: int):
        self.application_request(StopMessage(current_timestamp))

    def request_resume(self, current_timestamp: int):
        print('request_resume')
        self.application_request(ResumeMessage(current_timestamp))

    def request_jump_to_timestamp(self, current_timestamp: int, destination_timestamp: int):
        self.application_request(JumpToTimestampMessage(current_timestamp, destination_timestamp))

    def request_skip(self, current_timestamp: int):
        self.application_request(SkipMessage(current_timestamp))

    def shutdown(self) -> None:
        self._backend.shutdown()

    def _start_leader_election(self):
        pass # TODO implement leader elections

    def _process_application_message(self, message: ApplicationMessage):
        _logger.info(f"Received application message {type(message).__name__}: {message.__dict__}")

        if self._check_application_message(message):
            if self.is_leader():
                self.broadcast(self._create_application_message(message))
            self._execute_application_message(message)

    def _check_application_message(self, message: ApplicationMessage) -> bool:
        match message.command_type:
            case CommandType.Stop.value:
                return not self._player.pause
            
            case CommandType.Resume.value:
                return self._player.pause

            case CommandType.JumpToTimestamp.value:
                return True

            case CommandType.Skip.value:
                return True

    def _execute_application_message(self, message: ApplicationMessage):
        match message.command_type:
            case CommandType.Stop.value:
                self._player.do_pause()
            
            case CommandType.Resume.value:
                self._player.play()

            case CommandType.JumpToTimestamp.value:
                pass # TODO: 

            case CommandType.Skip.value:
                self._player.do_skip()

    def _create_application_message(cls, message: ApplicationMessage):
        return {'type': cls._APPLICATION_MESSAGE_TYPE, 'message': base64.b64encode(pickle.dumps(message)).decode('utf-8')}

def _write_message(msg) -> str:
    return json.dumps(msg)

def _read_message(data: str):
    return json.loads(data)