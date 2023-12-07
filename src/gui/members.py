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
        self._frame.pack(padx=5, pady=2)

        self._member_frame = tk.Frame(self._frame)
        self._member_frame.pack(pady=3)

        self._info_frame = tk.Frame(self._frame, bd=2, relief="solid")
        self._info_frame.pack(pady=3)

        canvas = tk.Canvas(self._info_frame, width=10, height=10, bg=self._ME_COLOR)
        canvas.grid(row=0, column=0)
        text = tk.Label(self._info_frame, text="You", font=("Helvetica", 11, "bold"))
        text.grid(row=0, column=1, sticky=tk.W)

        canvas = tk.Canvas(self._info_frame, width=10, height=10, bg=self._LEADER_COLOR)
        canvas.grid(row=0, column=2)
        text = tk.Label(self._info_frame, text="Leader", font=("Helvetica", 11, "bold"))
        text.grid(row=0, column=3)

        canvas = tk.Canvas(self._info_frame, width=10, height=10, bg=self._ME_LEADER_COLOR)
        canvas.grid(row=1, column=0)
        text = tk.Label(self._info_frame, text="You as leader", font=("Helvetica", 11, "bold"))
        text.grid(row=1, column=1)

    def update_members(self, new_members: list, me, leader):
        for widget in self._member_frame.winfo_children():
            widget.destroy()
        for member in new_members:
            label = tk.Label(self._member_frame, text=str(member), borderwidth=1, relief="solid", width=15, height=2, font=("Helvetica", 14, "bold"))
            if leader == me and me == member:
                label.config(fg=self._ME_LEADER_COLOR)
            elif me == member:
                label.config(fg=self._ME_COLOR)
            elif leader == member:
                label.config(fg=self._LEADER_COLOR)
            label.pack(pady=5)

def members_window(window: tk.Toplevel, lobby: NetLobby):
    window.resizable(False, True)
    window.geometry("240x200+800+200")
    MembersFrame(window, lobby)
