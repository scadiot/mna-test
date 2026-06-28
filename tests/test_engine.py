import time
import pytest
from circuit_loader import Circuit
from simulator.components import Resistor, Capacitor, VoltageSource, Voltmeter
from simulator.sources import DCSource
from simulator.engine import SimulationEngine
from shared_state import SharedState


def _make_rc_circuit():
    """Filtre RC : V1=5V, R1=1kΩ, C1=1µF. Constante de temps τ = 1ms."""
    return Circuit(
        name="RC test",
        dt=1e-5,
        components=[
            VoltageSource("V1", "N1", "GND", DCSource(5.0)),
            Resistor("R1", "N1", "N2", 1000.0),
            Capacitor("C1", "N2", "GND", 1e-6),
            Voltmeter("VM1", "N2", "GND", history_size=200),
        ],
        histories={"VM1": 200},
    )


def test_rc_charges_to_source_voltage():
    """Après 5τ (5ms), le condensateur doit être chargé à ~99% de 5V."""
    circuit = _make_rc_circuit()
    state = SharedState()
    for comp_id, hist_size in circuit.histories.items():
        state.init_histories([comp_id], hist_size)

    engine = SimulationEngine(circuit, state)
    engine.start()
    time.sleep(0.015)   # attend 15ms = 15τ pour être sûr
    engine.stop()

    data = state.read()
    v_cap = data["comp_states"].get("C1", {}).get("voltage", None)
    assert v_cap is not None
    assert v_cap == pytest.approx(5.0, abs=0.1)   # chargé à 5V ± 0.1V


def test_no_error_on_valid_circuit():
    circuit = _make_rc_circuit()
    state = SharedState()
    state.init_histories(["VM1"], 200)
    engine = SimulationEngine(circuit, state)
    engine.start()
    time.sleep(0.005)
    engine.stop()
    data = state.read()
    assert data["error"] is None
