import pytest
import numpy as np
from simulator.components import Resistor, Capacitor, Inductor, Switch, Voltmeter, Ammeter
from simulator.components import VoltageSource, CurrentSource
from simulator.components import BJT, OpAmp, Potentiometer
from simulator.sources import DCSource

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


# ── Tests Condensateur (Task 5) ───────────────────────────────────────────────

def test_capacitor_first_step():
    """Premier pas (v_prev=0) : seule la conductance compagnon est stampée."""
    G = np.zeros((1, 1))
    b = np.zeros(1)
    dt = 1e-5
    cap = Capacitor("C1", "N1", "GND", capacitance=1e-6)
    cap.stamp(G, b, {"N1": 0}, {}, dt=dt, t=0.0, prev_state={"voltage": 0.0, "current": 0.0})
    g_eq = 1e-6 / dt   # = 0.1 S
    assert G[0, 0] == pytest.approx(g_eq)
    assert b[0] == pytest.approx(0.0)   # I_companion = 0 au premier pas


def test_capacitor_companion_current():
    """Deuxième pas (v_prev=2V) : la source compagnon injecte G_eq*v_prev."""
    G = np.zeros((1, 1))
    b = np.zeros(1)
    dt = 1e-5
    cap = Capacitor("C1", "N1", "GND", capacitance=1e-6)
    cap.stamp(G, b, {"N1": 0}, {}, dt=dt, t=dt, prev_state={"voltage": 2.0, "current": 0.0})
    g_eq = 1e-6 / dt
    # La source compagnon injecte g_eq * v_prev depuis GND vers N1
    assert b[0] == pytest.approx(g_eq * 2.0)


# ── Tests Bobine (Task 5) ─────────────────────────────────────────────────────

def test_inductor_first_step():
    """Premier pas (i_prev=0) : seule la conductance compagnon est stampée."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    dt = 1e-3
    ind = Inductor("L1", "N1", "N2", inductance=1e-3)
    ind.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=dt, t=0.0, prev_state={"voltage": 0.0, "current": 0.0})
    g_eq = dt / 1e-3   # = 1.0 S
    assert G[0, 0] == pytest.approx(g_eq)
    assert G[1, 1] == pytest.approx(g_eq)
    assert G[0, 1] == pytest.approx(-g_eq)
    assert np.all(b == 0.0)


def test_inductor_companion_current():
    """Deuxième pas (i_prev=0.5A) : la source compagnon injecte i_prev."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    dt = 1e-3
    ind = Inductor("L1", "N1", "N2", inductance=1e-3)
    ind.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=dt, t=dt, prev_state={"voltage": 0.0, "current": 0.5})
    # Le courant de branche i(t)=g_eq*v(t)+i_prev circule de N1 vers N2 :
    # i_prev quitte N1 (injection négative) et entre dans N2.
    assert b[0] == pytest.approx(-0.5)
    assert b[1] == pytest.approx(0.5)


# ── Tests Switch (Task 6) ─────────────────────────────────────────────────────

def test_switch_open():
    """Interrupteur ouvert = résistance très grande (1e9 Ω)."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    sw = Switch("SW1", "N1", "N2", closed=False)
    sw.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=1e-5, t=0.0, prev_state={})
    assert G[0, 0] == pytest.approx(1e-9)

def test_switch_closed():
    """Interrupteur fermé = résistance très faible (1e-6 Ω)."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    sw = Switch("SW1", "N1", "N2", closed=True)
    sw.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=1e-5, t=0.0, prev_state={})
    assert G[0, 0] == pytest.approx(1e6)   # 1/1e-6

def test_switch_toggle():
    """toggle() inverse l'état ouvert/fermé."""
    sw = Switch("SW1", "N1", "N2", closed=False)
    assert sw.closed is False
    sw.toggle()
    assert sw.closed is True
    # Vérifie que params reflète l'état de l'interrupteur
    assert sw.params["closed"] == sw.closed

