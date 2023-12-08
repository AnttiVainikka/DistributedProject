import vlc #pip install python-vlc
from dataclasses import dataclass
from net.lobby import NetLobby
from event_manager.event_manager import EventManager

from mutagen.mp3 import MP3

def _audio_duration(file_path):
    try:
        audio = MP3(file_path)
        duration_seconds = audio.info.length
        return duration_seconds * 1000
    except Exception as e:
        print(f"Error: {e}")
        return -1

@dataclass
class State:
    index: int
    timestamp: int
    playing: int

class EpicMusicPlayer(EventManager):
    EVENT_TIMESTAMP = "timestamp_changed"
    EVENT_CHANGED = "music_changed"
    EVENT_PAUSED = "music_paused"
    EVENT_STARTED = "music_started"
    EVENT_SONG_LENGTH = "song_length"

    def __init__(self,playlist :list):
        super().__init__()
        self._register_event(self.EVENT_TIMESTAMP)
        self._register_event(self.EVENT_CHANGED)
        self._register_event(self.EVENT_PAUSED)
        self._register_event(self.EVENT_STARTED)
        self._register_event(self.EVENT_SONG_LENGTH)

        self.vlc_instance = vlc.Instance()
        
        # Create Song playlist from the input list of paths
        self.playlist: list[Song] = []
        for song in playlist:
            self.playlist.append(Song(self.vlc_instance,song))
        
        # Create media list from playlist
        self.media_list: vlc.MediaList = self.vlc_instance.media_list_new()
        for song in self.playlist:
            self.media_list.add_media(song.media)

        # Create media player and add media list
        self.player: vlc.MediaListPlayer = self.vlc_instance.media_list_player_new()
        self.player.set_playback_mode(vlc.PlaybackMode.loop)
        self.player.set_media_list(self.media_list)

        # Connect the necessary events
        event_manager: vlc.EventManager = self.player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self._event_media_set)
        self.player.get_media_player().event_manager().event_attach(vlc.EventType.MediaPlayerTimeChanged, self._time_changed)

        self.track = 0
        self.song = self.playlist[0]
        self.pause = False
        self.next = False
        self.exit = False
        self.skip = False
        self.direct_set = False
        self.timestamp = ""
        self.lobby: NetLobby = None

        self.player.play()
        self.player.set_pause(1)

    def _time_changed(self, event):
        self._raise_event(self.EVENT_TIMESTAMP, event.u.new_time)

    @property
    def current_media(self) -> int:
        return self.media_list.index_of_item(self.player.get_media_player().get_media())

    def get_state(self) -> State:
        return State(self.current_media,
                     self.player.get_media_player().get_time(),
                     self.player.is_playing())

    def set_state(self, state: State):
        self.set_song(state.index)
        self.skip_to_timestamp(state.timestamp)
        if state.playing:
            self.play()
        else:
            self.player.set_pause(1)

    def start(self):
        self.pause = True
        self._raise_event(self.EVENT_CHANGED, self.song.name, self.song.length)
        self._raise_event(self.EVENT_PAUSED, self.song.name, 0)

    def do_exit(self):
        self.exit = True
        # TODO: message

    def do_pause(self):
        self.pause = True
        self.player.set_pause(1)
        self._raise_event(self.EVENT_PAUSED, self.song.name, self.player.get_media_player().get_time())
    
    def play(self):
        self.pause = False
        self.player.play()
        self._raise_event(self.EVENT_STARTED, self.song.name, self.player.get_media_player().get_time())

    def skip_to_timestamp(self,timestamp):
        # Skipping fails sometimes when skipping while paused
        duration = self.playlist[self.current_media].length
        if timestamp >= duration or timestamp < 0:
            return
        
        self.player.get_media_player().set_time(timestamp)
        self._raise_event(self.EVENT_TIMESTAMP, timestamp)

    def set_song(self, index: int):
        if self.current_media != index:
            is_playing = self.player.is_playing()
            self.direct_set = True
            self.player.play_item_at_index(index)
            self.direct_set = False
            if not is_playing:
                self.player.set_pause(1)
            self._raise_event(self.EVENT_CHANGED, self.playlist[index].name, self.playlist[index].length)

    def request_pause(self):
        if self.lobby is not None:
            self.lobby.request_stop()
        else:
            self.do_pause()

    def request_resume(self):
        if self.lobby is not None:
            self.lobby.request_resume()
        else:
            self.play()

    def request_skip(self):
        index = (self.current_media + 1) % len(self.media_list)
        if self.lobby is not None:
            self.lobby.request_set(index)
        else:
            self.set_song(index)

    def request_skip_to_timestamp(self, timestamp: int):
        if self.lobby is not None:
            self.lobby.request_jump_to_timestamp(timestamp)
        else:
            self.skip_to_timestamp(timestamp)

    def _event_media_set(self, event):
        if self.lobby is not None:
            if not self.direct_set:
                if self.lobby.is_leader():
                    self.lobby.request_set(self.current_media)
                    self.request_resume()
                    self._raise_event(self.EVENT_CHANGED, self.playlist[self.current_media].name, self.playlist[self.current_media].length)
                else:
                    self.player.set_pause(1)
        else:
            pass

class Song:
    def __init__(self, vlc_instance,song :str):
        self.media: vlc.Media = vlc_instance.media_new(song)
        self.length: int = _audio_duration(song)
        self.name: str = song.replace("songs/","").replace(".mp3","").replace(".mpga","")
