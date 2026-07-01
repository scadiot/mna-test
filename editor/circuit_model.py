from __future__ import annotations
from dataclasses import dataclass, field

TYPE_PREFIX = {
    "resistor": "R", "capacitor": "C", "inductor": "L",
    "switch": "SW", "voltage_source": "V", "current_source": "I",
    "voltmeter": "VM", "ammeter": "AM", "transistor_bjt": "Q",
    "opamp": "U", "diode": "D", "potentiometer": "POT",
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

    def toggle_switch(self, comp_id: str) -> bool:
        """Inverse l'état closed d'un switch. Renvoie le nouvel état.

        No-op renvoyant False si le composant est absent ou n'a pas de
        paramètre 'closed'.
        """
        comp = self.get_component(comp_id)
        if comp is None or "closed" not in comp.params:
            return False
        comp.params["closed"] = not comp.params["closed"]
        self._touch()
        return comp.params["closed"]

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