def test_voltmeter_is_high_impedance():
    """Voltmètre = résistance 1e9 Ω (invisible pour le circuit)."""
    G = np.zeros((1, 1))
    b = np.zeros(1)
    vm = Voltmeter("VM1", "N1", "GND", history_size=100)
    vm.stamp(G, b, {"N1": 0}, {}, dt=1e-5, t=0.0, prev_state={})
    assert G[0, 0] == pytest.approx(1e-9)

def test_voltmeter_records_history():
    vm = Voltmeter("VM1", "N1", "GND")
    assert vm.records_history is True
    assert vm.history_size == 500

def test_ammeter_needs_branch():
    am = Ammeter("AM1", "N1", "N2", history_size=200)
    assert am.needs_branch() is True
    assert am.records_history is True

def test_ammeter_stamp():
    """Ampèremètre = source de tension 0V : stamp comme une source de tension."""
    G = np.zeros((3, 3))   # 2 nœuds + 1 branche
    b = np.zeros(3)
    # N1=0, N2=1, branche AM1=2
    am = Ammeter("AM1", "N1", "N2")
    am.stamp(G, b, {"N1": 0, "N2": 1}, {"AM1": 2}, dt=1e-5, t=0.0, prev_state={})
    # Ligne de branche : G[2,0]=1, G[2,1]=-1
    assert G[2, 0] == pytest.approx(1.0)
    assert G[2, 1] == pytest.approx(-1.0)
    # Colonnes KCL : G[0,2]=1, G[1,2]=-1
    assert G[0, 2] == pytest.approx(1.0)
    assert G[1, 2] == pytest.approx(-1.0)
    assert b[2] == pytest.approx(0.0)   # tension imposée = 0 V


# ── Tests VoltageSource et CurrentSource (Task 7) ────────────────────────────

def test_voltage_source_stamp():
    """Source 5V DC entre N1 et GND : impose V[N1]=5V via la ligne de branche."""
    G = np.zeros((2, 2))   # 1 nœud N1 + 1 branche V1
    b = np.zeros(2)
    src = VoltageSource("V1", "N1", "GND", DCSource(5.0))
    src.stamp(G, b, {"N1": 0}, {"V1": 1}, dt=1e-5, t=0.0, prev_state={})
    # Ligne de branche [1] : G[1,0]=1
    assert G[1, 0] == pytest.approx(1.0)
    # Colonne KCL : G[0,1]=1
    assert G[0, 1] == pytest.approx(1.0)
    # Valeur imposée
    assert b[1] == pytest.approx(5.0)

def test_voltage_source_needs_branch():
    src = VoltageSource("V1", "N1", "GND", DCSource(5.0))
    assert src.needs_branch() is True

def test_current_source_stamp():
    """Source 2mA de N2 vers N1 : inject dans b."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    isrc = CurrentSource("I1", "N1", "N2", DCSource(0.002))
    isrc.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=1e-5, t=0.0, prev_state={})
    assert b[0] == pytest.approx(0.002)    # courant entrant en N1
    assert b[1] == pytest.approx(-0.002)   # courant sortant de N2

def test_current_source_no_branch():
    isrc = CurrentSource("I1", "N1", "GND", DCSource(1.0))
    assert isrc.needs_branch() is False


# ── Tests BJT et OpAmp (Task 8) ───────────────────────────────────────────────

def test_bjt_cutoff():
    """V_BE < 0.6V → transistor bloqué : résistance infinie CE."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    # Base=0, Collector=1, Emitter=2; V_B=0.1V, V_E=0V → V_BE=0.1V < seuil
    bjt = BJT("Q1", "base", "collector", "emitter")
    node_map = {"base": 0, "collector": 1, "emitter": 2}
    bjt.stamp(G, b, node_map, {}, dt=1e-5, t=0.0,
              prev_state={"vbe": 0.1, "vce": 0.0, "current": 0.0})
    # Conductance CE très faible (bloqué)
    assert G[1, 1] == pytest.approx(1e-9, rel=1e-3)

