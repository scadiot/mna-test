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
