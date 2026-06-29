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
