from editor.validation import validate_for_simulation
from editor.circuit_model import CircuitModel, ComponentData, NodeData


def _model_with(components, nodes):
    m = CircuitModel()
    for n in nodes:
        m.add_node(n)
    for c in components:
        m.add_component(c)
    return m


def test_valid_circuit_returns_no_errors():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "N1", "node_b": "GND"})],
        [NodeData(id="N1", x=0, y=0), NodeData(id="GND", x=0, y=0, is_gnd=True)])
    assert validate_for_simulation(m) == []


def test_empty_circuit_is_invalid():
    assert validate_for_simulation(CircuitModel()) != []


def test_unconnected_pin_is_reported():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "GND"})],
        [NodeData(id="GND", x=0, y=0, is_gnd=True)])
    errors = validate_for_simulation(m)
    assert any("node_b" in e for e in errors)


def test_missing_gnd_is_reported():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "N1", "node_b": "N2"})],
        [NodeData(id="N1", x=0, y=0), NodeData(id="N2", x=0, y=0)])
    errors = validate_for_simulation(m)
    assert any("GND" in e for e in errors)
