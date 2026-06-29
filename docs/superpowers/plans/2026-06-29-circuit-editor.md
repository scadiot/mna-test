# Circuit Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer `editor/`, une application Tkinter permettant de créer et éditer visuellement les fichiers JSON de circuits électroniques.

**Architecture:** Architecture plate — `CircuitModel` porte les données, `EditorCanvas` gère tout le canvas Tkinter avec une machine à 4 états, les panneaux latéraux et la barre d'outils sont des widgets indépendants. Le module est entièrement découplé du simulateur.

**Tech Stack:** Python 3.10+, tkinter (natif), dataclasses, json, math

## Global Constraints

- Python 3.10+ — dataclasses, `match` non requis, f-strings OK
- Tkinter uniquement — aucune dépendance externe
- Le module `editor/` n'importe rien depuis `simulator/` ou `ui/`
- Tous les fichiers dans `editor/` sauf `tests/` qui reste à la racine
- Tests dans `tests/test_editor_*.py`
- Nommage : variables/fonctions en anglais, commentaires/labels UI en français

---

## Fichiers créés ou modifiés

| Fichier | Rôle |
|---|---|
| `editor/__init__.py` | Package marker vide |
| `editor/circuit_model.py` | Dataclasses + CircuitModel |
| `editor/io.py` | Chargement/sauvegarde JSON étendu |
| `editor/editor_canvas.py` | Canvas 2D, machine à états, COMPONENT_TEMPLATES |
| `editor/component_panel.py` | Panneau gauche, drag initiation |
| `editor/properties_panel.py` | Panneau droit, édition propriétés |
| `editor/toolbar.py` | Barre d'outils 4 boutons |
| `editor/main.py` | Point d'entrée, fenêtre principale |
| `tests/test_editor_model.py` | Tests CircuitModel |
| `tests/test_editor_io.py` | Tests io.py |

---

### Task 1: Modèle de données (`circuit_model.py`)

**Files:**
- Create: `editor/__init__.py`
- Create: `editor/circuit_model.py`
- Test: `tests/test_editor_model.py`

**Interfaces:**
- Produces:
  - `Pin(name, label, offset)` — dataclass
  - `ComponentData(id, type, x, y, rotation, params, pin_connections)` — dataclass
  - `NodeData(id, x, y, is_gnd)` — dataclass
  - `CircuitModel` — `.components: list[ComponentData]`, `.nodes: list[NodeData]`, `.name: str`, `.dt: float`
  - `CircuitModel.add_component(comp: ComponentData) -> None`
  - `CircuitModel.remove_component(comp_id: str) -> None`
  - `CircuitModel.add_node(node: NodeData) -> None`
  - `CircuitModel.remove_node(node_id: str) -> None`
  - `CircuitModel.connect_pin(comp_id: str, pin_name: str, node_id: str) -> None`
  - `CircuitModel.disconnect_pin(comp_id: str, pin_name: str) -> None`
  - `CircuitModel.next_id(comp_type: str) -> str`
  - `CircuitModel.rename_node(old_id: str, new_id: str) -> None`
  - `CircuitModel.rename_component(old_id: str, new_id: str) -> bool`
  - `CircuitModel.get_component(comp_id: str) -> ComponentData | None`
  - `CircuitModel.get_node(node_id: str) -> NodeData | None`
  - `CircuitModel.is_dirty: bool` — True si modifications non sauvegardées
  - `CircuitModel.mark_clean() -> None`

- [ ] **Step 1: Créer `editor/__init__.py` vide**

```python
# editor/__init__.py
```

- [ ] **Step 2: Écrire les tests du modèle**

