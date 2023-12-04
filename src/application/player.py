import vlc #pip install python-vlc
from pynput import keyboard #pip install pynput
import time

pause = False
skip = False
exit = False

def on_press(key):
    global pause
    global skip
    global exit
    pressed = '{0}'.format(key)
    if pressed == "'1'":#pause
        if pause == False:
            pause = True
        else:
            pause = False
    if pressed == "'2'":#skip
        skip = True
    if pressed == "'3'":#exit1
        exit = True

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
        
    def start(self):
        global pause
        global skip
        global exit
        song = self.song.name.replace("songs/","").replace(".mp3","")
        print("Playing: "+song+"\n1: Pause\n2: Skip\n3: Exit")
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        while True:
            if not pause:
                self.play()
            if pause and self.player.is_playing():
                self.player.set_pause(1) #TODO Send message to pause
            if skip:
                skip = False
                self.next_song() #TODO Send message to skip to next song
            if exit:
                break #TODO Send message that this node is leaving lobby

    def play(self):
        self.player.play()
        time.sleep(2) # VLC needs time to get ready
        while (pause,skip,exit) == (False,False,False):
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
        song = self.song.name.replace("songs/","").replace(".mp3","")
        print("Playing: "+song+"\n1: Pause\n2: Skip\n3: Exit")

class Song:
    def __init__(self, vlc_instance,song :str):
        self.media = vlc_instance.media_new(song)
        self.name = song

songs = ["songs/[Copyright Free Romantic Music] - .mpga","songs/Orchestral Trailer Piano Music (No Copyright) .mpga"]
player = EpicMusicPlayer(songs)
player.start()
#112322121212213