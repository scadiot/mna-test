from __future__ import annotations
import json
from editor.circuit_model import CircuitModel, ComponentData, NodeData

PIN_KEYS = {
    "resistor": ["node_a", "node_b"],
    "capacitor": ["node_a", "node_b"],
    "inductor": ["node_a", "node_b"],
    "switch": ["node_a", "node_b"],
    "voltage_source": ["node_pos", "node_neg"],
    "current_source": ["node_a", "node_b"],
    "voltmeter": ["node_a", "node_b"],
    "ammeter": ["node_a", "node_b"],
    "transistor_bjt": ["node_base", "node_collector", "node_emitter"],
    "opamp": ["node_plus", "node_minus", "node_out"],
    "diode": ["node_anode", "node_cathode"],
    "potentiometer": ["node_a", "node_wiper", "node_b"],
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
