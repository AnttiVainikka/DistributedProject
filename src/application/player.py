import vlc #pip install python-vlc
import time
import os
from net.lobby import NetLobby
from event_manager.event_manager import EventManager


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

        self.playlist = []
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.track = 0
        for song in playlist:
            self.playlist.append(Song(self.vlc_instance,song))
        self.song = self.playlist[0]
        self.player.set_media(self.song.media)
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self._media_finished)
        self.pause = False
        self.next = False
        self.exit = False
        self.skip = False
        self.timestamp = ""
        self.lobby: NetLobby = None

    def start(self):
        self.pause = True
        previous_timestamp = 0

        self._raise_event(self.EVENT_CHANGED, self.song.name, 0) # Cannot get the length here
        self._raise_event(self.EVENT_PAUSED, self.song.name, 0)
        while not self.exit:
            current_timestamp = self.player.get_time() // 1000
            if abs(current_timestamp - previous_timestamp) > 0.5:
                self._raise_event(self.EVENT_TIMESTAMP, current_timestamp)
                previous_timestamp = current_timestamp

    def do_exit(self):
        self.exit = True
        # TODO: message

    def do_skip(self):
        self.next_song()

    def do_pause(self):
        self.pause = True
        self.player.set_pause(1)
        self._raise_event(self.EVENT_PAUSED, self.song.name, self.player.get_time() / 1000)
    
    def play(self):
        self.pause = False
        self.player.play()
        time.sleep(2)
        # So I have to raise this here, because for some reasons I cannot query it before playing... or I'm just dumb
        if self.song.length == 0:
            self.song.length = int(self.player.get_length() / 1000)
            self._raise_event(self.EVENT_SONG_LENGTH, self.song.length)
        self._raise_event(self.EVENT_STARTED, self.song.name, self.player.get_time() / 1000)

    def skip_to_timestamp(self,timestamp):
        # Skipping fails sometimes when skipping while paused
        duration = self.player.get_length()/1000
        percentage = round(int(timestamp)/duration,2)
        self.timestamp = ""
        self.skip = False
        if percentage <= 1 and percentage >= 0:
            self.player.set_position(percentage)
            timestamp = self.player.get_time()/1000
        else:
            print("Invalid second")

    def next_song(self):
        if self.track == len(self.playlist)-1:
            self.song = self.playlist[0]
            self.track = 0
        else:
            self.track += 1
            self.song = self.playlist[self.track]
        self.player.set_media(self.song.media)
        self._raise_event("music_changed", self.song.name, 0) # Cannot get length here
        if not self.pause:
            self.play()

    def _media_finished(self, event):
        if self.lobby is not None:
            if self.lobby.is_leader():
                self.request_skip()
        else:
            self.request_skip()

    def request_pause(self):
        if self.lobby is not None:
            self.lobby.request_stop(self.player.get_time())
        else:
            self.do_pause()

    def request_resume(self):
        if self.lobby is not None:
            self.lobby.request_resume(self.player.get_time())
        else:
            self.play()

    def request_skip(self):
        if self.lobby is not None:
            self.lobby.request_skip(self.player.get_time())
        else:
            self.do_skip()

    def request_skip_to_timestamp(self, timestamp: int):
        if self.lobby is not None:
            self.lobby.request_jump_to_timestamp(self.player.get_time(), timestamp)
        else:
            self.skip_to_timestamp(timestamp)

class Song:
    def __init__(self, vlc_instance,song :str):
        self.media = vlc_instance.media_new(song)
        self.name = song.replace("songs/","").replace(".mp3","").replace(".mpga","")
        self.length: int = 0