```python
# tests/test_editor_model.py
import pytest
from editor.circuit_model import CircuitModel, ComponentData, NodeData, Pin

def make_resistor(id="R1", x=100.0, y=100.0):
    return ComponentData(id=id, type="resistor", x=x, y=y, rotation=0,
                         params={"resistance": 1000.0}, pin_connections={})

def make_node(id="N1", x=200.0, y=100.0):
    return NodeData(id=id, x=x, y=y, is_gnd=False)

def test_add_component():
    m = CircuitModel()
    m.add_component(make_resistor())
    assert len(m.components) == 1
    assert m.components[0].id == "R1"

def test_remove_component():
    m = CircuitModel()
    m.add_component(make_resistor())
    m.remove_component("R1")
    assert len(m.components) == 0

def test_add_node():
    m = CircuitModel()
    m.add_node(make_node())
    assert len(m.nodes) == 1

def test_remove_node():
    m = CircuitModel()
    m.add_node(make_node())
    m.remove_node("N1")
    assert len(m.nodes) == 0

def test_connect_pin():
    m = CircuitModel()
    m.add_component(make_resistor())
    m.add_node(make_node())
    m.connect_pin("R1", "node_a", "N1")
    assert m.components[0].pin_connections["node_a"] == "N1"

def test_disconnect_pin():
    m = CircuitModel()
    m.add_component(make_resistor())
    m.add_node(make_node())
    m.connect_pin("R1", "node_a", "N1")
    m.disconnect_pin("R1", "node_a")
    assert "node_a" not in m.components[0].pin_connections

def test_next_id_increments():
    m = CircuitModel()
    m.add_component(make_resistor("R1"))
    m.add_component(make_resistor("R2"))
    assert m.next_id("resistor") == "R3"

def test_next_id_fills_gap():
    m = CircuitModel()
    m.add_component(make_resistor("R1"))
    m.add_component(make_resistor("R3"))
    assert m.next_id("resistor") == "R2"

def test_next_id_prefix():
    m = CircuitModel()
    assert m.next_id("voltage_source") == "V1"
    assert m.next_id("capacitor") == "C1"
    assert m.next_id("transistor_bjt") == "Q1"

def test_rename_node_propagates():
    m = CircuitModel()
    m.add_component(make_resistor())
    m.add_node(make_node("N1"))
    m.connect_pin("R1", "node_a", "N1")
    m.rename_node("N1", "N10")
    assert m.nodes[0].id == "N10"
    assert m.components[0].pin_connections["node_a"] == "N10"

def test_rename_component_unique():
    m = CircuitModel()
    m.add_component(make_resistor("R1"))
    m.add_component(make_resistor("R2"))
    assert m.rename_component("R1", "R2") is False
    assert m.rename_component("R1", "R99") is True
    assert m.get_component("R99") is not None

def test_is_dirty():
    m = CircuitModel()
    assert m.is_dirty is False
    m.add_component(make_resistor())
    assert m.is_dirty is True
    m.mark_clean()
    assert m.is_dirty is False
```

- [ ] **Step 3: Lancer les tests — vérifier qu'ils échouent**

```
pytest tests/test_editor_model.py -v
```
Attendu : `ImportError` ou `ModuleNotFoundError`

- [ ] **Step 4: Implémenter `circuit_model.py`**

```python
# editor/circuit_model.py
from __future__ import annotations
from dataclasses import dataclass, field

TYPE_PREFIX = {
    "resistor": "R", "capacitor": "C", "inductor": "L",
    "switch": "SW", "voltage_source": "V", "current_source": "I",
    "voltmeter": "VM", "ammeter": "AM", "transistor_bjt": "Q",
    "opamp": "U", "diode": "D",
}

@dataclass
class Pin:
    name: str
    label: str
    offset: tuple[float, float]

@dataclass
class ComponentData:
    id: str
    type: str
    x: float
    y: float
    rotation: int
    params: dict
    pin_connections: dict = field(default_factory=dict)

@dataclass
class NodeData:
    id: str
    x: float
    y: float
    is_gnd: bool = False

class CircuitModel:
    def __init__(self):
        self.name: str = "Nouveau circuit"
        self.dt: float = 1e-5
        self.components: list[ComponentData] = []
        self.nodes: list[NodeData] = []
        self._dirty: bool = False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    def _touch(self):
        self._dirty = True

    def add_component(self, comp: ComponentData) -> None:
        self.components.append(comp)
        self._touch()

    def remove_component(self, comp_id: str) -> None:
        self.components = [c for c in self.components if c.id != comp_id]
        self._touch()

    def add_node(self, node: NodeData) -> None:
        self.nodes.append(node)
        self._touch()

    def remove_node(self, node_id: str) -> None:
        self.nodes = [n for n in self.nodes if n.id != node_id]
        for comp in self.components:
            keys = [k for k, v in comp.pin_connections.items() if v == node_id]
            for k in keys:
                del comp.pin_connections[k]
        self._touch()

    def connect_pin(self, comp_id: str, pin_name: str, node_id: str) -> None:
        comp = self.get_component(comp_id)
        if comp:
            comp.pin_connections[pin_name] = node_id
            self._touch()

    def disconnect_pin(self, comp_id: str, pin_name: str) -> None:
        comp = self.get_component(comp_id)
        if comp and pin_name in comp.pin_connections:
            del comp.pin_connections[pin_name]
            self._touch()

    def next_id(self, comp_type: str) -> str:
        prefix = TYPE_PREFIX.get(comp_type, comp_type[0].upper())
        used = {c.id for c in self.components}
        i = 1
        while f"{prefix}{i}" in used:
            i += 1
        return f"{prefix}{i}"

    def rename_node(self, old_id: str, new_id: str) -> None:
        node = self.get_node(old_id)
        if node:
            node.id = new_id
        for comp in self.components:
            for k, v in comp.pin_connections.items():
                if v == old_id:
                    comp.pin_connections[k] = new_id
        self._touch()

    def rename_component(self, old_id: str, new_id: str) -> bool:
        if any(c.id == new_id for c in self.components):
            return False
        comp = self.get_component(old_id)
        if comp:
            comp.id = new_id
            self._touch()
            return True
        return False

    def get_component(self, comp_id: str) -> ComponentData | None:
        return next((c for c in self.components if c.id == comp_id), None)

    def get_node(self, node_id: str) -> NodeData | None:
        return next((n for n in self.nodes if n.id == node_id), None)
```

- [ ] **Step 5: Lancer les tests — vérifier qu'ils passent**

```
pytest tests/test_editor_model.py -v
```
Attendu : tous PASS

