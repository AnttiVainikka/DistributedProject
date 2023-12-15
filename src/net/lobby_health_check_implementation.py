import threading

from net.base_lobby import BaseLobby
from net.lobby_message_implementation import LobbyMessageImplementation

from messages.messages import *

import log

_logger = log.getLogger(__name__)

class LobbyHealthCheckImplementation(BaseLobby):
    """
    Health Check Implementation for the BaseLobby.

    This class extends the BaseLobby and provides the Health Check implementation.
    It specifically implements the abstract methods related to health check, including:
    
        - _start_health_check
        - _stop_health_check
        - _process_health_check
    """
    # Time we wait on the leader for health acknowledgement
    _HEALTH_CHECK_EXPIRATION_TIMER = 5.0

    # Time we wait for leader health check message
    _HEALTH_CHECK_LEADER_ALIVE_TIMER = 8.0

    # The main health check loop thread
    _health_check_loop_thread: threading.Thread

    # Timer for waiting the health check
    _health_check_expiration_timer: threading.Timer

    # This can be used to stop the health check
    _is_health_check_running: bool

    def __init__(self):
        super().__init__()
        self._health_check_loop_thread = None
        self._health_check_expiration_timer = None
        self._is_health_check_running = False

    def _start_health_check(self):
        """
        Start the health check loop for the client within the lobby.

        This method is used to initiate the health check loop for the client within
        the lobby. For detailed information about the health check
        system, please refer to the documentation or the implementation.
        """
        self._stop_health_check()
        self._health_check_loop_thread = threading.Thread(target=self._health_check_loop)
        self._is_health_check_running = True
        self._health_check_loop_thread.start()

    def _stop_health_check(self):
        """
        Stop the health check main loop for the client within the lobby.

        This method is used to halt the health check main loop for the client within
        the lobby. It effectively stops the monitoring of the status and availability
        of lobby members.
        """
        self._is_health_check_running = False
        if self._health_check_loop_thread is not None:
            self._health_check_loop_thread.join()

    def _process_health_check(self, msg: HealthCheckMessage):
        """
        Process the received HealthCheckMessage within the lobby.

        This method is designed to handle the HealthCheckMessage, which is used for health
        monitoring within the lobby. For detailed information about the health check system,
        please refer to the documentation or the implementation.

        Parameters:
        - msg (HealthCheckMessage): The HealthCheckMessage received from another lobby member.
        """
        if msg.sender in self._members:
            self._members[msg.sender].is_alive = True
            if not self.is_leader():
                _logger.debug(f"Received health check from leader {self._leader_peer.name}/{self._leader_peer.ip_address}")
                self._send_health_check()
            else:
                _logger.debug(f"Received health check acknowledge from {self._members[msg.sender].name}/{self._members[msg.sender].ip_address}")

    def _health_check_loop(self):
        """
        Main health check loop for monitoring leader or member health.

        This method serves as the main health check loop, started on a separate thread.
        As a lobby member, it is used to monitor the health of the leader, while as a leader,
        it is used to monitor the health of the lobby members.
        """
        # Initiate the expiration timer
        self._health_check_expiration_timer = None
        if self.is_leader():
            self._health_check_expiration_timer = threading.Timer(self._HEALTH_CHECK_EXPIRATION_TIMER, self._process_leader_health_check_expired)
            self._send_health_check()
        else:
            self._leader_peer.is_alive = False
            self._health_check_expiration_timer = threading.Timer(self._HEALTH_CHECK_LEADER_ALIVE_TIMER, self._process_member_health_check_expired)
        
        # Start the timer
        self._health_check_expiration_timer.start()

        while self._is_health_check_running:
            # As soon as the expiration timer has expired we are starting a new one
            if not self._health_check_expiration_timer.is_alive():
                if self.is_leader():
                    self._send_health_check()
                    self._health_check_expiration_timer = threading.Timer(self._HEALTH_CHECK_EXPIRATION_TIMER, self._process_leader_health_check_expired)
                else:
                    self._leader_peer.is_alive = False
                    self._health_check_expiration_timer = threading.Timer(self._HEALTH_CHECK_LEADER_ALIVE_TIMER, self._process_member_health_check_expired)

                self._health_check_expiration_timer.start()

        self._health_check_expiration_timer.cancel()

    def _send_health_check(self):
        """
        Send a health check message to monitor leader or member health.

        This method is used to send a health check message. If the client is a lobby member,
        it sends the health check to the leader. If the client is the leader, it broadcasts
        the health check to all the members.
        """
        if self.is_leader():
            for address, member in self._members.copy().items():
                if address != self._identity:
                    member.is_alive = False
            _logger.debug(f"Broadcasting health check to members")
            self.broadcast(HealthCheckMessage(self._identity))
        else:
            _logger.debug(f"Sending health check acknowledge to leader {self._leader_peer.name}/{self._leader_peer.ip_address}")
            self.send_to(self._leader, HealthCheckMessage(self._identity))

    def _process_leader_health_check_expired(self):
        """
        Process leader health check timer expiration.

        This method is called on the leader when the timer to receive the health check
        acknowledgment from the members has expired. It allows the leader to handle the
        situation where members have not responded within the expected time.

        When a member has no responded within the expected time, it is immediately removed
        from the lobby.
        """
        for address, member in self._members.copy().items():
            if not member.is_alive:
                self.broadcast(MemberLeftMessage(self._identity, address))
                _logger.info(f"Member {member.name}/{member.ip_address} timeout")
                self._remove_member(member)
        
    def _process_member_health_check_expired(self):
        """
        Process member health check timer expiration.

        This method is called on the members when the timer to receive the health check from
        the leader has expired. If the leader didn't send a message within the expected time,
        it initiates a new leader election procedure.
        """
        if not self._leader_peer.is_alive:
            _logger.info(f"Leader {self._leader_peer.name}/{self._leader_peer.ip_address} timeout")
            self._start_leader_election()
