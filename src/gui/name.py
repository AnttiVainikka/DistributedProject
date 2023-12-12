import tkinter as tk

class NameFrame:
    def __init__(self, master, ok_callback, exit_callback, **kwargs):
        self._frame = tk.Frame(master, **kwargs)
        self._frame.pack(padx=5, pady=5)

        self._top_frame = tk.Frame(self._frame)
        self._top_frame.pack(side="top", pady=5)

        self._bot_frame = tk.Frame(self._frame)
        self._bot_frame.pack(side="bottom", pady=5)

        self._label = tk.Label(self._top_frame, text="Name: ", font=("Helvetica", 14, "bold"))
        self._label.pack(side="left")

        self._text_input = tk.Entry(self._top_frame, font=("Helvetica", 14, "bold"))
        self._text_input.pack(side="left", padx=5)

        self._exit_button = tk.Button(self._bot_frame, text="Exit", command=exit_callback, font=("Helvetica", 14, "bold"))
        self._exit_button.pack(side="right", padx=5)

        self._ok_button = tk.Button(self._bot_frame, text="Ok", command=self._ok_button_pressed, font=("Helvetica", 14, "bold"))
        self._ok_button.pack(side="right", padx=5)

        self._ok_callback = ok_callback

    def _ok_button_pressed(self):
        self._ok_callback(self._text_input.get())

def name_window(window: tk.Tk, ok_callback, exit_callback):
    for widget in window.winfo_children():
        widget.destroy()
    window.resizable(False, False)
    NameFrame(window, ok_callback, exit_callback)
    window.geometry("300x100+200+200")