- [ ] **Step 6: Commit**

```bash
git add editor/__init__.py editor/circuit_model.py tests/test_editor_model.py
git commit -m "feat(editor): add CircuitModel dataclasses and operations"
```

---

### Task 2: Lecture/écriture JSON (`io.py`)

**Files:**
- Create: `editor/io.py`
- Test: `tests/test_editor_io.py`

**Interfaces:**
- Consumes: `CircuitModel`, `ComponentData`, `NodeData` de `circuit_model.py`
- Produces:
  - `load_circuit(path: str) -> CircuitModel`
  - `save_circuit(model: CircuitModel, path: str) -> None`

- [ ] **Step 1: Écrire les tests**

```python
# tests/test_editor_io.py
import json, os, pytest
from editor.circuit_model import CircuitModel, ComponentData, NodeData
from editor.io import load_circuit, save_circuit

EXTENDED_JSON = {
    "name": "Test",
    "dt": 1e-5,
    "nodes": [
        {"id": "N1", "x": 200.0, "y": 100.0},
        {"id": "GND", "x": 300.0, "y": 300.0}
    ],
    "components": [
        {"id": "R1", "type": "resistor", "x": 250.0, "y": 100.0,
         "rotation": 0, "node_a": "N1", "node_b": "GND",
         "params": {"resistance": 1000.0}}
    ]
}

LEGACY_JSON = {
    "name": "Legacy",
    "dt": 1e-5,
    "components": [
        {"id": "R1", "type": "resistor", "node_a": "N1", "node_b": "GND",
         "params": {"resistance": 1000.0}},
        {"id": "C1", "type": "capacitor", "node_a": "N1", "node_b": "GND",
         "params": {"capacitance": 1e-6}}
    ]
}

def write_tmp(tmp_path, data):
    p = tmp_path / "circuit.json"
    p.write_text(json.dumps(data))
    return str(p)

def test_load_extended(tmp_path):
    path = write_tmp(tmp_path, EXTENDED_JSON)
    m = load_circuit(path)
    assert m.name == "Test"
    assert len(m.components) == 1
    assert m.components[0].id == "R1"
    assert m.components[0].x == 250.0
    assert m.components[0].pin_connections == {"node_a": "N1", "node_b": "GND"}
    assert len(m.nodes) == 2
    assert m.nodes[0].id == "N1"

def test_load_legacy_creates_positions(tmp_path):
    path = write_tmp(tmp_path, LEGACY_JSON)
    m = load_circuit(path)
    assert len(m.components) == 2
    # les composants doivent avoir des positions (non nulles)
    assert m.components[0].x > 0 or m.components[0].y > 0
    # les nœuds uniques doivent être créés
    node_ids = {n.id for n in m.nodes}
    assert "N1" in node_ids
    assert "GND" in node_ids

def test_load_gnd_is_gnd_node(tmp_path):
    path = write_tmp(tmp_path, EXTENDED_JSON)
    m = load_circuit(path)
    gnd = m.get_node("GND")
    assert gnd is not None
    assert gnd.is_gnd is True

def test_save_and_reload(tmp_path):
    m = CircuitModel()
    m.name = "SaveTest"
    m.dt = 1e-4
    from editor.circuit_model import ComponentData, NodeData
    m.add_node(NodeData(id="N1", x=100.0, y=200.0, is_gnd=False))
    m.add_component(ComponentData(id="R1", type="resistor",
                                   x=150.0, y=200.0, rotation=90,
                                   params={"resistance": 470.0},
                                   pin_connections={"node_a": "N1"}))
    out = str(tmp_path / "out.json")
    save_circuit(m, out)
    m2 = load_circuit(out)
    assert m2.name == "SaveTest"
    assert m2.components[0].rotation == 90
    assert m2.components[0].params["resistance"] == 470.0
    assert m2.nodes[0].id == "N1"

def test_load_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ invalid json }")
    with pytest.raises(Exception):
        load_circuit(str(p))
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```
pytest tests/test_editor_io.py -v
```
Attendu : `ImportError`

- [ ] **Step 3: Implémenter `io.py`**

```python
# editor/io.py
from __future__ import annotations
import json
import math
from editor.circuit_model import CircuitModel, ComponentData, NodeData

PIN_KEYS = {
    "resistor": ["node_a", "node_b"],
    "capacitor": ["node_a", "node_b"],
    "inductor": ["node_a", "node_b"],
    "switch": ["node_a", "node_b"],
    "voltage_source": ["node_pos", "node_neg"],
    "current_source": ["node_pos", "node_neg"],
    "voltmeter": ["node_a", "node_b"],
    "ammeter": ["node_a", "node_b"],
    "transistor_bjt": ["node_base", "node_collector", "node_emitter"],
    "opamp": ["node_plus", "node_minus", "node_out"],
    "diode": ["node_a", "node_k"],
}

