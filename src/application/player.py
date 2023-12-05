import vlc #pip install python-vlc
from pynput import keyboard #pip install pynput
import time

class EpicMusicPlayer:
    def __init__(self,playlist :list):
        self.playlist = []
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.track = 0
        for song in playlist:
            self.playlist.append(Song(self.vlc_instance,song))
        self.song = self.playlist[0]
        self.player.set_media(self.song.media)
        self.pause = False
        self.skip = False
        self.exit = False

    def on_press(self,key):
        pressed = '{0}'.format(key)
        if pressed == "'1'":#pause
            if self.pause == False:
                self.pause = True
            else:
                self.pause = False
        if pressed == "'2'":#skip
            self.skip = True
        if pressed == "'3'":#exit1
            self.exit = True

    def start(self):
        print("Playing: "+self.song.name+"\n1: Pause\n2: Skip\n3: Exit")
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        while True:
            if not self.pause:
                self.play()
            if self.pause and self.player.is_playing():
                self.player.set_pause(1) #TODO Send message to pause
            if self.skip:
                self.skip = False
                self.next_song() #TODO Send message to skip to next song
            if self.exit:
                break #TODO Send message that this node is leaving lobby

    def play(self):
        self.player.play()
        time.sleep(2) # VLC needs time to get ready
        while (self.pause,self.skip,self.exit) == (False,False,False):
            if not self.player.is_playing():
                self.next_song()
            
    def next_song(self):
        if self.track == len(self.playlist)-1:
            self.song = self.playlist[0]
            self.track = 0
        else:
            self.track += 1
            self.song = self.playlist[self.track]
        self.player.set_media(self.song.media)
        print("Playing: "+self.song.name+"\n1: Pause\n2: Skip\n3: Exit")

class Song:
    def __init__(self, vlc_instance,song :str):
        self.media = vlc_instance.media_new(song)
        self.name = song.replace("songs/","").replace(".mp3","").replace(".mpga","")
        #TODO add self.duration and self.timestamp

songs = ["songs/[Copyright Free Romantic Music] - .mpga","songs/Orchestral Trailer Piano Music (No Copyright) .mpga"]
player = EpicMusicPlayer(songs)
player.start()
