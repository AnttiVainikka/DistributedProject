import tkinter as tk

class ConnectFrame:
    def __init__(self, master, connect_callback, back_callback, **kwargs):
        self._frame = tk.Frame(master, **kwargs)
        self._frame.pack(padx=5, pady=5)

        self._top_frame = tk.Frame(self._frame)
        self._top_frame.pack(side="top", pady=5)

        self._bot_frame = tk.Frame(self._frame)
        self._bot_frame.pack(side="bottom", pady=5)

        self._label = tk.Label(self._top_frame, text="IP: ", font=("Helvetica", 14, "bold"))
        self._label.pack(side="left")

        self._text_input = tk.Entry(self._top_frame, font=("Helvetica", 14, "bold"))
        self._text_input.pack(side="left", padx=5)

        self._back_button = tk.Button(self._bot_frame, text="Back", command=back_callback, font=("Helvetica", 14, "bold"))
        self._back_button.pack(side="right", padx=5)

        self._connect_button = tk.Button(self._bot_frame, text="Connect", command=self._button_pressed, font=("Helvetica", 14, "bold"))
        self._connect_button.pack(side="right", padx=5)

        self._connect_callback = connect_callback

    def _button_pressed(self):
        self._connect_callback(self._text_input.get())

def connect_window(window: tk.Tk, connect_callback, back_callback):
    for widget in window.winfo_children():
        widget.destroy()
    window.resizable(False, False)
    ConnectFrame(window, connect_callback, back_callback)
    window.geometry("300x100+200+200")