def load_circuit(path: str) -> CircuitModel:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = CircuitModel()
    model.name = data.get("name", "Circuit")
    model.dt = data.get("dt", 1e-5)

    raw_comps = data.get("components", [])
    has_positions = any("x" in c for c in raw_comps)

    # Charger les nœuds explicites
    node_map: dict[str, NodeData] = {}
    for n in data.get("nodes", []):
        nd = NodeData(id=n["id"], x=float(n["x"]), y=float(n["y"]),
                      is_gnd=n["id"] == "GND" or n["id"].startswith("GND_"))
        node_map[nd.id] = nd

    # Charger les composants
    COLS = 5
    SPACING = 150
    for idx, c in enumerate(raw_comps):
        comp_type = c["type"]
        pin_connections = {}
        for key in PIN_KEYS.get(comp_type, []):
            if key in c:
                pin_connections[key] = c[key]

        if has_positions and "x" in c:
            cx, cy = float(c["x"]), float(c["y"])
        else:
            col = idx % COLS
            row = idx // COLS
            cx = 100.0 + col * SPACING
            cy = 100.0 + row * SPACING

        comp = ComponentData(
            id=c["id"], type=comp_type,
            x=cx, y=cy,
            rotation=int(c.get("rotation", 0)),
            params=dict(c.get("params", {})),
            pin_connections=pin_connections,
        )
        model.add_component(comp)

        # Créer les nœuds manquants depuis les connexions
        for node_id in pin_connections.values():
            if node_id not in node_map:
                is_gnd = node_id == "GND" or node_id.startswith("GND_")
                nd = NodeData(id=node_id, x=cx + 80, y=cy + 80, is_gnd=is_gnd)
                node_map[node_id] = nd

    for nd in node_map.values():
        model.add_node(nd)

    model.mark_clean()
    return model


def save_circuit(model: CircuitModel, path: str) -> None:
    nodes = [{"id": n.id, "x": n.x, "y": n.y} for n in model.nodes]

    components = []
    for c in model.components:
        obj: dict = {
            "id": c.id,
            "type": c.type,
            "x": c.x,
            "y": c.y,
            "rotation": c.rotation,
        }
        obj.update(c.pin_connections)
        obj["params"] = c.params
        components.append(obj)

    data = {"name": model.name, "dt": model.dt,
            "nodes": nodes, "components": components}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    model.mark_clean()
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```
pytest tests/test_editor_io.py -v
```
Attendu : tous PASS

- [ ] **Step 5: Commit**

```bash
git add editor/io.py tests/test_editor_io.py
git commit -m "feat(editor): add JSON load/save with extended format and legacy fallback"
```

---

### Task 3: Barre d'outils (`toolbar.py`)

**Files:**
- Create: `editor/toolbar.py`

**Interfaces:**
- Consumes: `tk.Frame`, callbacks passés par `main.py`
- Produces: `Toolbar(parent, on_new, on_open, on_save, on_save_as)` — `tk.Frame`

Note : pas de tests unitaires pour les widgets Tkinter purs — vérification visuelle dans Task 7.

- [ ] **Step 1: Implémenter `toolbar.py`**

```python
# editor/toolbar.py
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
```

- [ ] **Step 2: Commit**

```bash
git add editor/toolbar.py
git commit -m "feat(editor): add Toolbar widget with tooltips"
```

---

### Task 4: Canvas 2D — rendu statique et COMPONENT_TEMPLATES (`editor_canvas.py` partie 1)

**Files:**
- Create: `editor/editor_canvas.py`

**Interfaces:**
- Consumes: `CircuitModel`, `ComponentData`, `NodeData` de `circuit_model.py`
- Produces: `EditorCanvas(parent, model)` — `tk.Frame` avec méthodes :
  - `redraw() -> None` — redessine tout depuis le modèle
  - `set_on_selection_change(callback: Callable[[str|None, str|None], None]) -> None`
    - appelé avec `(comp_id, node_id)` — l'un des deux est None
  - `set_on_model_change(callback: Callable[[], None]) -> None`
  - `drop_component(comp_type: str, canvas_x: float, canvas_y: float) -> None`

- [ ] **Step 1: Implémenter les COMPONENT_TEMPLATES et la fonction `rotate_offset`**

```python
# editor/editor_canvas.py
from __future__ import annotations
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
```

- [ ] **Step 2: Implémenter la méthode `redraw` (rendu complet)**

Ajouter après les fonctions utilitaires, dans la classe `EditorCanvas` :

```python
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
        import copy
        comp = ComponentData(id=comp_id, type=comp_type,
                              x=canvas_x, y=canvas_y, rotation=0,
                              params=copy.deepcopy(template["params"]),
                              pin_connections={})
        self.model.add_component(comp)
        self.redraw()
        self._notify_model()
```

- [ ] **Step 3: Commit**

```bash
git add editor/editor_canvas.py
git commit -m "feat(editor): add EditorCanvas with COMPONENT_TEMPLATES and static redraw"
```

---

### Task 5: Canvas 2D — machine à états et interactions souris

**Files:**
- Modify: `editor/editor_canvas.py`

**Interfaces:**
- Consumes: tout ce qui existe dans `editor_canvas.py` (Task 4)
- Produces: interactions souris complètes (sélection, déplacement, connexion, suppression, double-clic)

