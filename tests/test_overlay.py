from editor.overlay import voltage_color, state_indicator
from simulator.components import Switch, BJT, Diode


def test_voltage_color_extremes():
    assert voltage_color(0.0, 0.0, 10.0) == "#0000ff"   # bleu = min
    assert voltage_color(10.0, 0.0, 10.0) == "#ff0000"  # rouge = max


def test_voltage_color_clamps_and_handles_flat_range():
    # hors bornes -> clampé
    assert voltage_color(-5.0, 0.0, 10.0) == "#0000ff"
    assert voltage_color(99.0, 0.0, 10.0) == "#ff0000"
    # plage plate -> pas de division par zéro, couleur médiane
    c = voltage_color(3.0, 3.0, 3.0)
    assert c.startswith("#") and len(c) == 7


def test_state_indicator_switch_returns_none():
    sw_open = Switch("SW1", "A", "B", closed=False)
    sw_closed = Switch("SW2", "A", "B", closed=True)
    assert state_indicator(sw_open, {}) is None
    assert state_indicator(sw_closed, {}) is None


def test_state_indicator_bjt():
    q = BJT("Q1", "b", "c", "e")
    assert state_indicator(q, {"current": 0.0})[0] == "bloqué"
    assert state_indicator(q, {"current": 1e-3, "saturated": True})[0] == "saturé"
    assert state_indicator(q, {"current": 1e-3, "saturated": False})[0] == "actif"


def test_state_indicator_diode():
    d = Diode("D1", "a", "k")
    assert state_indicator(d, {"current": 1e-3})[0] == "passante"
    assert state_indicator(d, {"current": 0.0})[0] == "bloquée"


def test_state_indicator_other_returns_none():
    from simulator.components import Resistor
    assert state_indicator(Resistor("R1", "a", "b", 1000.0), {"current": 1.0}) is None
