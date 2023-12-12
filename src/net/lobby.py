import json
import log
import random
import threading
from dataclasses import dataclass
from net.backend import IpAddress, NetBackend, TcpBackend

from messages.messages import *

from event_manager.event_manager import EventManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from application.player import EpicMusicPlayer

_logger = log.getLogger(__name__)

@dataclass
class Peer:
    ip: str = ""
    port: int = 0
    name: str = ""
    is_leader: bool = True
    is_alive: bool = True
    id: int = 0

    @property
    def ip_address(self) -> IpAddress:
        return f"{self.ip}:{self.port}"

    def __str__(self) -> str:
        return self.name
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, Peer):
            return self.ip == __value.ip and self.port == __value.port
        elif isinstance(__value, IpAddress):
            return self.ip_address == __value
        return False
    
class NetLobby(EventManager):
    """
    A network lobby.
    """
    EVENT_MEMBERS_CHANGED = "members_changed"

    _APPLICATION_MESSAGE_TYPE = 'application' # typo
    _HEALTH_CHECK_EXPIRATION_TIMER = 5.0
    _HEALTH_CHECK_LEADER_ALIVE_TIMER = 8.0
    _ELECTION_EXPIRATION_TIMER = 5.0



    _port: int
    _backend: NetBackend

    _identity: IpAddress = None
    _leader: IpAddress = None
    _members: dict[IpAddress, Peer] = None

    _pending_leader_msgs: list = []

    _player: "EpicMusicPlayer"

    _election_ok_received: int
    _health_check_ack_received: int

    def __init__(self) -> None:
        super().__init__()
        self._register_event(self.EVENT_MEMBERS_CHANGED)

        self._port = 30000
        _logger.debug(f'Listening on port {self._port}')
        self._backend = TcpBackend(self._port)
        self._members = {}
        self._leader_health = True
        self._exit = False
        self._election_ok_received = False
        self._election_is_running = False
        self._health_check_loop_thread = threading.Thread(target=self._health_check_loop)

    def is_leader(self) -> bool:
        return self._identity == self._leader

    def send_to(self, name: IpAddress, msg) -> None:
        msg['identity'] = self._identity
        _logger.debug(f"Target: {name}   Message: {msg}")
        return self._backend.send(name, _write_message(msg))

    def send_to_leader(self, msg) -> None:
        msg['to_leader'] = True
        success = self.send_to(self._leader, msg)
        if not success:
            # Leader offline? Try to elect a new one
            _logger.warn('Leader unavailable')
            self._pending_leader_msgs.append(msg) # Send this when we have a leader
            self._start_leader_election()

    def broadcast(self, msg) -> None:
        if not self.is_leader():
            raise RuntimeError('only the leader can broadcast')
        for member in {**self._members}:
            if member == self._identity:
                continue
            success = self.send_to(member, msg)
            if not success:
                pass # TODO remove member?

    def register_player(self, player: "EpicMusicPlayer"):
        self._player = player
        self._player.lobby = self

    def remove_player(self):
        if self._player is not None:
            if self.is_leader():
                if len(self._members) > 1:
                    # This could be achieved better, but good for now
                    del self._members[self._identity]
                    address= random.choice(list(self._members.keys()))
                    self.send_to(address, {'type': 'leave', 'member_identity': self._identity})
            else:
                self.send_to_leader({'type': 'leave', 'member_identity': self._identity})

    def create_lobby(self, ip: str, port: int, name: str) -> None:
        """Starts a new lobby."""
        # Actual initialization happens when first node joins
        peer = Peer(ip, port, name, True, True, self._generate_random_id())
        self._leader = peer.ip_address
        self._identity = peer.ip_address
        self._members[self._identity] = peer
        self._health_check_loop_thread.start()
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        _logger.debug('Created a new lobby')

    def join_lobby(self, my_name: str, my_port: int, lobby_ip: str, lobby_port: int) -> None:
        """Attempts to join a lobby using name of one of its members."""
        lobby_address = f'{lobby_ip}:{lobby_port}'
        _logger.debug(f'Joining a lobby at {lobby_address}...')

        peer = Peer("", my_port, my_name, False, True)
        self._identity = peer.ip_address
        self._members[self._identity] = peer
        # Ask the given member to join the lobby
        self.send_to(lobby_address, {'type': 'request_join', 'name': my_name, 'target': lobby_address})

    def handle_msg(self):
        source, data = self._backend.receive()
        if source is None or data is None:
            return 
        msg = _read_message(data)
        _logger.debug(f'Received message from {msg["identity"]}: {msg}')

        if 'to_leader' in msg:
            if not self.is_leader():
                _logger.warning(f'Message is for the leader, but I\'m not the leader')
                return
            else:
                msg.pop('to_leader')

        self._process_message(source, msg)

    ####################
    #####   LOBBY  #####
    ####################
    def _process_message(self, source, msg):
        if not isinstance(msg, dict):
            _logger.warning('The message type is not a dictionary')
            return
        
        if 'type' not in msg:
            _logger.warning('Message has no key "type"')
            return

        process_method_name = f"_process_{msg['type']}"

        if hasattr(self, f"_process_{msg['type']}"):
            method = getattr(self, process_method_name)
            method(source, msg)
        else:
            _logger.warn(f'{type(self).__name__} has no method {process_method_name} to process received message')

    def _process_request_join(self, source, msg):
        # A node has requested to join the lobby
        if self.is_leader() and self._me.ip == "":
            self._update_me(msg['target'].split(':')[0])

        _logger.debug(f'Forwarding new member request to leader')
        ip = source.split(':')[0]
        port = msg['identity'].split(':')[1]
        self.send_to_leader({'type': 'request_new_member', 'name': msg['name'], 'member_identity': f"{ip}:{port}"})

    def _process_request_new_member(self, source, msg):
        # A lobby member has requested that another node is added to the lobby
        _logger.debug(f'Approving new member {msg["member_identity"]}')

        address = msg["member_identity"].split(":")

        # Tell everyone in the lobby about them
        self.broadcast({'type': 'new_member', 'name': msg['name'], 'member_identity': msg['member_identity']})
        
        self._members[msg["member_identity"]] = Peer(address[0], address[1], msg["name"], False, True, self._generate_random_id())

        # Tell them about the lobby
        self.send_to(msg["member_identity"], {
            'type': 'lobby_info',
            'member_identity': msg['member_identity'],
            'members': {address: member.__dict__ for address, member in self._members.items()}
        })

        self._send_player_state(msg["member_identity"])
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _process_lobby_info(self, source, msg):
        if self._me.ip == "":
            self._update_me(msg["member_identity"].split(':')[0])

        for ip_address, member in msg["members"].items():
            if ip_address != self._identity:
                self._members[ip_address] = Peer(**member)
                if self._members[ip_address].is_leader:
                    self._leader = ip_address
            else:
                self._me.id = member["id"]

        self._health_check_loop_thread.start()

        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        _logger.debug(f'Joined lobby, I am {self._identity}, with id {self._me.id} (leader: {self._leader})')

    def _process_new_member(self, source, msg):
        # Leader is telling us about the new member
        _logger.debug(f'New lobby member: {msg["identity"]}')
        address = msg["member_identity"].split(':')[0]
        self._members[msg["member_identity"]] = Peer(address[0], address[1], msg['name'], False, True)
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _process_leave(self, source, msg):
        if msg['member_identity'] in self._members:
            _logger.debug(f'{msg["member_identity"]} has left the lobby')

            if self.is_leader():
                del self._members[msg['identity']]
                self.broadcast({'type': 'leave', 'member_identity': msg['identity']})
            elif self._leader == msg['member_identity']:
                self._start_leader_election()
            else:
                del self._members[msg['member_identity']]

            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    ####################
    ### HEALTH CHECK ###
    ####################
    def _process_health_check(self, source, msg):
        self._members[msg['identity']].is_alive = True
        if not self.is_leader():
            self._leader_health = True
            self._send_health_check()

    def _health_check_loop(self):
        expiration_timer = None
        
        if self.is_leader():
            expiration_timer = threading.Timer(self._HEALTH_CHECK_EXPIRATION_TIMER, self._process_health_check_expired)
            self._send_health_check()
        else:
            expiration_timer = threading.Timer(self._HEALTH_CHECK_LEADER_ALIVE_TIMER, self._check_leader_health)
        
        expiration_timer.start()

        while not self._exit:
            if not expiration_timer.is_alive():
                if self.is_leader():
                    self._send_health_check()
                    expiration_timer = threading.Timer(self._HEALTH_CHECK_EXPIRATION_TIMER, self._process_health_check_expired)
                else:
                    expiration_timer = threading.Timer(self._HEALTH_CHECK_LEADER_ALIVE_TIMER, self._check_leader_health)

                expiration_timer.start()

        expiration_timer.cancel()

    def _check_leader_health(self):
        if not self._election_is_running and not self._leader_health and not self.is_leader():
            self.send_to(self._identity, {'type': 'election'})
        self._leader_health = False

    def _send_health_check(self):
        if self.is_leader():
            for address, member in self._members.copy().items():
                if address != self._identity:
                    member.is_alive = False
            self.broadcast({'type': 'health_check', 'identity': self._identity})
        else:
            self.send_to_leader({'type': 'health_check', 'identity': self._identity})

    def _health_check_expired(self):
        self.send_to(self._identity, {'type': 'health_check_expired'})

    def _process_health_check_expired(self):
        expired = False
        for address, member in self._members.copy().items():
            if not member.is_alive:
                del self._members[address]
                self.broadcast({'type': 'leave', 'member_identity': address})
                expired = True
                _logger.debug(f"Health check expired for {address}")
        if expired:
            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    ####################
    ##### ELECTION #####
    ####################
    def _process_election(self, source, msg):
        if msg["identity"] == self._identity:
            if not self.is_leader() and not self._election_is_running:
                self._start_leader_election()
        else:
            if self._members[msg["identity"]].id < self._me.id:
                self.send_to(msg["identity"], {'type': 'election_ok'})
                if not self.is_leader() and not self._election_is_running:
                    self._start_leader_election()

    def _process_election_ok(self, source, msg):
        self._election_ok_received = True

    def _process_i_am_leader(self, source, msg):
        # A new leader has appeared
        if self._leader in self._members:
            del self._members[self._leader]

        self._leader = msg["identity"]
        # Send messages that were waiting for leader election to finish
        # TODO this assumes that newly appointed leader will not IMMEDIATELY fail
        for msg in self._pending_leader_msgs:
            self.send_to_leader(msg)
        self._pending_leader_msgs = []
        self._leader_health = True
        self._election_is_running = False
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _start_leader_election(self):
        _logger.info(f"Starting a leader election")
        self._election_is_running = True
        del self._members[self._leader]
        has_greater = False
        for address, member in self._members.items():
            if member.id > self._me.id:
                self.send_to(address, {'type': 'election'})
                has_greater = True

        if has_greater:
            self._election_ok_received = False
            threading.Timer(self._ELECTION_EXPIRATION_TIMER, self._election_timer_expired).start()
        else:
            self._promote_to_leader()

    def _election_timer_expired(self):
        if not self._election_ok_received:
            self._promote_to_leader()

    def _process_application(self, source, msg):
        self._process_application_message(ApplicationMessage.from_dict(msg['message']))
    
    def _promote_to_leader(self):
        _logger.info(f"I am promoted to leader")
        self._leader = self._identity
        self._members[self._leader].is_leader = True
        self.broadcast({'type': 'i_am_leader'})
        self._election_is_running = False
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def shutdown(self) -> None:
        self._exit = True
        self._backend.shutdown()

    ###################
    ### APPLICATION ###
    ###################
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

    def _send_player_state(self, name: str):
        state = StateMessage(self._player.get_state())
        msg = self._create_application_message(state)
        self.send_to(name, msg)

    def _process_application_message(self, message: ApplicationMessage):
        _logger.debug(f"Received application message {type(message).__name__}: {message.__dict__}")

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

    def _update_me(self, ip: str):
        me = self._me
        me.ip = ip
        del self._members[self._identity]
        self._identity = me.ip_address
        self._members[self._identity] = me

        if me.is_leader:
            self._leader = self._identity

    @property
    def _me(self) -> Peer:
        return self._members[self._identity]

    def _create_application_message(cls, message: ApplicationMessage):
        return {'type': cls._APPLICATION_MESSAGE_TYPE, 'message': message.__dict__}

    def _generate_random_id(self) -> int:
        id = random.randint(-(2**31), 2**31 - 1)
        while any(member.id == id for member in self._members.values()):
            id = random.randint(-(2**31), 2**31 - 1)
        return id

def _write_message(msg) -> str:
    return json.dumps(msg)

def _read_message(data: str):
    return json.loads(data)