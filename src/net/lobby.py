import json
import log
import random
from net.backend import IpAddress, NetBackend, TcpBackend

_logger = log.getLogger(__name__)

class NetLobby:
    """
    A network lobby.
    """
    _port: int
    _backend: NetBackend

    _identity: IpAddress = None
    _leader: IpAddress = None
    _members: set[IpAddress] = None

    _pending_leader_msgs: list = []

    def __init__(self) -> None:
        self._port = random.randint(10000, 30000)
        _logger.info(f'Listening on port {self._port}')
        self._backend = TcpBackend(self._port)

    def create_lobby(self) -> None:
        """Starts a new lobby."""
        # Actual initialization happens when first node joins
        _logger.info('Created a new lobby')

    def join_lobby(self, name_of_member: IpAddress) -> None:
        """Attempts to join a lobby using name of one of its members."""
        _logger.info(f'Joining a lobby at {name_of_member}...')
        # Ask the given member to join the lobby
        self.send_to(name_of_member, {'type': 'request_join', 'return_port': self._port, 'target': name_of_member})

        # We'll hear back from the leader...
        _source, data = self._backend.receive()
        reply = _read_message(data)
        if reply['type'] != 'lobby_info':
            raise RuntimeError() # FIXME how to handle this?
        
        self._identity = f'{reply["identity"]}:{self._port}'
        self._leader = reply['leader']
        self._members = set(reply['members'])
        _logger.info(f'Joined lobby, I am {self._identity} (leader: {self._leader})')

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
            case 'i_am_leader':
                # A new leader has appeared
                self._leader = msg['name']
                # Send messages that were waiting for leader election to finish
                # TODO this assumes that newly appointed leader will not IMMEDIATELY fail
                for msg in self._pending_leader_msgs:
                    self.send_to_leader(msg)
                self._pending_leader_msgs = []

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
    
    def _start_leader_election(self):
        pass # TODO implement leader elections

def _write_message(msg) -> str:
    return json.dumps(msg)

def _read_message(data: str):
    return json.loads(data)