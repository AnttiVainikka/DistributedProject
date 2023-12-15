import vlc
from mutagen.mp3 import MP3

from application.player_lobby_connector import PlayerLobbyConnector

from event_manager.event_manager import EventManager
from application.state import State

import log

_logger = log.getLogger(__name__)

class EpicMusicPlayer(EventManager):
    """
    Music player class with lobby communication capabilities.

    The EpicMusicPlayer class is designed to play media on a client. If it is connected to a lobby,
    it facilitates communication with other members through the lobby.
    """
    
    # Event raised when the timestamp of the media has changed
    EVENT_TIMESTAMP = "timestamp_changed"

    # Event raised when the current media has changed
    EVENT_CHANGED = "music_changed"

    # Event raised when the media is paused
    EVENT_PAUSED = "music_paused"

    # Event raised when the media is started
    EVENT_STARTED = "music_started"

    _vlc_instance: vlc.Instance

    # This contains the songs of media player
    _playlist: list["Song"]

    # This contains the vlc medias (created from the playlist)
    _media_list: vlc.MediaList

    # The main vlc player
    _player: vlc.MediaListPlayer

    # This is used to establish the communication between the player and a lobby
    _connector: PlayerLobbyConnector

    # Used for vlc hack
    _direct_set: bool

    def __init__(self, playlist: list[str]):
        """
        Constructor for the EpicMusicPlayer class.

        This method initializes the VLC backend, adds the songs provided in the playlist as the input parameter,
        registers its own events, and performs other necessary setup for the EpicMusicPlayer.

        When the player is connected to a lobby, instead of directly issueing the commands
        those commands need to be requested from the lobby.

        Parameters:
        - playlist (list[str]): List of song names to be added to the player's playlist.
        """
        super().__init__()

        # Register own events
        self._register_event(self.EVENT_TIMESTAMP)
        self._register_event(self.EVENT_CHANGED)
        self._register_event(self.EVENT_PAUSED)
        self._register_event(self.EVENT_STARTED)

        self._vlc_instance = vlc.Instance()
        
        # Create Song playlist from the input list of paths
        self._playlist: list[Song] = []
        for song in playlist:
            self._playlist.append(Song(self._vlc_instance,song))
        
        # Create media list from playlist
        self._media_list: vlc.MediaList = self._vlc_instance.media_list_new()
        for song in self._playlist:
            self._media_list.add_media(song.media)

        # Create media player and add media list
        self._player: vlc.MediaListPlayer = self._vlc_instance.media_list_player_new()
        self._player.set_playback_mode(vlc.PlaybackMode.loop)
        self._player.set_media_list(self._media_list)

        # Connect the necessary events
        event_manager: vlc.EventManager = self._player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self._event_media_set)
        self._player.get_media_player().event_manager().event_attach(vlc.EventType.MediaPlayerTimeChanged, self._time_changed)

        self._direct_set = False

        self._connector: PlayerLobbyConnector = None

        self._player.play()
        self._player.set_pause(1)

    def start(self):
        """
        Start the media player.

        This method starts the media player. It needs to be called only once when the system is initialized.
        """
        self._raise_event(self.EVENT_CHANGED, self._playlist[self.current_media].name, self._playlist[self.current_media].length)
        self._raise_event(self.EVENT_PAUSED)

    def connect_to_lobby(self, lobby):
        """
        Connect the media player to the lobby for communication.

        This method is used to connect the EpicMusicPlayer to a lobby, enabling communication with other lobby members.

        Parameters:
        - lobby: An instance of the lobby (e.g., NetLobby) to which the media player will connect.
        """
        self._connector = PlayerLobbyConnector(self, lobby)

    @property
    def current_media(self) -> int:
        """
        Get the index of the currently played media.

        This method returns the index of the currently played media in the playlist.

        Returns:
        - int: The index of the currently played media in the playlist.
        """
        return self._media_list.index_of_item(self._player.get_media_player().get_media())

    @property
    def is_paused(self) -> bool:
        """
        Check if the currently played media is paused.

        This method returns a boolean indicating whether the currently played media is in a paused state.

        Returns:
        - bool: True if the media is paused, False if it is playing.
        """
        return not self._player.is_playing()

    def get_state(self) -> State:
        """
        Get the current state of the media player.

        This method returns the current state of the media player, encapsulated in a State object.

        Returns:
        - State: An instance of the State class representing the current state of the media player.
        """
        return State(self.current_media,
                     self._player.get_media_player().get_time(),
                     self._player.is_playing())

    def set_state(self, state: State):
        """
        Set the state of the media player. This is a local method, meaning only affects the local client's media player.

        This method sets the state of the media player using the provided State object.

        Parameters:
        - state (State): An instance of the State class representing the desired state of the media player.
        """
        self.set_song(state.index)
        self.skip_to_timestamp(state.timestamp)
        if state.playing:
            self.play()
        else:
            self._player.set_pause(1)

    def pause(self):
        """
        Pause the currently played media. This is a local method, meaning only affects the local client's media player.

        This method pauses the playback of the currently played media.
        """
        self._player.set_pause(1)
        self._raise_event(self.EVENT_PAUSED)
    
    def play(self):
        """
        Start playing the current media. This is a local method, meaning only affects the local client's media player.

        This method starts playing the currently paused media.
        """
        self._player.play()
        self._raise_event(self.EVENT_STARTED)

    def skip_to_timestamp(self, timestamp:int):
        """
        Set the timestamp of the currently played media. This is a local method, meaning only affects the local client's media player.

        This method sets the timestamp of the currently played media to the specified value.

        Parameters:
        - timestamp (int): The desired timestamp to skip to, in seconds.
        """
        duration = self._playlist[self.current_media].length
        if timestamp >= duration or timestamp < 0:
            return
        
        self._player.get_media_player().set_time(timestamp)
        self._raise_event(self.EVENT_TIMESTAMP, timestamp)

    def set_song(self, index: int):
        """
        Set the index of the media to be played. This is a local method, meaning only affects the local client's media player.

        This method sets the index of the media to be played in the playlist.

        Parameters:
        - index (int): The index of the media in the playlist to be set.
        """
        if self.current_media != index:
            is_playing = self._player.is_playing()
            self._direct_set = True
            self._player.play_item_at_index(index)
            self._direct_set = False
            if not is_playing:
                self._player.set_pause(1)
            self._raise_event(self.EVENT_CHANGED, self._playlist[index].name, self._playlist[index].length)

    def request_pause(self):
        """
        Request a pause from the lobby. This is a lobby method, meaning it is propagated to all the lobby members.

        This method sends a request to the lobby, asking other members to pause the currently played media.
        """
        _logger.debug(f"Request to pause song")
        if self._connector is not None:
            self._connector.request_stop()
        else:
            self.pause()

    def request_resume(self):
        """
        Request a resume from the lobby. This is a lobby method, meaning it is propagated to all the lobby members.

        This method sends a request to the lobby, asking other members to resume the currently paused media.
        """
        _logger.debug(f"Request to start song")
        if self._connector is not None:
            self._connector.request_resume()
        else:
            self.play()

    def request_skip(self):
        """
        Request a skip to the next song from the lobby. This is a lobby method, meaning it is propagated to all the lobby members.

        This method sends a request to the lobby, asking other members to skip to the next song in the playlist.
        """
        index = (self.current_media + 1) % len(self._media_list)
        _logger.debug(f"Request to skip to song {index} ({self._playlist[index].name})")

        if self._connector is not None:
            self._connector.request_set(index)
        else:
            self.set_song(index)

    def request_skip_to_timestamp(self, timestamp: int):
        """
        Request the lobby to skip to the given timestamp. This is a lobby method, meaning it is propagated to all the lobby members.

        This method sends a request to the lobby, asking other members to skip to the specified timestamp in the currently played media.

        Parameters:
        - timestamp (int): The desired timestamp to skip to, in seconds.
        """
        _logger.debug(f"Request to skip to timestamp {timestamp}")
        if self._connector is not None:
            self._connector.request_jump_to_timestamp(timestamp)
        else:
            self.skip_to_timestamp(timestamp)

    def _event_media_set(self, event):
        """
        Handle the event when a media has finished playing.

        This method is called when a media has finished playing. It needs to be handled differently for regular members
        and the leader, as only the leader can automatically move to the next song and propagate the change to all members.

        Parameters:
        - event: The event triggered when a media has finished playing.
        """
        if self._connector is not None:
            if not self._direct_set:
                if self._connector.lobby.is_leader(): # TODO: Try to move this part to the connector
                    self._connector.request_set(self.current_media)
                    self.request_resume()
                    self._raise_event(self.EVENT_CHANGED, self._playlist[self.current_media].name, self._playlist[self.current_media].length)
                else:
                    self._player.set_pause(1)
        else:
            pass

    def _time_changed(self, event):
        """
        Handle the event when the media player's time has changed.

        This method is called by the VLC thread when the time of the media player has changed. It is used to raise the
        EVENT_TIMESTAMP event, indicating a change in the playback timestamp.

        Parameters:
        - event: The event triggered when the media player's time has changed.
        """
        self._raise_event(self.EVENT_TIMESTAMP, event.u.new_time)

class Song:
    """
    Class representing a song with essential information.

    The Song class contains necessary information for a song, including its name, length, and the associated VLC media instance.
    """
    def __init__(self, vlc_instance,song :str):
        self.media: vlc.Media = vlc_instance.media_new(song)
        self.length: int = _audio_duration(song)
        self.name: str = song.replace("songs/","").replace(".mp3","").replace(".mpga","")

def _audio_duration(file_path: str):
    """
    Get the duration of an audio file.

    This function returns the duration of an audio file located at the specified file path.

    Parameters:
    - file_path (str): The path to the audio file.

    Returns:
    - int: The duration of the audio file in seconds.
    """
    try:
        audio = MP3(file_path)
        duration_seconds = audio.info.length
        return duration_seconds * 1000
    except Exception as e:
        print(f"Error: {e}")
        return -1
