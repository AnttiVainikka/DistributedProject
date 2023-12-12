import threading
from tkinter import *

from application.player import EpicMusicPlayer
from net.lobby import NetLobby
from gui.main import main_window
from gui.connect import connect_window
from gui.music_player import music_player_window
from gui.members import members_window

import log

_logger = log.getLogger(__name__)

class Application:
    def __init__(self):
        self.main_window = Tk()
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_close)
        songs = ["src/songs/[Copyright Free Romantic Music] - .mpga","src/songs/Orchestral Trailer Piano Music (No Copyright) .mpga"]
        self._player = EpicMusicPlayer(songs)
        self._lobby = NetLobby()
        self._lobby.register_player(self._player)
        self._should_exit = False

        _logger.debug("Starting network thread...")
        self._net_thread = threading.Thread(target=self._net_main)
        self._net_thread.start()
        _logger.debug("Network thread is running")

    def _net_main(self):
        while not self._should_exit:
            self._lobby.handle_msg()

    def start(self):
        main_window(self.main_window, self.main_host_pushed, self.main_connect_pushed, self.main_exit_pushed)
        self.main_window.mainloop()

    def main_host_pushed(self):
        print(f"Listening on port {self._lobby._port}")
        music_player_window(self.main_window, self._player)
        members_win = Toplevel(self.main_window)
        members_window(members_win, self._lobby)
        
        self._lobby.register_player(self._player)
        self._player.start()

    def main_connect_pushed(self):
        connect_window(self.main_window, self.connect_connect_pushed, self.connect_back_pushed)

    def main_exit_pushed(self):
        self.main_window.destroy()

    def connect_connect_pushed(self, ip: str):
        music_player_window(self.main_window, self._player)
        members_win = Toplevel(self.main_window)
        members_window(members_win, self._lobby)
        
        self._lobby.join_lobby(f'{ip}:30000')
        self._lobby.register_player(self._player)
        self._player.start()

    def connect_back_pushed(self):
        main_window(self.main_window, self.main_host_pushed, self.main_connect_pushed, self.main_exit_pushed)

    def on_close(self):
        self._player.do_exit()
        
        _logger.debug("Stopping network thread...")
        self._should_exit = True
        self._lobby.shutdown()
        self._net_thread.join()
        _logger.debug("Network thread has stopped")

        self.main_window.destroy()

app = Application()
app.start()