def test_bjt_active():
    """V_BE >= seuil, V_CE > Vce_sat → mode actif : source de courant β*I_B."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    # V_BE=0.7V (actif), I_B=0.01A → I_C = β*I_B = 1A
    bjt = BJT("Q1", "base", "collector", "emitter", beta=100)
    node_map = {"base": 0, "collector": 1, "emitter": 2}
    bjt.stamp(G, b, node_map, {}, dt=1e-5, t=0.0,
              prev_state={"vbe": 0.7, "vce": 5.0, "current": 0.01})
    # Source de courant I_C = β*I_B = 1A : sort du collector (b[1] -= 1.0)
    assert b[1] == pytest.approx(-1.0)
    # La jonction base-émetteur passante est modélisée : conductance B-E + offset
    g_be = 1.0 / BJT.R_BE_ON
    assert G[0, 0] == pytest.approx(g_be)    # base
    assert G[0, 2] == pytest.approx(-g_be)   # base ↔ emitter
    # I_C (1A) sur l'émetteur moins l'offset de seuil de la jonction (0.6/R_BE_ON)
    offset = bjt.vbe_threshold / BJT.R_BE_ON
    assert b[2] == pytest.approx(1.0 - offset)


def test_bjt_active_base_draws_current():
    """En mode actif, la jonction B-E impose un courant de base réel (≠ 0)."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    bjt = BJT("Q1", "base", "collector", "emitter", beta=100)
    node_map = {"base": 0, "collector": 1, "emitter": 2}
    bjt.stamp(G, b, node_map, {}, dt=1e-5, t=0.0,
              prev_state={"vbe": 0.7, "vce": 5.0, "current": 0.01})
    # V_base=0.65V, V_emitter=0V → V_BE=0.65V au-dessus du seuil → I_B > 0
    x = np.array([0.65, 5.0, 0.0])
    state = bjt.get_state(x, node_map, {})
    assert state["current"] > 0.0
    assert state["current"] == pytest.approx((0.65 - 0.6) / BJT.R_BE_ON)

def test_opamp_needs_branch():
    op = OpAmp("U1", "plus", "minus", "out")
    assert op.needs_branch() is True

def test_opamp_stamp():
    """Op-amp idéal : contrainte V+ = V- via ligne de branche."""
    G = np.zeros((4, 4))   # plus=0, minus=1, out=2, branche=3
    b = np.zeros(4)
    op = OpAmp("U1", "plus", "minus", "out")
    node_map = {"plus": 0, "minus": 1, "out": 2}
    branch_map = {"U1": 3}
    op.stamp(G, b, node_map, branch_map, dt=1e-5, t=0.0, prev_state={})
    # Ligne de branche : V(plus) - V(minus) = 0
    assert G[3, 0] == pytest.approx(1.0)
    assert G[3, 1] == pytest.approx(-1.0)
    # Courant de sortie injecté sur node_out
    assert G[2, 3] == pytest.approx(1.0)
    assert b[3] == pytest.approx(0.0)


# ── Tests Potentiomètre ───────────────────────────────────────────────────────

def test_potentiometer_get_nodes():
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0)
    assert set(pot.get_nodes()) == {"N1", "N2", "N3"}

def test_potentiometer_does_not_need_branch():
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0)
    assert pot.needs_branch() is False

