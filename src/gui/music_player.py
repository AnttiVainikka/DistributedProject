import tkinter as tk
from application.player import EpicMusicPlayer


class MusicPlayerFrame:
    def __init__(self, master, player: EpicMusicPlayer, **kwargs):
        self._player = player
        self._player.connect_to_event(self._player.EVENT_TIMESTAMP, self.set_timestamp)
        self._player.connect_to_event(self._player.EVENT_PAUSED, self._paused)
        self._player.connect_to_event(self._player.EVENT_STARTED, self._started)
        self._player.connect_to_event(self._player.EVENT_CHANGED, self._changed)
        self._player.connect_to_event(self._player.EVENT_SONG_LENGTH, self.set_max_timestamp)

        self._frame = tk.Frame(master, **kwargs)
        self._frame.pack(padx=2)
        
        self._name_text = tk.StringVar()
        self._name_text.set("")
        self._name_label = tk.Label(self._frame, textvariable=self._name_text, font=("Helvetica", 14, "bold"))
        self._name_label.pack(pady=5)

        self._max_timestamp = 0
        self._timestamp_text = tk.StringVar()
        self._timestamp_text.set("0 / 0")
        self._timestamp_label = tk.Label(self._frame, textvariable=self._timestamp_text, font=("Helvetica", 14, "bold"))
        self._timestamp_label.pack(pady=5)

        self._is_slider_dragged = False
        self._slider = tk.Scale(self._frame, orient=tk.HORIZONTAL)
        self._slider.bind("<Button-1>", self._slider_pressed)
        self._slider.bind("<ButtonRelease-1>", self._slider_released)
        self._slider.pack(pady=5, fill="x")

        self._button_frame = tk.Frame(self._frame)
        self._button_frame.pack(pady=5)

        self._pause_button = tk.Button(self._button_frame, text="Pause", font=("Helvetica", 14, "bold"), command=self._pause_pushed)
        self._pause_button.pack(side="left", padx=3)

        self._start_button = tk.Button(self._button_frame, text="Start", font=("Helvetica", 14, "bold"), command=self._start_pushed)
        self._start_button.pack(side="left", padx=3)

        self._next_button = tk.Button(self._button_frame, text="Next", font=("Helvetica", 14, "bold"), command=self._next_pushed)
        self._next_button.pack(side="left", padx=3)

    def set_name(self, name: str):
        self._name_text.set(name)

    def set_max_timestamp(self, max_timestamp: int):
        self._max_timestamp = int(max_timestamp)
        self._slider.config(from_=0, to=self._max_timestamp)

    def set_timestamp(self, timestamp: int):
        ts = int(timestamp)
        if ts > self._max_timestamp:
            ts = self._max_timestamp
        self._timestamp_text.set(f"{ts} / {self._max_timestamp}")
        if not self._is_slider_dragged:
            self._slider.set(ts)

    def _started(self, name: str, timestamp: int):
        self.set_timestamp(timestamp)
        self._start_button.config(state="disabled")
        self._pause_button.config(state="active")

    def _paused(self, name: str, timestamp: int):
        self.set_timestamp(timestamp)
        self._pause_button.config(state="disabled")
        self._start_button.config(state="active")

    def _changed(self, name: str, max_timestamp: int):
        self._name_text.set(name)
        #self.set_max_timestamp(max_timestamp)

    def _slider_pressed(self, event):
        self._is_slider_dragged = True

    def _slider_released(self, event):
        self._is_slider_dragged = False
        self._player.request_skip_to_timestamp(self._slider.get())

    def _pause_pushed(self):
        self._player.request_pause()

    def _start_pushed(self):
        self._player.request_resume()

    def _next_pushed(self):
        self._player.request_skip()

def music_player_window(window: tk.Tk, player: EpicMusicPlayer):
    for widget in window.winfo_children():
        widget.destroy()
    window.resizable(False, False)
    MusicPlayerFrame(window, player)
    window.geometry("280x180+200+200")