- [ ] **Step 1: Ajouter `_bind_events` et les helpers de hit-test**

```python
    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Delete>", self._on_delete)
        self.canvas.bind("<KeyPress-Delete>", self._on_delete)
        self.canvas.focus_set()

    def _item_at(self, x, y) -> tuple[str, str] | None:
        """Retourne (kind, id) pour l'item Tkinter le plus proche : 'comp', 'node', 'pin', 'wire'."""
        items = self.canvas.find_overlapping(x-2, y-2, x+2, y+2)
        for item in reversed(items):
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("pin_"):
                    parts = tag.split("_", 2)  # pin_{comp_id}_{pin_name}
                    return ("pin", parts[1], parts[2])
                if tag.startswith("node_"):
                    return ("node", tag[5:])
                if tag.startswith("wire_"):
                    parts = tag.split("_", 2)  # wire_{comp_id}_{pin_name}
                    return ("wire", parts[1], parts[2])
                if tag.startswith("comp_"):
                    return ("comp", tag[5:])
        return None
```

- [ ] **Step 2: Implémenter `_on_press`**

```python
    def _on_press(self, event):
        self.canvas.focus_set()
        hit = self._item_at(event.x, event.y)
        self._drag_start = (event.x, event.y)

        if hit is None:
            self._deselect()
            return

        kind = hit[0]

        if kind == "pin":
            _, comp_id, pin_name = hit
            self._state = "CONNECTING"
            self._connect_source = (comp_id, pin_name)
            self._connect_line = None

        elif kind == "node":
            node_id = hit[1]
            self._selected_comp = None
            self._selected_node = node_id
            self._selected_wire = None
            self._state = "SELECTED"
            self.redraw()
            self._notify_selection()

        elif kind == "wire":
            _, comp_id, pin_name = hit
            self._selected_comp = None
            self._selected_node = None
            self._selected_wire = (comp_id, pin_name)
            self._state = "SELECTED"
            self.redraw()
            self._notify_selection()

        elif kind == "comp":
            comp_id = hit[1]
            self._selected_comp = comp_id
            self._selected_node = None
            self._selected_wire = None
            self._state = "SELECTED"
            self.redraw()
            self._notify_selection()
```

- [ ] **Step 3: Implémenter `_on_motion`**

```python
    def _on_motion(self, event):
        if self._state == "SELECTED":
            dx = abs(event.x - self._drag_start[0])
            dy = abs(event.y - self._drag_start[1])
            if dx > 3 or dy > 3:
                self._state = "DRAGGING"

        elif self._state == "DRAGGING":
            dx = event.x - self._drag_start[0]
            dy = event.y - self._drag_start[1]
            self._drag_start = (event.x, event.y)
            if self._selected_comp:
                comp = self.model.get_component(self._selected_comp)
                if comp:
                    comp.x += dx
                    comp.y += dy
                    self.model._touch()
            elif self._selected_node:
                node = self.model.get_node(self._selected_node)
                if node:
                    node.x += dx
                    node.y += dy
                    self.model._touch()
            self.redraw()

        elif self._state == "CONNECTING":
            if self._connect_line:
                self.canvas.delete(self._connect_line)
            src_comp_id, pin_name = self._connect_source
            comp = self.model.get_component(src_comp_id)
            template = COMPONENT_TEMPLATES.get(comp.type, {})
            pin = next((p for p in template.get("pins", []) if p.name == pin_name), None)
            if pin:
                px, py = pin_abs_pos(comp, pin)
                self._connect_line = self.canvas.create_line(
                    px, py, event.x, event.y,
                    fill="#0055ff", width=2, dash=(4, 4))
```

- [ ] **Step 4: Implémenter `_on_release` et `_on_double_click`**

```python
    def _on_release(self, event):
        if self._state == "DRAGGING":
            self._state = "SELECTED"
            self._notify_model()

        elif self._state == "CONNECTING":
            if self._connect_line:
                self.canvas.delete(self._connect_line)
                self._connect_line = None
            hit = self._item_at(event.x, event.y)
            if hit and hit[0] == "node":
                comp_id, pin_name = self._connect_source
                self.model.connect_pin(comp_id, pin_name, hit[1])
                self._notify_model()
            self._connect_source = None
            self._state = "IDLE"
            self.redraw()

    def _on_double_click(self, event):
        hit = self._item_at(event.x, event.y)
        if hit is None:
            # Créer un nouveau nœud
            existing_ids = {n.id for n in self.model.nodes}
            i = 1
            while f"N{i}" in existing_ids:
                i += 1
            node = NodeData(id=f"N{i}", x=float(event.x), y=float(event.y), is_gnd=False)
            self.model.add_node(node)
            self.redraw()
            self._notify_model()

    def _deselect(self):
        self._selected_comp = None
        self._selected_node = None
        self._selected_wire = None
        self._state = "IDLE"
        self.redraw()
        self._notify_selection()
```

- [ ] **Step 5: Implémenter `_on_delete`**

