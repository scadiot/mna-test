from __future__ import annotations
import copy
import math
import tkinter as tk
from editor.circuit_model import CircuitModel, ComponentData, NodeData, Pin

COMP_SIZE = 100
PIN_RADIUS = 6
NODE_RADIUS = 10

# (name, label, (dx, dy)) — offsets relatifs au centre avant rotation
COMPONENT_TEMPLATES: dict[str, dict] = {
    "resistor":       {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"resistance": 1000.0}},
    "capacitor":      {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"capacitance": 1e-6}},
    "inductor":       {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"inductance": 0.01}},
    "switch":         {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"closed": False}},
    "voltage_source": {"pins": [Pin("node_pos", "+", (0, -50)), Pin("node_neg", "−", (0, 50))],    "params": {"waveform": "dc", "amplitude": 5.0}},
    "current_source": {"pins": [Pin("node_pos", "+", (0, -50)), Pin("node_neg", "−", (0, 50))],    "params": {"waveform": "dc", "amplitude": 0.001}},
    "voltmeter":      {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"history_size": 500}},
    "ammeter":        {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_b", "B", (50, 0))],        "params": {"history_size": 500}},
    "transistor_bjt": {"pins": [Pin("node_base", "B", (-50, 0)), Pin("node_collector", "C", (0, -50)), Pin("node_emitter", "E", (0, 50))], "params": {"beta": 100, "vce_sat": 0.2}},
    "opamp":          {"pins": [Pin("node_plus", "IN+", (-50, -25)), Pin("node_minus", "IN−", (-50, 25)), Pin("node_out", "OUT", (50, 0))], "params": {}},
    "diode":          {"pins": [Pin("node_a", "A", (-50, 0)), Pin("node_k", "K", (50, 0))],        "params": {"is": 1e-12, "n": 1.0}},
}


def rotate_offset(dx: float, dy: float, rotation: int) -> tuple[float, float]:
    angle = math.radians(rotation)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a)


def pin_abs_pos(comp: ComponentData, pin: Pin) -> tuple[float, float]:
    rdx, rdy = rotate_offset(pin.offset[0], pin.offset[1], comp.rotation)
    return (comp.x + rdx, comp.y + rdy)


class EditorCanvas(tk.Frame):
    def __init__(self, parent, model: CircuitModel):
        super().__init__(parent)
        self.model = model
        self._selected_comp: str | None = None
        self._selected_node: str | None = None
        self._selected_wire: tuple[str, str] | None = None  # (comp_id, pin_name)
        self._state = "IDLE"
        self._drag_start: tuple[float, float] = (0, 0)
        self._connect_source: tuple[str, str] | None = None  # (comp_id, pin_name)
        self._connect_line: int | None = None
        self._ghost_rect: int | None = None
        self._on_selection_change = None
        self._on_model_change = None

        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._bind_events()

    def _bind_events(self):
        # Placeholder — interactions seront ajoutées en Task 5
        pass

    def set_on_selection_change(self, cb):
        self._on_selection_change = cb

    def set_on_model_change(self, cb):
        self._on_model_change = cb

    def _notify_selection(self):
        if self._on_selection_change:
            self._on_selection_change(self._selected_comp, self._selected_node)

    def _notify_model(self):
        if self._on_model_change:
            self._on_model_change()

    def redraw(self):
        self.canvas.delete("all")
        for comp in self.model.components:
            self._draw_component(comp)
        for node in self.model.nodes:
            self._draw_node(node)
        for comp in self.model.components:
            self._draw_wires(comp)

    def _draw_component(self, comp: ComponentData):
        tag = f"comp_{comp.id}"
        half = COMP_SIZE // 2
        x0, y0 = comp.x - half, comp.y - half
        x1, y1 = comp.x + half, comp.y + half

        is_sel = (comp.id == self._selected_comp)
        outline = "#ff8800" if is_sel else "#444444"
        width = 3 if is_sel else 1

        self.canvas.create_rectangle(x0, y0, x1, y1,
                                      fill="#e8e8e8", outline=outline,
                                      width=width, tags=(tag, "component"))
        self.canvas.create_text(comp.x, comp.y, text=comp.type,
                                 font=("TkDefaultFont", 8), tags=(tag, "component"))
        self.canvas.create_text(comp.x, y0 + 8, text=comp.id,
                                 font=("TkDefaultFont", 7, "bold"), tags=(tag, "component"))

        template = COMPONENT_TEMPLATES.get(comp.type, {})
        for pin in template.get("pins", []):
            px, py = pin_abs_pos(comp, pin)
            connected = pin.name in comp.pin_connections
            color = "#44bb44" if connected else "#ff4444"
            pin_tag = f"pin_{comp.id}_{pin.name}"
            self.canvas.create_oval(
                px - PIN_RADIUS, py - PIN_RADIUS,
                px + PIN_RADIUS, py + PIN_RADIUS,
                fill=color, outline="#222222",
                tags=(tag, "pin", pin_tag))

    def _draw_node(self, node: NodeData):
        tag = f"node_{node.id}"
        is_sel = (node.id == self._selected_node)
        outline = "#ff8800" if is_sel else "#2255aa"
        width = 3 if is_sel else 1
        fill = "black" if node.is_gnd else "#aad4ff"
        text_color = "white" if node.is_gnd else "black"
        self.canvas.create_oval(
            node.x - NODE_RADIUS, node.y - NODE_RADIUS,
            node.x + NODE_RADIUS, node.y + NODE_RADIUS,
            fill=fill, outline=outline, width=width,
            tags=(tag, "node"))
        label = "GND" if node.is_gnd else node.id
        self.canvas.create_text(node.x, node.y - NODE_RADIUS - 8,
                                 text=label, font=("TkDefaultFont", 7),
                                 fill=text_color if not node.is_gnd else "black",
                                 tags=(tag, "node"))

    def _draw_wires(self, comp: ComponentData):
        template = COMPONENT_TEMPLATES.get(comp.type, {})
        for pin in template.get("pins", []):
            if pin.name not in comp.pin_connections:
                continue
            node_id = comp.pin_connections[pin.name]
            node = self.model.get_node(node_id)
            if node is None:
                continue
            px, py = pin_abs_pos(comp, pin)
            wire_tag = f"wire_{comp.id}_{pin.name}"
            is_sel = (self._selected_wire == (comp.id, pin.name))
            color = "#ff8800" if is_sel else "black"
            width = 3 if is_sel else 2
            self.canvas.create_line(px, py, node.x, node.y,
                                     fill=color, width=width,
                                     tags=(wire_tag, "wire"))

    def drop_component(self, comp_type: str, canvas_x: float, canvas_y: float):
        template = COMPONENT_TEMPLATES.get(comp_type)
        if template is None:
            return
        comp_id = self.model.next_id(comp_type)
        comp = ComponentData(id=comp_id, type=comp_type,
                              x=canvas_x, y=canvas_y, rotation=0,
                              params=copy.deepcopy(template["params"]),
                              pin_connections={})
        self.model.add_component(comp)
        self.redraw()
        self._notify_model()
