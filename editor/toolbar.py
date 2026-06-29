import tkinter as tk


class Toolbar(tk.Frame):
    def __init__(self, parent, on_new, on_open, on_save, on_save_as):
        super().__init__(parent, bd=1, relief=tk.RAISED)
        buttons = [
            ("📄", "Nouveau  (Ctrl+N)", on_new),
            ("📂", "Ouvrir   (Ctrl+O)", on_open),
            ("💾", "Enregistrer  (Ctrl+S)", on_save),
            ("💾+", "Enregistrer sous  (Ctrl+Shift+S)", on_save_as),
        ]
        for icon, tip, cmd in buttons:
            btn = tk.Button(self, text=icon, width=4, height=2,
                            relief=tk.FLAT, command=cmd,
                            font=("TkDefaultFont", 14))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self._bind_tooltip(btn, tip)

    def _bind_tooltip(self, widget, text):
        tip_win = []

        def show(event):
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            tk.Label(tw, text=text, background="#ffffe0",
                     relief=tk.SOLID, borderwidth=1,
                     font=("TkDefaultFont", 9)).pack()
            tip_win.append(tw)

        def hide(event):
            for tw in tip_win:
                tw.destroy()
            tip_win.clear()

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
