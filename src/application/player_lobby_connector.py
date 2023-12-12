from net.lobby import NetLobby

from messages.messages import *

import log

_logger = log.getLogger(__name__)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.player import EpicMusicPlayer

class PlayerLobbyConnector:
    """
    Class for maintaining the connection and communication between the lobby and a media player.

    The PlayerLobbyConnector class is designed to manage the connection and communication between a lobby (e.g., NetLobby)
    and a media player (e.g., EpicMusicPlayer). It facilitates interactions such as sending requests, receiving updates,
    and ensuring seamless communication between the lobby and the media player.
    """

    # The player that is connected to a lobby
    _player: "EpicMusicPlayer"

    # The lobby the player is connected to
    _lobby: NetLobby

    def __init__(self, player: "EpicMusicPlayer", lobby: NetLobby):
        """
        Constructor for the PlayerLobbyConnector class.

        This method initializes the PlayerLobbyConnector by connecting the necessary events and message handlers between
        the provided media player (e.g., EpicMusicPlayer) and lobby (e.g., NetLobby).

        Parameters:
        - player (EpicMusicPlayer): The media player instance to connect.
        - lobby (NetLobby): The lobby instance to connect.
        """
        self._player = player
        self._lobby = lobby

        self._lobby.connect_to_event(self._lobby.EVENT_NEW_MEMBER, self._send_player_state)

        self._lobby.connect_to_message(StopMessage, self._process_stop_message)
        self._lobby.connect_to_message(ResumeMessage, self._process_resume_message)
        self._lobby.connect_to_message(SetMessage, self._process_set_message)
        self._lobby.connect_to_message(JumpToTimestampMessage, self._process_jump_to_timestamp_message)
        self._lobby.connect_to_message(StateMessage, self._process_state_message)

    @property
    def player(self) -> "EpicMusicPlayer":
        """
        Get the media player in the connection.

        This method returns the media player instance that is part of the PlayerLobbyConnector.

        Returns:
        - EpicMusicPlayer: The media player instance.
        """
        return self._player
    
    @property
    def lobby(self) -> NetLobby:
        """
        Get the lobby in the connection.

        This method returns the lobby instance that is part of the PlayerLobbyConnector.

        Returns:
        - NetLobby: The lobby instance.
        """
        return self._lobby

    def application_request(self, message: ApplicationMessage):
        """
        Propagate a general application request to the lobby.

        This method sends a general application request to the lobby, propagating the specified ApplicationMessage to all members.

        Parameters:
        - message (ApplicationMessage): The application message to be sent to the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
            self._lobby.send_to_leader(message)
        else:
            self._lobby.send_to_leader(message)

    def request_stop(self):
        """
        Request a stop from the lobby.

        This method sends a request to the lobby, asking other members to stop the current media.
        """
        self.application_request(StopMessage())

    def request_resume(self):
        """
        Request a resume from the lobby.

        This method sends a resume to the lobby, asking other members to resume the current media.
        """
        self.application_request(ResumeMessage())

    def request_jump_to_timestamp(self, destination_timestamp: int):
        """
        Request the lobby to jump to the specified timestamp.

        This method sends a request to the lobby, asking other members to jump to the specified timestamp in the current activity.

        Parameters:
        - destination_timestamp (int): The desired timestamp to jump to, in seconds.
        """
        self.application_request(JumpToTimestampMessage(destination_timestamp))

    def request_set(self, index: int):
        """
        Request the lobby to set the specified media as the current media.

        This method sends a request to the lobby, asking other members to set the media at the specified index as the current media.

        Parameters:
        - index (int): The index of the media in the playlist to be set as the current media.
        """
        self.application_request(SetMessage(index))

    def _send_player_state(self, address: str):
        """
        Automatically send the current state of the media player to a newly joined member.

        This method is called automatically when a new member is added to the lobby (specifically by the leader client).
        It sends the current state of the media player to the newly joined member using the specified address.

        Parameters:
        - address (str): The address of the newly joined member to send the player state.
        """
        state = StateMessage(self._player.get_state())
        self._lobby.send_to(address, state)

    def _process_stop_message(self, message: StopMessage):
        """
        Process the received StopMessage from the lobby.

        This method processes the received StopMessage from the lobby. When this message is received by the leader and the
        stop command can be issued on the media player, the leader broadcasts the stop message to all members and stops its
        own media player.

        Parameters:
        - message (StopMessage): The StopMessage received from the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
        if not self._player.is_paused:
            self._player.pause()

    def _process_resume_message(self, message: ResumeMessage):
        """
        Process the received ResumeMessage from the lobby.

        This method processes the received ResumeMessage from the lobby. When this message is received by the leader and the
        resume command can be issued on the media player, the leader broadcasts the resume message to all members and resumes its
        own media player.

        Parameters:
        - message (ResumeMessage): The ResumeMessage received from the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
        if self._player.is_paused:
            self._player.play()

    def _process_set_message(self, message: SetMessage):
        """
        Process the received SetMessage from the lobby.

        This method processes the received SetMessage from the lobby. When this message is received by the leader and the
        set command can be issued on the media player, the leader broadcasts the set message to all members and sets its
        own media player.

        Parameters:
        - message (SetMessage): The SetMessage received from the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
        self._player.set_song(message.index)

    def _process_jump_to_timestamp_message(self, message: JumpToTimestampMessage):
        """
        Process the received JumpToTimestampMessage from the lobby.

        This method processes the received JumpToTimestampMessage from the lobby. When this message is received by the leader and the
        jump command can be issued on the media player, the leader broadcasts the jump message to all members and issues the jump command
        on its own media player.

        Parameters:
        - message (JumpToTimestampMessage): The JumpToTimestampMessage received from the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
        self._player.skip_to_timestamp(message.destination_timestamp)

    def _process_state_message(self, message: StateMessage):
        """
        Process the received StateMessage from the lobby.

        This method processes the received StateMessage from the lobby. When this message is received by the leader and the
        state change can be issued on the media player, the leader broadcasts the state change message to all members and sets its
        own media player to the given state.

        Parameters:
        - message (StateMessage): The StateMessage received from the lobby.
        """
        if self._lobby.is_leader():
            self._lobby.broadcast(message)
        self._player.set_state(message.state)
