# editor/component_panel.py
import tkinter as tk
from editor.circuit_model import NodeData

COMPONENT_TYPES = [
    "resistor", "capacitor", "inductor", "switch",
    "voltage_source", "current_source",
    "voltmeter", "ammeter",
    "transistor_bjt", "opamp", "diode", "potentiometer",
]


class ComponentPanel(tk.Frame):
    def __init__(self, parent, canvas, root: tk.Tk):
        super().__init__(parent, width=140, bd=1, relief=tk.SUNKEN)
        self.pack_propagate(False)
        self._canvas_widget = canvas
        self._root = root
        self._drag_type: str | None = None
        self._ghost: int | None = None

        tk.Label(self, text="Composants", font=("TkDefaultFont", 9, "bold")).pack(pady=(4, 2))

        self._listbox = tk.Listbox(self, selectmode=tk.SINGLE,
                                    font=("TkDefaultFont", 9), height=12)
        for ct in COMPONENT_TYPES:
            self._listbox.insert(tk.END, ct)
        self._listbox.insert(tk.END, "─────────")
        self._listbox.insert(tk.END, "GND")
        self._listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._listbox.bind("<ButtonPress-1>", self._on_list_press)

    def _on_list_press(self, event):
        idx = self._listbox.nearest(event.y)
        if idx < 0 or idx >= len(COMPONENT_TYPES) + 2:
            return
        if idx == len(COMPONENT_TYPES):
            return  # séparateur
        selected = self._listbox.get(idx)
        if selected == "─────────":
            return
        self._drag_type = selected
        self._root.bind("<B1-Motion>", self._on_root_motion)
        self._root.bind("<ButtonRelease-1>", self._on_root_release)

    def _on_root_motion(self, event):
        cv = self._canvas_widget.canvas
        cx = event.x_root - cv.winfo_rootx()
        cy = event.y_root - cv.winfo_rooty()
        if self._ghost:
            cv.delete(self._ghost)
            self._ghost = None
        if 0 <= cx <= cv.winfo_width() and 0 <= cy <= cv.winfo_height():
            self._ghost = cv.create_rectangle(
                cx - 50, cy - 50, cx + 50, cy + 50,
                fill="#cccccc", outline="#555555",
                stipple="gray50", tags="ghost")

    def _on_root_release(self, event):
        self._root.unbind("<B1-Motion>")
        self._root.unbind("<ButtonRelease-1>")
        cv = self._canvas_widget.canvas
        if self._ghost:
            cv.delete(self._ghost)
            self._ghost = None
        cx = event.x_root - cv.winfo_rootx()
        cy = event.y_root - cv.winfo_rooty()
        if 0 <= cx <= cv.winfo_width() and 0 <= cy <= cv.winfo_height():
            if self._drag_type == "GND":
                self._add_gnd_node(float(cx), float(cy))
            else:
                self._canvas_widget.drop_component(self._drag_type, float(cx), float(cy))
        self._drag_type = None

    def _add_gnd_node(self, cx: float, cy: float):
        model = self._canvas_widget.model
        existing_gnds = [n.id for n in model.nodes if n.is_gnd]
        if not existing_gnds:
            node_id = "GND"
        else:
            i = 1
            while f"GND_{i}" in existing_gnds:
                i += 1
            node_id = f"GND_{i}"
        node = NodeData(id=node_id, x=cx, y=cy, is_gnd=True)
        model.add_node(node)
        self._canvas_widget.redraw()
        self._canvas_widget._notify_model()