```python
    def _on_delete(self, event):
        if self._selected_comp:
            self.model.remove_component(self._selected_comp)
            self._selected_comp = None
            self.redraw()
            self._notify_model()
            self._notify_selection()

        elif self._selected_node:
            node_id = self._selected_node
            # Vérifier si connecté
            connected_pins = [
                (c.id, pn)
                for c in self.model.components
                for pn, nid in c.pin_connections.items()
                if nid == node_id
            ]
            if connected_pins:
                from tkinter import messagebox
                ok = messagebox.askyesno(
                    "Supprimer le nœud",
                    f"Le nœud {node_id} est connecté à {len(connected_pins)} patte(s).\n"
                    "Supprimer quand même et retirer les liaisons ?")
                if not ok:
                    return
            self.model.remove_node(node_id)
            self._selected_node = None
            self.redraw()
            self._notify_model()
            self._notify_selection()

        elif self._selected_wire:
            comp_id, pin_name = self._selected_wire
            self.model.disconnect_pin(comp_id, pin_name)
            self._selected_wire = None
            self.redraw()
            self._notify_model()
            self._notify_selection()
```

- [ ] **Step 6: Commit**

```bash
git add editor/editor_canvas.py
git commit -m "feat(editor): add state machine and mouse interactions to EditorCanvas"
```

---

### Task 6: Panneau gauche — drag depuis la liste (`component_panel.py`)

**Files:**
- Create: `editor/component_panel.py`

**Interfaces:**
- Consumes: `EditorCanvas.drop_component(comp_type, canvas_x, canvas_y)`
- Produces: `ComponentPanel(parent, canvas: EditorCanvas, root: tk.Tk)` — `tk.Frame`
  - méthode `add_gnd_node(canvas_x, canvas_y)` — ajoute un nœud GND via le modèle

- [ ] **Step 1: Implémenter `component_panel.py`**

```python
# editor/component_panel.py
import tkinter as tk
from editor.circuit_model import NodeData

COMPONENT_TYPES = [
    "resistor", "capacitor", "inductor", "switch",
    "voltage_source", "current_source",
    "voltmeter", "ammeter",
    "transistor_bjt", "opamp", "diode",
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
```

- [ ] **Step 2: Commit**

```bash
git add editor/component_panel.py
git commit -m "feat(editor): add ComponentPanel with cross-widget drag-and-drop"
```

---

### Task 7: Panneau droit — propriétés (`properties_panel.py`)

**Files:**
- Create: `editor/properties_panel.py`

**Interfaces:**
- Consumes: `CircuitModel`, `ComponentData`, `NodeData`, `COMPONENT_TEMPLATES`
- Produces: `PropertiesPanel(parent, model: CircuitModel, canvas: EditorCanvas)` — `tk.Frame`
  - méthode `show_component(comp_id: str) -> None`
  - méthode `show_node(node_id: str) -> None`
  - méthode `show_empty() -> None`

- [ ] **Step 1: Implémenter `properties_panel.py`**

