import base64
import json
import log
import random
import pickle
import time
import threading
from threading import Event
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

    _election_ok_received: int
    _health_check_ack_received: int

    def __init__(self) -> None:
        super().__init__()
        self._register_event(self.EVENT_MEMBERS_CHANGED)

        self._port = 30000
        _logger.info(f'Listening on port {self._port}')
        self._backend = TcpBackend(self._port)
        self._members = []

        self._election_ok_received = False
        self._health_check_ack_received = False

    def register_player(self, player: "EpicMusicPlayer"):
        self._player = player
        self._player.lobby = self

    def remove_player(self):
        if self._player is not None:
            if self.is_leader():
                pass # TODO: Send a leader election initiation and then leave or just leave idk
            else:
                self.send_to_leader({'type': 'leave', 'name': self._identity})

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
        if source is None or data is None:
            return 
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
                    self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
                    _logger.info(f'Initialized lobby, I am leader {self._identity}')
                _logger.info(f'Forwarding new member request to leader')
                self.send_to_leader({'type': 'request_new_member', 'port': msg['return_port'], 'identity': source.split(':')[0]})
            case 'request_new_member':
                # A lobby member has requested that another node is added to the lobby
                name = f'{msg["identity"]}:{msg["port"]}'
                _logger.info(f'Approving new member {name}')
                self._members.add(name)
                self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
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
                self._send_player_state(name)
            case 'new_member':
                # Leader is telling us about the new member
                _logger.info(f'New lobby member: {msg["name"]}')
                self._members.add(msg['name'])
                self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
                self._members.remove(msg['name'])
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
                self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
                _logger.info(f'Joined lobby, I am {self._identity} (leader: {self._leader})')
            case 'start_election':
                # An election is underway
                _logger.info(f'I, {self._identity} received an election message from {msg["name"]}')
                self.send_to(msg["name"], {'type': 'election_OK', 'return_port': self._port, 'target': msg["name"]})
                self._start_leader_election()
            case 'election_OK':
                # withdraw from election and wait for new leader
                self._election_ok_received = True
                _logger.info(f'I, {self._identity} received a election OK from {msg["name"]}')
            case 'health_check':
                _logger.info(f'I, {self._identity} received a health check from {msg["name"]}')
                self.send_to(msg["name"], {'type': 'health_check_ack', 'return_port': self._port, 'target': msg["name"]})
            case 'health_check_ack':
                # confirm health check
                self._health_check_ack_received = True
                _logger.info(f'I, {self._identity} received a health check ACK from {msg["name"]}')
            case 'leave':
                if msg['name'] in self._members:
                    self._members.remove(msg['name'])
                if self.is_leader():
                    msg.pop('to_leader')
                    self.broadcast(msg)
                self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
                _logger.info(f'{self._identity} has left the lobby')
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
        if self.is_leader():
            self.broadcast(self._create_application_message(message))
            self._execute_application_message(message)
        else:
            self.send_to_leader(self._create_application_message(message))

    def request_stop(self):
        self.application_request(StopMessage())

    def request_resume(self):
        self.application_request(ResumeMessage())

    def request_jump_to_timestamp(self, destination_timestamp: int):
        self.application_request(JumpToTimestampMessage(destination_timestamp))

    def request_set(self, index: int):
        self.application_request(SetMessage(index))

    def shutdown(self) -> None:
        self._backend.shutdown()

    def _start_leader_election(self):
        for member in self._members:
                if hash(self._identity) < hash(member): # IP address equals ID?
                    self.send_to(member, {'type': 'start_election', 'return_port': self._port, 'target': member})
        waiting_thread = threading.Thread(target=self._wait_for_election_ok, args=(self))
        waiting_thread.start()

    def _send_health_check(self, target): #how often should this be sent?
        self.send_to(target, {'type': 'health_check', 'return_port': self._port, 'target': target})
        waiting_thread = threading.Thread(target=self._wait_for_health_check_response, args=(self, target))
        waiting_thread.start()

    def _wait_for_election_ok(self):
        time.sleep(2)
        if not self._election_ok_received: # If no response is received
            self._leader = self._identity
            self.broadcast({'type': 'i_am_leader', 'name': self._identity})
    
    def _wait_for_health_check_response(self, target):
        time.sleep(2)
        if not self._health_check_ack_received: # If no response is received
            if self._leader == target:
                    self._start_leader_election()
            else: # so what?
                pass


    def _send_player_state(self, name: str):
        state = StateMessage(self._player.get_state())
        msg = self._create_application_message(state)
        self.send_to(name, msg)

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

            case CommandType.Set.value:
                return True
            
            case CommandType.State.value:
                return True

    def _execute_application_message(self, message: ApplicationMessage):
        match message.command_type:
            case CommandType.Stop.value:
                self._player.do_pause()
            
            case CommandType.Resume.value:
                self._player.play()

            case CommandType.JumpToTimestamp.value:
                self._player.skip_to_timestamp(message.destination_timestamp)

            case CommandType.Set.value:
                self._player.set_song(message.index)

            case CommandType.State.value:
                self._player.set_state(message.state)

    def _create_application_message(cls, message: ApplicationMessage):
        return {'type': cls._APPLICATION_MESSAGE_TYPE, 'message': base64.b64encode(pickle.dumps(message)).decode('utf-8')}

def _write_message(msg) -> str:
    return json.dumps(msg)

def _read_message(data: str):
    return json.loads(data)