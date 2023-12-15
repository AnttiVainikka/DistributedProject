import random
import json
import threading

from abc import abstractmethod

from dataclasses import dataclass

from net.backend import IpAddress, NetBackend, TcpBackend

from event_manager.event_manager import EventManager
from event_manager.message_manager import MessageManager

from messages.messages import *

import log

_logger = log.getLogger(__name__)

@dataclass
class LobbyMessage:
    to_leader: bool
    message: BaseMessage

    @property
    def __dict__(self) -> dict[str, any]:
        return {
            'to_leader': self.to_leader,
            'message': self.message.__dict__
        }
    
    def from_dict(d: dict[str, any]) -> "LobbyMessage":
        return LobbyMessage(d["to_leader"], BaseMessage.from_dict(d["message"]))

@dataclass
class Peer:
    ip: str = ""
    port: int = 0
    name: str = ""
    id: int = 0
    is_leader: bool = True
    is_alive: bool = True

    @property
    def ip_address(self) -> IpAddress:
        return f"{self.ip}:{self.port}"

    def __str__(self) -> str:
        return f"{self.name}:{self.id}"
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, Peer):
            return self.ip == __value.ip and self.port == __value.port
        elif isinstance(__value, IpAddress):
            return self.ip_address == __value
        return False

class BaseLobby(EventManager, MessageManager):
    """
    Base class for hosting or joining another lobby.

    This class serves as an interface providing the fundamental structure and basic functionalities
    required for lobby operations. It is designed to be inherited by specific lobby implementations
    that extend its capabilities. Key functionalities such as message processing, leader election,
    and health checks are left to be implemented in their respective inherited classes.
    """

    # The event raised when the members of lobby have changed
    EVENT_MEMBERS_CHANGED = "members_changed"

    # The event raised when a member has joined the lobby
    EVENT_NEW_MEMBER = "new_member"

    # TCP backend used to send the messages
    _backend: NetBackend = None

    # Own identity
    _identity: IpAddress = ""

    #Leader identity
    _leader: IpAddress = ""

    # Members of the lobby
    _members: dict[IpAddress, Peer] = {}

    # The message handler thread is in charge of receiving and distributing the messages
    _message_handler_thread: threading.Thread
    
    # Used to end the message handle thread
    _exit: bool

    # In case the leader is not available we queue the messages until a new leader is selected
    _pending_leader_msgs: list = []

    def __init__(self):
        """
        Constructor for the BaseLobby class.

        This method initializes the BaseLobby instance. It registers its own events and message
        handlers, setting up the necessary infrastructure for lobby communication.
        """
        EventManager.__init__(self)
        MessageManager.__init__(self)

        self._message_handler_thread = threading.Thread(target=self._main_loop)
        self._exit = True

        # Register own events
        self._register_event(self.EVENT_MEMBERS_CHANGED)
        self._register_event(self.EVENT_NEW_MEMBER)

        # Register own message handlers
        self.connect_to_message(RequestJoinMessage, self._process_request_join)
        self.connect_to_message(RequestNewMemberMessage, self._process_request_new_member)
        self.connect_to_message(NewMemberMessage, self._process_new_member)
        self.connect_to_message(MemberAcceptMessage, self._process_member_accept)
        self.connect_to_message(LeaveMessage, self._process_leave)
        self.connect_to_message(MemberLeftMessage, self._process_member_left)
        self.connect_to_message(HealthCheckMessage, self._process_health_check)
        self.connect_to_message(ElectionStartMessage, self._process_election_start)
        self.connect_to_message(ElectionOkMessage, self._process_election_ok)
        self.connect_to_message(IAmLeaderMessage, self._process_i_am_leader)

    def stop(self):
        """
        Stops and finishes the lobby.

        This method should be called before ending the application to properly close the threads
        and perform any necessary cleanup tasks associated with the lobby. It ensures a graceful
        shutdown of the application by handling the necessary termination steps.
        """
        self._exit = True
        self._stop_health_check()
        self._message_handler_thread.join()

    def start(self):
        """
        Start the message handling thread of the lobby.

        This method initiates the message handling thread for the lobby,
        allowing it to propagate the incoming messages to the preinitialized callbacks.
        Call this method after initializing the lobby instance to begin message processing.

        Note:
        To the start the message handling the lobby needs to be hosted or joined to another lobby.
        """
        self._exit = False
        self._message_handler_thread.start()

    def create_lobby(self, ip: str, port: int, name: str) -> None:
        """
        Create and host a new lobby.

        This method initiates the creation of a new lobby, hosting it on the
        specified IP address and port number. The provided name parameter
        represents the name of the client who is hosting the lobby.

        Parameters:
        - ip (str): The IP address on which the lobby will be hosted.
        - port (int): The port number on which the lobby will be accessible.
        - name (str): The name of the client hosting the lobby.

        Note:
        The start() method needs to be called to start the message handling.
        """
        peer = Peer(ip, port, name, self._generate_random_id(), True, True)
        self._leader = peer.ip_address
        self._identity = peer.ip_address
        self._add_member(peer)

        self._backend = TcpBackend(port)

        self._start_health_check()

        _logger.info(f"Created lobby with peer {peer.__dict__}")

    def join_lobby(self, my_name: str, my_ip: str, my_port: int, lobby_ip: str, lobby_port: int) -> bool:
        """
        Join another lobby.

        This method sends a joining request to an existing lobby specified by the
        provided lobby_ip and lobby_port parameters. The request includes the name,
        IP, and port of the client wishing to join the lobby. The method returns
        True if the joining request was successful, and False otherwise.

        Parameters:
        - my_name (str): The name of the client wishing to join the lobby.
        - my_ip (str): The IP address of the client wishing to join.
        - my_port (int): The port number of the client wishing to join.
        - lobby_ip (str): The IP address of the lobby to join.
        - lobby_port (int): The port number of the lobby to join.

        Returns:
        - bool: True if the joining request was successful, False otherwise.

        Note:
        The start() method needs to be called to start the message handling.
        """
        lobby_address = f'{lobby_ip}:{lobby_port}'
        self._backend = TcpBackend(my_port)

        # Create myself
        me = Peer(my_ip, my_port, my_name, -1, False, True)
        self._identity = me.ip_address
        self._add_member(me)

        # Ask the given member to join the lobby
        _logger.info(f'Joining a lobby at {lobby_address}...')
        return self.send_to(lobby_address, RequestJoinMessage(self._identity, lobby_address, my_name))

    def leave_lobby(self):
        """
        Leave the lobby.

        This method is used to gracefully exit the lobby. If the client initiating
        the leave operation is the leader, the method selects a random member and
        requests them to initiate a new leader election. If the client is not the
        leader, it sends a leave message to the current leader, notifying them of
        the departure.
        """
        if self.is_leader():
            if len(self._members) > 1:
                del self._members[self._identity]
                address= random.choice(list(self._members.keys()))
                self.send_to(address, LeaveMessage(self._identity))
        else:
            self.send_to(self._leader, LeaveMessage(self._identity))

    def broadcast(self, msg: BaseMessage) -> None:
        """
        Broadcast a message to all lobby members.

        This method sends the provided message to all members within the lobby.
        The broadcasting functionality is restricted to the leader; therefore,
        only the leader has the authority to send messages to all members.

        Parameters:
        - msg (BaseMessage): The message to be broadcasted to all members.
        """
        if not self.is_leader():
            raise RuntimeError('only the leader can broadcast')
        
        unavailable_members = []

        for address, member in self._members.items():
            if address == self._identity:
                continue

            success = self.send_to(address, msg)
            if not success:
                unavailable_members.append(member)
                
        self._remove_members(unavailable_members)

    def send_to(self, target: IpAddress, msg: BaseMessage) -> None:
        """
        Send a message to a specific lobby member.

        This method allows a client, typically a lobby member, to send a message
        to a specific target member within the lobby. While it is possible to
        send messages to any member, it is generally recommended to communicate
        with the leader for coordination purposes.

        Parameters:
        - target (IpAddress): The IP address of the target member combined with port.
        - msg (BaseMessage): The message to be sent to the target member.
        """
        message = LobbyMessage(target == self._leader, msg)
        _logger.debug(f"Sending message to {target}: {msg.__dict__}")

        success = self._backend.send(target, _write_message(message.__dict__))
        if not success and target == self._leader:
            self._pending_leader_msgs.append(msg) # Send this when we have a leader 
        return success

    def send_to_leader(self, msg: BaseMessage) -> None:
        """
        Send a message directly to the lobby leader.

        This method allows a client to send a message directly to the lobby leader.
        It facilitates direct communication with the leader for coordination or
        specific requests.

        Parameters:
        - msg (BaseMessage): The message to be sent to the lobby leader.
        """
        self.send_to(self._leader, msg)

    def is_leader(self) -> bool:
        """
        Check if the client is the leader of the lobby.

        This method returns True if the client is currently the leader of the lobby,
        indicating that they have leadership responsibilities. It returns False if
        the client is not the leader.

        Returns:
        - bool: True if the client is the leader, False otherwise.
        """
        return self._identity == self._leader

    @property
    def _me(self) -> Peer | None:
        """
        Retrieve the client's own peer object.

        This returns the client's own peer object if it exists, or None
        if the peer object is not available. The peer object typically contains
        information such as the client's name, IP address, and port number.

        Returns:
        - Union[Peer, None]: The client's own peer object if available, or None.
        """
        if self._identity in self._members:
            return self._members[self._identity]
        else:
            return None
    
    @property
    def _leader_peer(self) -> Peer | None:
        """
        Retrieve the leader's peer object if available.

        This method returns the peer object of the lobby leader if it is available,
        or None if the leader's peer information is not currently accessible.

        Returns:
        - Union[Peer, None]: The leader's peer object if available, or None.
        """
        if self._leader in self._members:
            return self._members[self._leader]
        else:
            return None

    def _main_loop(self):
        """
        Main loop for lobby communication.

        This method serves as the main loop for the lobby's communication thread.
        It is started on a separate thread and is responsible for receiving messages
        from other lobby members and delegating them to preconfigured handlers.
        """
        # Wait for backend initialization
        while not self._exit and self._backend == None:
            pass

        while not self._exit:
            source, data = self._backend.receive()

            # Timeout occured
            if source is None or data is None:
                continue
        
            msg: LobbyMessage = LobbyMessage.from_dict(_read_message(data))

            # Don't process leader message if I'm not the leader
            if msg.to_leader and not self.is_leader():
                _logger.warning(f'Received message for the leader, but I\'m not the leader')
                continue

            _logger.debug(f"Received {type(msg.message).__name__}: {msg.message.__dict__}")
            self._call_message_handler(type(msg.message), msg.message)

    def _add_member(self, peer: Peer):
        """
        Add a new peer member to the lobby.

        This method is used to add a new peer member to the lobby. After adding the member,
        it raises a members changed event, indicating that the lobby's member list has been
        updated.

        Parameters:
        - peer (Peer): The peer object representing the new lobby member.
        """
        member_identity = peer.ip_address
        if member_identity not in self._members:
            self._members[member_identity] = peer
            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        else:
            _logger.warn(f"Tried to add member who is already in the list: {peer.__dict__}")

    def _remove_member(self, peer: Peer):
        """
        Remove a peer member from the lobby.

        This method is used to remove an existing peer member from the lobby. After removing
        the member, it raises a members changed event, indicating that the lobby's member list
        has been updated.

        Parameters:
        - peer (Peer): The peer object representing the lobby member to be removed.
        """
        member_identity = peer.ip_address
        if member_identity in self._members:
            del self._members[member_identity]
            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        else:
            _logger.warn(f"Tried to remove member who is not in the list: {peer.__dict__}")

    def _remove_members(self, peers: list[Peer]):
        """
        Remove multiple peer members from the lobby.

        This method is used to remove multiple existing peer members from the lobby. Instead
        of raising multiple events for each removal, it raises a single members changed event
        after removing all specified members.

        Parameters:
        - peers (list[Peer]): The list of peer objects representing the lobby members to be removed.
        """
        member_removed = False
        for member in peers:
            member_identity = member.ip_address
            if member_identity in self._members:
                del self._members[member_identity]
                member_removed = True
            else:
                _logger.warn(f"Tried to remove member who is not in the list: {member.__dict__}")

        if member_removed:
            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _generate_random_id(self) -> int:
        """
        Generate a new unique ID for a lobby member.

        This method is used by the lobby leader to generate a new unique ID for a member
        who has just joined the lobby. The leader generates the ID, sends it back to the
        joining member, and broadcasts it to all members in the lobby. The ID is used for
        the bully leader election algorithm.

        Returns:
        - int: A new unique ID for a lobby member.
        """
        id = random.randint(-(2**31), 2**31 - 1)
        while any(member.id == id for member in self._members.values()):
            id = random.randint(-(2**31), 2**31 - 1)
        return id

    @abstractmethod
    def _start_health_check(self):
        """
        Start the health check loop for the client within the lobby.

        This method is used to initiate the health check loop for the client within
        the lobby. For detailed information about the health check
        system, please refer to the documentation or the implementation.
        """
        pass

    @abstractmethod
    def _stop_health_check(self):
        """
        Stop the health check main loop for the client within the lobby.

        This method is used to halt the health check main loop for the client within
        the lobby. It effectively stops the monitoring of the status and availability
        of lobby members.
        """
        pass

    @abstractmethod
    def _start_leader_election(self):
        """
        Start the bully leader election procedure within the lobby.

        This method initiates the bully leader election procedure within the lobby.
        For detailed information about the leader election system, including the
        implementation details, please refer to the corresponding documentation.
        """
        pass

    @abstractmethod
    def _process_request_join(self, msg: RequestJoinMessage):
        """
        Process the received RequestJoinMessage within the lobby.

        This method is responsible for processing the received RequestJoinMessage within
        the lobby. When a client wants to join the lobby, it sends this message. If the
        leader receives this message, it is immediately processed. If a non-leader member
        receives it, the message is propagated to the leader for further processing.

        Parameters:
        - msg (RequestJoinMessage): The RequestJoinMessage received from a client.
        """
        pass

    @abstractmethod
    def _process_request_new_member(self, msg: RequestNewMemberMessage):
        """
        Process the received RequestNewMemberMessage within the lobby.

        This method is specifically designed to handle the RequestNewMemberMessage, which
        can only be received by the leader. The RequestNewMemberMessage is sent by another
        lobby member when that member receives a RequestJoinMessage and propagates it to the leader.

        Parameters:
        - msg (RequestNewMemberMessage): The RequestNewMemberMessage received from another lobby member.
        """
        pass

    @abstractmethod
    def _process_new_member(self, msg: NewMemberMessage):
        """
        Process the received NewMemberMessage within the lobby.

        This method is responsible for handling the NewMemberMessage, which is sent by the leader
        to all members of the lobby. The purpose of this message is to notify all members that a
        new member has successfully joined the lobby.

        Parameters:
        - msg (NewMemberMessage): The NewMemberMessage received from the lobby leader.
        """
        pass

    @abstractmethod
    def _process_member_accept(self, msg: MemberAcceptMessage):
        """
        Process the received MemberAcceptMessage within the lobby.

        This method is responsible for handling the MemberAcceptMessage, which is sent to a
        client after requesting to join the lobby. The MemberAcceptMessage contains the necessary
        information for the client to initialize itself within the lobby.

        Parameters:
        - msg (MemberAcceptMessage): The MemberAcceptMessage received by a joining client.
        """
        pass

    @abstractmethod
    def _process_leave(self, msg: LeaveMessage):
        """
        Process the received LeaveMessage within the lobby.

        This method handles the LeaveMessage, which can be initiated by either the leader or a
        member when they decide to leave the lobby. If the leader receives this message, it
        immediately removes the client from the lobby and broadcasts the leaving information to
        all remaining members. If a member receives this message from the leader, it initiates
        a leader election procedure within the lobby.

        Parameters:
        - msg (LeaveMessage): The LeaveMessage received from a client.
        """
        pass

    @abstractmethod
    def _process_member_left(self, msg: MemberLeftMessage):
        """
        Process the received MemberLeftMessage within the lobby.

        This method handles the MemberLeftMessage, which is received from the leader when a
        member has just left the lobby. The purpose of this message is to notify all members
        about the departure of a specific member.

        Parameters:
        - msg (MemberLeftMessage): The MemberLeftMessage received from the lobby leader.
        """
        pass
    
    @abstractmethod
    def _process_health_check(self, msg: HealthCheckMessage):
        """
        Process the received HealthCheckMessage within the lobby.

        This method is designed to handle the HealthCheckMessage, which is used for health
        monitoring within the lobby. For detailed information about the health check system,
        please refer to the documentation or the implementation.

        Parameters:
        - msg (HealthCheckMessage): The HealthCheckMessage received from another lobby member.
        """
        pass

    @abstractmethod
    def _process_election_start(self, msg: ElectionStartMessage):
        """
        Process the received ElectionStartMessage within the lobby.

        This method handles the ElectionStartMessage, which is received to initiate the leader
        election procedure for the client. For detailed information about the leader election
        system, please refer to the documentation or the implementation details.

        Parameters:
        - msg (ElectionStartMessage): The ElectionStartMessage received to initiate leader election.
        """
        pass

    @abstractmethod
    def _process_election_ok(self, msg: ElectionOkMessage):
        """
        Process the received ElectionOkMessage within the lobby.

        This method handles the ElectionOkMessage.
        For detailed information about the leader election system, please refer to
        the documentation or the implementation details.

        Parameters:
        - msg (ElectionOkMessage): The received ElectionOkMessage.
        """
        pass

    @abstractmethod
    def _process_i_am_leader(self, msg: IAmLeaderMessage):
        """
        Process the received IAmLeaderMessage within the lobby.

        This method handles the IAmLeaderMessage, which is sent by a new leader when it
        has been promoted within the lobby.

        Parameters:
        - msg (IAmLeaderMessage): The IAmLeaderMessage received from the new lobby leader.
        """
        pass

def _write_message(msg) -> str:
    return json.dumps(msg)

def _read_message(data: str):
    return json.loads(data)
