import ttkbootstrap as ttk
from ttkbootstrap.constants import *  # type: ignore

root = ttk.Window(themename="darkly")


def timer():
    timer_window = ttk.Toplevel("Timer window")
    timer_window.mainloop()


button_send = ttk.Button(
    root, text=" Send", bootstyle=(SUCCESS, OUTLINE))
button_send.pack(side=LEFT, padx=8, pady=12)

Stop_button = ttk.Button(
    root, text=" Stop ", bootstyle=(INFO), command=timer)
Stop_button.pack(side=LEFT, padx=8, pady=12)


root.mainloop()