def test_potentiometer_stamp_ratio_half():
    """ratio=0.5, R=1000Ω : deux conductances égales G1=G2=0.002 S."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    # node_a=0, node_wiper=1, node_b=2
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=0.5)
    pot.stamp(G, b, {"N1": 0, "N2": 1, "N3": 2}, {}, dt=1e-5, t=0.0, prev_state={})
    G1 = 1.0 / (0.5 * 1000.0)  # 0.002
    G2 = 1.0 / (0.5 * 1000.0)  # 0.002
    assert G[0, 0] == pytest.approx(G1)
    assert G[0, 1] == pytest.approx(-G1)
    assert G[1, 0] == pytest.approx(-G1)
    assert G[1, 1] == pytest.approx(G1 + G2)
    assert G[1, 2] == pytest.approx(-G2)
    assert G[2, 1] == pytest.approx(-G2)
    assert G[2, 2] == pytest.approx(G2)
    assert np.all(b == 0.0)

def test_potentiometer_stamp_ratio_quarter():
    """ratio=0.25, R=1000Ω : G1=0.004 S, G2=1/750 S."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=0.25)
    pot.stamp(G, b, {"N1": 0, "N2": 1, "N3": 2}, {}, dt=1e-5, t=0.0, prev_state={})
    G1 = 1.0 / (0.25 * 1000.0)   # 0.004
    G2 = 1.0 / (0.75 * 1000.0)   # ~0.001333
    assert G[0, 0] == pytest.approx(G1)
    assert G[2, 2] == pytest.approx(G2)

def test_potentiometer_stamp_clamps_zero():
    """ratio=0.0 est clampé à 0.01 dans stamp() pour éviter la division par zéro."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=0.0)
    pot.stamp(G, b, {"N1": 0, "N2": 1, "N3": 2}, {}, dt=1e-5, t=0.0, prev_state={})
    G1_expected = 1.0 / (0.01 * 1000.0)  # ratio clampé à 0.01
    assert G[0, 0] == pytest.approx(G1_expected)

def test_potentiometer_stamp_clamps_one():
    """ratio=1.0 est clampé à 0.99 dans stamp() pour éviter la division par zéro."""
    G = np.zeros((3, 3))
    b = np.zeros(3)
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=1.0)
    pot.stamp(G, b, {"N1": 0, "N2": 1, "N3": 2}, {}, dt=1e-5, t=0.0, prev_state={})
    # ratio clampé à 0.99 → G2 = 1/(0.01*1000) = 0.1
    assert G[2, 2] == pytest.approx(1.0 / (0.01 * 1000.0))

def test_potentiometer_stamp_with_gnd():
    """node_b connecté à GND (absent de node_map) : seule la partie A-W est stampée."""
    G = np.zeros((2, 2))
    b = np.zeros(2)
    pot = Potentiometer("POT1", "N1", "N2", "GND", 1000.0, ratio=0.5)
    pot.stamp(G, b, {"N1": 0, "N2": 1}, {}, dt=1e-5, t=0.0, prev_state={})
    G1 = 1.0 / (0.5 * 1000.0)
    G2 = 1.0 / (0.5 * 1000.0)
    assert G[0, 0] == pytest.approx(G1)
    assert G[1, 1] == pytest.approx(G1 + G2)   # G2 connecté à GND : seulement diag N2

def test_potentiometer_get_state():
    """Va=10V, Vw=6V, Vb=2V, ratio=0.5, R=1000Ω → voltage=8V, current=0.008A."""
    node_map = {"N1": 0, "N2": 1, "N3": 2}
    x = np.array([10.0, 6.0, 2.0])
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=0.5)
    state = pot.get_state(x, node_map, {})
    assert state["voltage"] == pytest.approx(8.0)    # Va - Vb
    assert state["current"] == pytest.approx(0.008)  # G1 * (Va - Vw) = 0.002 * 4

def test_potentiometer_set_ratio():
    """set_ratio() met à jour ratio et params."""
    pot = Potentiometer("POT1", "N1", "N2", "N3", 1000.0, ratio=0.5)
    pot.set_ratio(0.75)
    assert pot.ratio == pytest.approx(0.75)
    assert pot.params["ratio"] == pytest.approx(0.75)

def test_potentiometer_params():
    """Les paramètres contiennent resistance et ratio."""
    pot = Potentiometer("POT1", "N1", "N2", "N3", 2200.0, ratio=0.3)
    assert pot.params["resistance"] == pytest.approx(2200.0)
    assert pot.params["ratio"] == pytest.approx(0.3)
