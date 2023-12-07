import tkinter as tk
from collections.abc import Iterable

from net.lobby import NetLobby

class MembersFrame:
    _LEADER_COLOR = "#3333ff"
    _ME_COLOR = "#06832d"
    _ME_LEADER_COLOR = "#ee8127"

    def __init__(self, master, lobby: NetLobby, **kwargs):
        lobby.connect_to_event(lobby.EVENT_MEMBERS_CHANGED, self.update_members)

        self._frame = tk.Frame(master, **kwargs)
        self._frame.pack(padx=20, pady=20)

    def update_members(self, new_members: list, me, leader):
        for widget in self._frame.winfo_children():
            widget.destroy()
        for member in range(len(new_members)):
            label = tk.Label(self._frame, text=str(member), borderwidth=1, relief="solid", width=15, height=2, font=("Helvetica", 14, "bold"))
            if leader == me and me == member:
                label.config(fg=self._ME_LEADER_COLOR)
            elif me == member:
                label.config(fg=self._ME_COLOR)
            elif leader == member:
                label.config(fg=self._LEADER_COLOR)
            label.pack(pady=5)

def members_window(window: tk.Toplevel, lobby: NetLobby):
    window.resizable(False, True)
    window.geometry("120x200+800+200")
    MembersFrame(window, lobby)
