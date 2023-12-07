import tkinter as tk

class MainFrame():
    def __init__(self, master, 
                       host_callback,
                       connect_callback,
                       exit_callback,
                       **kwargs):
        self._main_frame = tk.Frame(master, **kwargs)
        self._main_frame.pack(expand=True, fill="both", pady=3, padx=3)
        
        self._host_button = tk.Button(self._main_frame, text="Host", font=("Helvetica", 14, "bold"), command=host_callback, height=2, width=5)
        self._host_button.pack(side="left", padx=5)
        
        self._connect_button = tk.Button(self._main_frame, text="Connect", font=("Helvetica", 14, "bold"), command=connect_callback, height=2, width=8)
        self._connect_button.pack(side="left", padx=5)

        self._exit_button = tk.Button(self._main_frame, text="Exit", command=exit_callback, font=("Helvetica", 14, "bold"), height=1, width=4)
        self._exit_button.pack(side="right")


def main_window(window: tk.Tk, host_callback, connect_callback, exit_callback):
    for widget in window.winfo_children():
        widget.destroy()
    window.resizable(False, False)
    MainFrame(window, host_callback, connect_callback, exit_callback)
    window.geometry("300x75+200+200")
