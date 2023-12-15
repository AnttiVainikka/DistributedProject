import threading

from net.base_lobby import BaseLobby
from net.lobby_health_check_implementation import LobbyHealthCheckImplementation

from messages.messages import *

import log

_logger = log.getLogger(__name__)

class LobbyLeaderElectionImplementation(BaseLobby):
    """
    Leader Election Implementation for the BaseLobby.

    This class extends the BaseLobby and provides the Leader Election implementation.
    It specifically implements the abstract methods related to leader election, including:
    
        - _start_leader_election
        - _process_election_start
        - _process_election_ok
        - _process_i_am_leader
    """

    # Time we wait for election ok message
    _ELECTION_EXPIRATION_TIMER = 5.0

    # Timer for waiting election ok message
    _election_timer: threading.Timer

    # Used to monitor whether a leader election is in progress
    _leader_election_in_progress: bool

    # Used to check whether an ElectionOk message has been received after the election has started
    _ok_received: bool

    def __init__(self):
        super().__init__()

        self._election_timer = None
        self._leader_election_in_progress = False
        self._ok_received = False

    def _start_leader_election(self):
        """
        Start the bully leader election procedure within the lobby.

        This method initiates the bully leader election procedure within the lobby.
        For detailed information about the leader election system, including the
        implementation details, please refer to the corresponding documentation.
        """
        self._leader_election_in_progress = True

        # The health check will be stopped while the leader election takes place
        self._stop_health_check()
        self._leader_peer.is_alive = False
        _logger.info(f"Starting a leader election")

        # If the current leader is still in our member list, we remove it
        if self._leader in self._members:
            del self._members[self._leader]

        # Iterate over all the members and send an ElectionStart message to those, whose id is greater
        has_greater = False
        for address, member in self._members.items():
            if member.id > self._me.id:
                self._ok_received = False
                self.send_to(address, ElectionStartMessage(self._identity))
                has_greater = True

        # If there are members with greater id, we are waiting for ElectionOk message
        if has_greater:
            self._election_timer = threading.Timer(self._ELECTION_EXPIRATION_TIMER, self._election_timer_expired)
            self._election_timer.start()
        else:
            # If there is no member with greater id, this client is immediately promoted to leader
            self._promote_to_leader()

    def _process_election_start(self, msg: ElectionStartMessage):
        """
        Process the received ElectionStartMessage within the lobby.

        This method handles the ElectionStartMessage, which is received to initiate the leader
        election procedure for the client. For detailed information about the leader election
        system, please refer to the documentation or the implementation details.

        Parameters:
        - msg (ElectionStartMessage): The ElectionStartMessage received to initiate leader election.
        """
        if msg.sender in self._members:
            if self.is_leader():
                self.send_to(msg.sender, ElectionOkMessage(self._identity))
            elif self._me.id > self._members[msg.sender].id:
                self.send_to(msg.sender, ElectionOkMessage(self._identity))
                if not self._leader_election_in_progress:
                    self._start_leader_election()

    def _process_election_ok(self, msg: ElectionOkMessage):
        """
        Process the received ElectionOkMessage within the lobby.

        This method handles the ElectionOkMessage.
        For detailed information about the leader election system, please refer to
        the documentation or the implementation details.

        Parameters:
        - msg (ElectionOkMessage): The received ElectionOkMessage.
        """
        self._ok_received = True
        if self._election_timer is not None:
            self._election_timer.cancel()

    def _process_i_am_leader(self, msg: IAmLeaderMessage):
        """
        Process the received IAmLeaderMessage within the lobby.

        This method handles the IAmLeaderMessage, which is sent by a new leader when it
        has been promoted within the lobby.

        Parameters:
        - msg (IAmLeaderMessage): The IAmLeaderMessage received from the new lobby leader.
        """
        # A new leader has appeared
        if msg.sender in self._members and msg.sender != self._leader:
            # Stop election timer if it is running
            if self._election_timer is not None:
                self._election_timer.cancel()

            if self.is_leader():
                # If this client is the leader and received a new leader message from a member with greater id
                # it simply yields and give it the role
                if self._members[msg.sender].id > self._me.id:
                    self._leader = msg.sender
                    self._members[self._leader].is_leader = True
                    self._members[self._identity].is_leader = False
                else:
                    # This cannot really happen, just be sure a message is printed
                    _logger.fatal(f"{self._members[msg.sender]}/{self._members[msg.sender].ip_address} also promoted itself to leader, but its id is lesser than mine")
            else:
                # If this new leader is caused by the previous leader's timeout and the previous leader is
                # still in the member list, it must be removed
                if self._leader_peer is not None and (not self._leader_peer.is_alive or not self._leader_election_in_progress):
                    del self._members[self._leader]

                self._leader = msg.sender
                self._members[self._leader].is_leader = True
                self._members[self._leader].is_alive = True

                # Send the pending messages to the new leader
                for msg in self._pending_leader_msgs:
                    self.send_to(self._leader, msg)
                self._pending_leader_msgs = []

            # Restart health check
            self._leader_election_in_progress = False
            self._start_health_check()
            self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _election_timer_expired(self):
        """
        Process leader election timer expiration.

        This method is called when the timer for receiving leader election OK messages has expired.
        """
        if not self._ok_received:
            self._promote_to_leader()
    
    def _promote_to_leader(self):
        """
        Promote the client to the leader role.

        This method is called to promote the client to the leader role. It broadcasts this information
        to all members and restarts the health check for the new leader.
        """
        self._leader = self._identity
        self._members[self._leader].is_leader = True
        self.broadcast(IAmLeaderMessage(self._identity))
        self._start_health_check()
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        _logger.info(f"I am promoted to leader")
