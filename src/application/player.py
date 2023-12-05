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
        self.next = False
        self.exit = False
        self.skip = False
        self.timestamp = ""

    def on_press(self,key):
        pressed = '{0}'.format(key)
        keys = ["'0'","'1'","'2'","'3'","'4'","'5'","'6'","'7'","'8'","'9'","'t'"]
        if self.skip:
            if pressed in keys:
                if pressed == keys[10]:
                    self.skip = False
                else:
                    self.timestamp += pressed.replace("'","")
        else:
            if pressed == keys[1]:#pause
                if self.pause == False:
                    self.pause = True
                else:
                    self.pause = False
            if pressed == keys[2]:#skip
                self.next = True
            if pressed == keys[3]:#exit
                self.exit = True
            if pressed == keys[4]:#print timestamp
                self.skip = True

    def start(self):
        print("Playing: "+self.song.name+"\n1: Pause    2: Next\n3: Exit     4: Skip")
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        while True:
            if not self.pause:
                self.play()
            if self.pause and self.player.is_playing():
                self.player.set_pause(1) #TODO Send message to pause
            if self.next:
                self.next = False
                self.next_song() #TODO Send message to skip to next song
            if self.exit:
                break #TODO Send message that this node is leaving lobby
            if self.skip:
                timestamp = self.player.get_time()/1000
                duration = self.player.get_length()/1000
                print(f"{int(timestamp)}/{int(duration)}")
                print("Type second to skip to. Press 't' to finish.")
                while self.skip:
                    if not self.player.is_playing() and not self.pause:
                        self.skip = False
                        self.timestamp = ""
                        self.next_song()
                if not self.timestamp:
                    print("Skipping canceled")
                else:
                    self.skip_to_timestamp(self.timestamp)

    def play(self):
        self.player.play()
        time.sleep(2) # VLC needs time to get ready
        while (self.pause,self.next,self.exit,self.skip) == (False,False,False,False):
            if not self.player.is_playing():
                self.next_song()
                break

    def next_song(self):
        if self.track == len(self.playlist)-1:
            self.song = self.playlist[0]
            self.track = 0
        else:
            self.track += 1
            self.song = self.playlist[self.track]
        self.player.set_media(self.song.media)
        print("Playing: "+self.song.name)

    def skip_to_timestamp(self,timestamp):
        # Skipping fails sometimes when skipping while paused
        duration = self.player.get_length()/1000
        percentage = round(int(timestamp)/duration,2)
        self.timestamp = ""
        self.skip = False
        if percentage <= 1 and percentage >= 0:
            self.player.set_position(percentage)
            timestamp = self.player.get_time()/1000
            print(f"Skipped to {int(timestamp)}/{int(duration)}")
        else:
            print("Invalid second")

class Song:
    def __init__(self, vlc_instance,song :str):
        self.media = vlc_instance.media_new(song)
        self.name = song.replace("songs/","").replace(".mp3","").replace(".mpga","")

songs = ["songs/[Copyright Free Romantic Music] - .mpga","songs/Orchestral Trailer Piano Music (No Copyright) .mpga"]
player = EpicMusicPlayer(songs)
player.start()
