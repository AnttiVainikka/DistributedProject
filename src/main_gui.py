import random
from requests import get
from tkinter import *

from application.player import EpicMusicPlayer

from net.lobby import NetLobby

from gui.main import main_window
from gui.name import name_window
from gui.connect import connect_window
from gui.music_player import music_player_window
from gui.members import members_window

def get_public_ip():
    return get('https://api.ipify.org').text

class Application:
    def __init__(self, songs: list[str], local: bool):
        self.main_window = Tk()
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._name = "No Name"
        self._player = EpicMusicPlayer(songs)
        self._lobby = NetLobby()
        self._player.connect_to_lobby(self._lobby)
        self._local = local

    def set_name(self, name: str):
        self._name = name
        main_window(self.main_window, self.main_host_pushed, self.main_connect_pushed, self.main_exit_pushed)

    def start(self):
        name_window(self.main_window, self.set_name, self.main_exit_pushed)
        self.main_window.mainloop()

    def main_host_pushed(self):
        self._lobby.start()
        ip = '127.0.0.1' if self._local else get_public_ip()
        port = 30000

        print(f"Listening on {ip}:{port}")
        self._lobby.create_lobby(ip, port, self._name)

        music_player_window(self.main_window, self._player)
        members_win = Toplevel(self.main_window)
        members_window(members_win, self._lobby)
        self._player.start()
        
    def main_connect_pushed(self):
        connect_window(self.main_window, self.connect_connect_pushed, self.connect_back_pushed)

    def main_exit_pushed(self):
        self.main_window.destroy()

    def connect_connect_pushed(self, ip: str):
        music_player_window(self.main_window, self._player)
        members_win = Toplevel(self.main_window)
        members_window(members_win, self._lobby)
        
        if ip == "":
            ip = '127.0.0.1'

        address = ip.split(':')

        my_ip = '127.0.0.1' if self._local else get_public_ip()
        port = random.randint(10000, 30000)

        print(f"Listening on {my_ip}:{port}")

        self._lobby.start()
        self._lobby.join_lobby(self._name, my_ip, port, address[0], address[1] if len(address) == 2 else 30000)
        self._player.start()

    def connect_back_pushed(self):
        main_window(self.main_window, self.main_host_pushed, self.main_connect_pushed, self.main_exit_pushed)

    def on_close(self):
        self._lobby.leave_lobby()
        self._lobby.stop()

        self.main_window.destroy()