```python
# editor/properties_panel.py
import tkinter as tk
from editor.editor_canvas import COMPONENT_TEMPLATES

class PropertiesPanel(tk.Frame):
    def __init__(self, parent, model, canvas):
        super().__init__(parent, width=180, bd=1, relief=tk.SUNKEN)
        self.pack_propagate(False)
        self._model = model
        self._canvas = canvas
        self._widgets = []
        self._err_label = None
        tk.Label(self, text="Propriétés", font=("TkDefaultFont", 9, "bold")).pack(pady=(4, 2))
        self._body = tk.Frame(self)
        self._body.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.show_empty()

    def _clear(self):
        for w in self._widgets:
            w.destroy()
        self._widgets = []
        self._err_label = None

    def show_empty(self):
        self._clear()
        lbl = tk.Label(self._body, text="Sélectionnez un composant\nou un nœud.",
                        font=("TkDefaultFont", 9), fg="gray", justify=tk.CENTER)
        lbl.pack(pady=20)
        self._widgets.append(lbl)

    def show_component(self, comp_id: str):
        self._clear()
        comp = self._model.get_component(comp_id)
        if comp is None:
            self.show_empty()
            return

        # ID
        tk.Label(self._body, text="ID :", anchor="w").pack(fill=tk.X)
        id_var = tk.StringVar(value=comp.id)
        err_lbl = tk.Label(self._body, text="", fg="red", font=("TkDefaultFont", 8))
        err_lbl.pack(fill=tk.X)
        self._err_label = err_lbl
        self._widgets.append(err_lbl)

        def on_id_change(*_):
            new_id = id_var.get().strip()
            if not new_id or new_id == comp.id:
                err_lbl.config(text="")
                return
            ok = self._model.rename_component(comp.id, new_id)
            if ok:
                err_lbl.config(text="")
                self._canvas.redraw()
                self._canvas._notify_model()
            else:
                err_lbl.config(text=f"ID '{new_id}' déjà utilisé")

        id_entry = tk.Entry(self._body, textvariable=id_var)
        id_entry.pack(fill=tk.X)
        id_entry.bind("<FocusOut>", on_id_change)
        id_entry.bind("<Return>", on_id_change)
        self._widgets.append(id_entry)

        # Type
        tk.Label(self._body, text=f"Type : {comp.type}", anchor="w",
                  font=("TkDefaultFont", 9, "italic")).pack(fill=tk.X, pady=(4, 0))

        # Rotation
        def rotate():
            comp.rotation = (comp.rotation + 90) % 360
            self._model._touch()
            self._canvas.redraw()
            self._canvas._notify_model()
            rot_lbl.config(text=f"Rotation : {comp.rotation}°")

        rot_lbl = tk.Label(self._body, text=f"Rotation : {comp.rotation}°", anchor="w")
        rot_lbl.pack(fill=tk.X, pady=(4, 0))
        rot_btn = tk.Button(self._body, text="↻ Tourner 90°", command=rotate)
        rot_btn.pack(fill=tk.X, pady=(0, 6))
        self._widgets += [rot_lbl, rot_btn]

        # Params
        template = COMPONENT_TEMPLATES.get(comp.type, {})
        param_keys = list(template.get("params", {}).keys())
        tk.Label(self._body, text="Paramètres :", anchor="w",
                  font=("TkDefaultFont", 9, "bold")).pack(fill=tk.X, pady=(4, 0))
        param_vars = {}
        for key in param_keys:
            row = tk.Frame(self._body)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{key} :", width=14, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(comp.params.get(key, "")))
            param_vars[key] = var

            def make_updater(k, v):
                def update(*_):
                    raw = v.get().strip()
                    try:
                        val = float(raw)
                    except ValueError:
                        val = raw
                    comp.params[k] = val
                    self._model._touch()
                    self._canvas._notify_model()
                return update

            ent = tk.Entry(row, textvariable=var, width=10)
            ent.pack(side=tk.LEFT)
            updater = make_updater(key, var)
            ent.bind("<FocusOut>", updater)
            ent.bind("<Return>", updater)
            self._widgets.append(row)

        # Connexions
        tk.Label(self._body, text="Pattes :", anchor="w",
                  font=("TkDefaultFont", 9, "bold")).pack(fill=tk.X, pady=(6, 0))
        pins = template.get("pins", [])
        for pin in pins:
            node_id = comp.pin_connections.get(pin.name, "—")
            lbl = tk.Label(self._body, text=f"  {pin.name} → {node_id}", anchor="w",
                            font=("TkDefaultFont", 8))
            lbl.pack(fill=tk.X)
            self._widgets.append(lbl)

    def show_node(self, node_id: str):
        self._clear()
        node = self._model.get_node(node_id)
        if node is None:
            self.show_empty()
            return

        tk.Label(self._body, text="Nœud", font=("TkDefaultFont", 9, "bold"), anchor="w").pack(fill=tk.X)

        tk.Label(self._body, text="ID :", anchor="w").pack(fill=tk.X)
        err_lbl = tk.Label(self._body, text="", fg="red", font=("TkDefaultFont", 8))
        err_lbl.pack(fill=tk.X)
        self._widgets.append(err_lbl)
        id_var = tk.StringVar(value=node.id)

        def on_node_id_change(*_):
            new_id = id_var.get().strip()
            if not new_id or new_id == node.id:
                return
            if self._model.get_node(new_id) is not None:
                err_lbl.config(text=f"ID '{new_id}' déjà utilisé")
                return
            err_lbl.config(text="")
            self._model.rename_node(node.id, new_id)
            self._canvas.redraw()
            self._canvas._notify_model()

        id_entry = tk.Entry(self._body, textvariable=id_var)
        id_entry.pack(fill=tk.X)
        id_entry.bind("<FocusOut>", on_node_id_change)
        id_entry.bind("<Return>", on_node_id_change)
        self._widgets.append(id_entry)

        tk.Label(self._body, text=f"x : {node.x:.1f}", anchor="w").pack(fill=tk.X, pady=(6, 0))
        tk.Label(self._body, text=f"y : {node.y:.1f}", anchor="w").pack(fill=tk.X)
```

- [ ] **Step 2: Commit**

```bash
git add editor/properties_panel.py
git commit -m "feat(editor): add PropertiesPanel for component and node editing"
```

---

### Task 8: Fenêtre principale et point d'entrée (`main.py`)

**Files:**
- Create: `editor/main.py`

**Interfaces:**
- Consumes: tous les widgets précédents + `io.py`
- Produces: application Tkinter complète et fonctionnelle

- [ ] **Step 1: Implémenter `main.py`**

