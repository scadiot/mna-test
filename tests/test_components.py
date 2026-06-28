import pytest
import numpy as np
from simulator.components import Resistor

def test_resistor_stamp_between_two_nodes():
    """Résistance 1kΩ entre N1 (idx=0) et N2 (idx=1) : conductance 0.001 S."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    node_map = {"N1": 0, "N2": 1}
    r = Resistor("R1", "N1", "N2", 1000.0)
    r.stamp(G, b, node_map, {}, dt=1e-5, t=0.0, prev_state={})
    assert G[0, 0] == pytest.approx(0.001)
    assert G[1, 1] == pytest.approx(0.001)
    assert G[0, 1] == pytest.approx(-0.001)
    assert G[1, 0] == pytest.approx(-0.001)
    assert np.all(b == 0.0)

def test_resistor_stamp_to_gnd():
    """Résistance 500Ω entre N1 et GND : seule la diagonale N1 est modifiée."""
    G = np.zeros((1, 1))
    b = np.zeros(1)
    node_map = {"N1": 0}
    r = Resistor("R1", "N1", "GND", 500.0)
    r.stamp(G, b, node_map, {}, dt=1e-5, t=0.0, prev_state={})
    assert G[0, 0] == pytest.approx(0.002)   # 1/500

def test_resistor_get_state():
    """get_state() calcule tension et courant depuis le vecteur solution."""
    node_map = {"N1": 0, "N2": 1}
    x = np.array([5.0, 2.0])   # V_N1=5V, V_N2=2V
    r = Resistor("R1", "N1", "N2", 1000.0)
    state = r.get_state(x, node_map, {})
    assert state["voltage"] == pytest.approx(3.0)        # 5-2
    assert state["current"] == pytest.approx(0.003)      # 3/1000

def test_resistor_does_not_need_branch():
    r = Resistor("R1", "N1", "GND", 1000.0)
    assert r.needs_branch() is False

def test_resistor_get_nodes():
    r = Resistor("R1", "N1", "N2", 1000.0)
    assert set(r.get_nodes()) == {"N1", "N2"}