```python
# editor/main.py
import tkinter as tk
from tkinter import filedialog, messagebox

from editor.circuit_model import CircuitModel
from editor.editor_canvas import EditorCanvas
from editor.component_panel import ComponentPanel
from editor.properties_panel import PropertiesPanel
from editor.toolbar import Toolbar
from editor import io

class EditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.model = CircuitModel()
        self._current_file: str | None = None

        root.title("Éditeur de circuit")
        root.geometry("1100x700")

        # Barre d'outils
        self.toolbar = Toolbar(root,
                                on_new=self._new,
                                on_open=self._open,
                                on_save=self._save,
                                on_save_as=self._save_as)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Zone principale
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas au centre
        self.canvas = EditorCanvas(main_frame, self.model)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Panneau droit
        self.props = PropertiesPanel(main_frame, self.model, self.canvas)
        self.props.pack(side=tk.RIGHT, fill=tk.Y)

        # Panneau gauche
        self.comp_panel = ComponentPanel(main_frame, self.canvas, root)
        self.comp_panel.pack(side=tk.LEFT, fill=tk.Y, before=self.canvas)

        # Callbacks
        self.canvas.set_on_selection_change(self._on_selection)
        self.canvas.set_on_model_change(self._on_model_change)

        # Raccourcis clavier
        root.bind("<Control-n>", lambda e: self._new())
        root.bind("<Control-o>", lambda e: self._open())
        root.bind("<Control-s>", lambda e: self._save())
        root.bind("<Control-S>", lambda e: self._save_as())

        # Fermeture
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._update_title()

    def _update_title(self):
        prefix = "* " if self.model.is_dirty else ""
        name = self.model.name or "Nouveau circuit"
        self.root.title(f"{prefix}{name} — Éditeur de circuit")

    def _on_selection(self, comp_id, node_id):
        if comp_id:
            self.props.show_component(comp_id)
        elif node_id:
            self.props.show_node(node_id)
        else:
            self.props.show_empty()

    def _on_model_change(self):
        self._update_title()

    def _confirm_unsaved(self) -> bool:
        if not self.model.is_dirty:
            return True
        return messagebox.askyesno(
            "Modifications non sauvegardées",
            "Des modifications non sauvegardées seront perdues. Continuer ?")

    def _new(self):
        if not self._confirm_unsaved():
            return
        self.model = CircuitModel()
        self._current_file = None
        self.canvas.model = self.model
        self.props._model = self.model
        self.canvas.redraw()
        self.props.show_empty()
        self._update_title()

    def _open(self):
        if not self._confirm_unsaved():
            return
        path = filedialog.askopenfilename(
            title="Ouvrir un circuit",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")],
            initialdir="circuits")
        if not path:
            return
        try:
            self.model = io.load_circuit(path)
        except Exception as e:
            messagebox.showerror("Erreur de chargement", str(e))
            return
        self._current_file = path
        self.canvas.model = self.model
        self.props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self.props.show_empty()
        self._update_title()

    def _save(self):
        if self._current_file is None:
            self._save_as()
            return
        try:
            io.save_circuit(self.model, self._current_file)
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", str(e))
            return
        self._update_title()

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title="Enregistrer sous",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir="circuits")
        if not path:
            return
        self._current_file = path
        self._save()

    def _on_close(self):
        if self._confirm_unsaved():
            self.root.destroy()


def main():
    root = tk.Tk()
    EditorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Vérifier le lancement**

```
python -m editor.main
```
Attendu : fenêtre Tkinter avec toolbar, canvas blanc, panneau gauche avec la liste, panneau droit vide.

- [ ] **Step 3: Tester manuellement les interactions clés**
  - Glisser un `resistor` depuis la liste → vérifie qu'il apparaît sur le canvas
  - Double-cliquer sur le canvas vide → vérifie qu'un nœud `N1` apparaît
  - Presser sur une patte rouge, glisser vers le nœud → vérifie que la liaison est dessinée et la patte devient verte
  - Sélectionner un composant → vérifie que le panneau droit affiche ses propriétés
  - Modifier la résistance dans le panneau → vérifie que la valeur est bien mise à jour
  - Tourner un composant → vérifie que les pattes bougent
  - Sélectionner et appuyer Suppr → vérifie la suppression
  - Ctrl+S → vérifier la sauvegarde (créer un fichier dans `circuits/`)
  - Ctrl+O → ouvrir un fichier existant (`circuits/rc_filter.json`) → vérifie la disposition en grille

- [ ] **Step 4: Commit**

```bash
git add editor/main.py
git commit -m "feat(editor): add EditorApp main window, wiring all panels together"
```

---

### Task 9: Tests d'intégration et vérification finale

**Files:**
- Test: `tests/test_editor_io.py` (compléter si besoin)

- [ ] **Step 1: Lancer toute la suite de tests**

```
pytest tests/test_editor_model.py tests/test_editor_io.py -v
```
Attendu : tous PASS

- [ ] **Step 2: Ouvrir chacun des circuits d'exemple et vérifier la disposition**

```
python -m editor.main
```
Ouvrir successivement :
- `circuits/rc_filter.json` → 3 composants disposés en grille, 2 nœuds auto-créés
- `circuits/rl_transient.json` → 5 composants en grille
- `circuits/diode_bridge.json` → vérifier les diodes avec pattes `node_a`/`node_k`

- [ ] **Step 3: Sauvegarder un circuit modifié et vérifier le JSON produit**

Ajouter un composant, relier une patte à un nœud, sauvegarder. Vérifier dans le JSON que :
- La clé `"nodes"` est présente avec les bonnes coordonnées
- Chaque composant a `"x"`, `"y"`, `"rotation"`
- Les connexions de pattes (`"node_a"`, etc.) sont correctes

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "feat(editor): complete circuit editor — all tasks done"
```
