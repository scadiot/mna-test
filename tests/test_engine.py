import time
import pytest
from circuit_loader import Circuit
from simulator.components import (
    Resistor, Capacitor, VoltageSource, Voltmeter, BJT, Potentiometer,
)
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
    """Après 15τ (1500 pas à dt=1e-5), le condensateur doit être chargé à ~5V.

    Avance la simulation pas à pas de façon déterministe (comme _settle) plutôt
    que via le temps mural : depuis l'introduction du throttle CPU, le temps
    simulé n'avance plus à la vitesse du temps réel, donc un sleep() mural ne
    garantit pas un nombre de pas fixe. La physique testée est indépendante de
    l'ordonnancement temps réel.
    """
    circuit = _make_rc_circuit()
    state = SharedState()
    engine = SimulationEngine(circuit, state)
    for k in range(1500):   # 1500 × 1e-5 s = 15 ms = 15τ
        engine._step(k * circuit.dt)

    v_cap = engine._prev_states["C1"]["voltage"]
    assert v_cap == pytest.approx(5.0, abs=0.1)   # chargé à 5V ± 0.1V


def _make_bjt_amplifier(ratio):
    """
    Potentiomètre en diviseur (Vcc=12V) pilotant la base d'un NPN via R_base.
    Étage collecteur : R_collector entre Vcc et le collecteur, émetteur à GND.
    Avec R_base élevée, l'étage doit fonctionner en régime actif (linéaire).
    """
    return Circuit(
        name="BJT amp test",
        dt=1e-5,
        components=[
            VoltageSource("V_cc", "N_vcc", "GND", DCSource(12.0)),
            Potentiometer("POT1", "N_vcc", "N_wiper", "GND", 10000.0, ratio=ratio),
            Resistor("R_base", "N_wiper", "N_base", 100000.0),
            Resistor("R_collector", "N_vcc", "N_collector", 1000.0),
            BJT("Q1", "N_base", "N_collector", "GND", beta=100),
        ],
        histories={},
    )


def _settle(circuit, n_steps=400):
    """Avance la simulation pas à pas (déterministe) et renvoie le dernier état."""
    state = SharedState()
    engine = SimulationEngine(circuit, state)
    for k in range(n_steps):
        engine._step(k * circuit.dt)
    return engine._prev_states


def test_bjt_base_resistor_carries_current():
    """En régime actif, R_base doit voir un courant de base non nul."""
    states = _settle(_make_bjt_amplifier(ratio=0.5))
    i_rbase = states["R_base"]["current"]
    assert abs(i_rbase) > 1e-7   # > 0.1 µA : la base tire bien du courant


def test_bjt_collector_voltage_is_intermediate():
    """En régime actif, V_collector doit être strictement entre GND et Vcc."""
    states = _settle(_make_bjt_amplifier(ratio=0.5))
    v_col = states["Q1"]["vce"]   # émetteur à GND → vce = V_collector
    assert 0.5 < v_col < 11.5     # ni saturé (~0) ni bloqué (12)


def test_bjt_collector_tracks_potentiometer():
    """Faire varier le potentiomètre doit déplacer continûment V_collector."""
    v_low = _settle(_make_bjt_amplifier(ratio=0.2))["Q1"]["vce"]
    v_high = _settle(_make_bjt_amplifier(ratio=0.8))["Q1"]["vce"]
    # Les deux réglages donnent des sorties différentes et intermédiaires
    assert abs(v_high - v_low) > 1.0
    assert 0.0 < v_low < 12.0
    assert 0.0 < v_high < 12.0


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


from simulator.engine import _compute_sleep, THROTTLE_RATIO


def test_compute_sleep_when_ahead_sleeps_until_deadline():
    # now avant l'échéance → on dort le slack, échéance avancée de dt
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.00001, now=100.0, next_deadline=100.0003, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.0003)
    assert new_deadline == pytest.approx(100.0003 + 1e-4)


def test_compute_sleep_when_behind_throttles_and_reanchors():
    # now après l'échéance → throttle proportionnel au coût du pas, ré-ancrage sur now
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.002, now=100.5, next_deadline=100.0, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.002 * THROTTLE_RATIO)
    assert new_deadline == pytest.approx(100.5 + 1e-4)


def test_compute_sleep_exactly_on_time_is_treated_as_behind():
    # slack nul → branche "en retard" : throttle appliqué, ré-ancrage sur now
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.0005, now=100.0, next_deadline=100.0, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.0005 * THROTTLE_RATIO)
    assert new_deadline == pytest.approx(100.0 + 1e-4)


def test_compute_sleep_behind_caps_cpu_fraction():
    # La fraction d'occupation CPU ne dépasse pas 1/(1+THROTTLE_RATIO)
    step_duration = 0.003
    sleep_s, _ = _compute_sleep(
        step_duration=step_duration, now=100.5, next_deadline=100.0, dt=1e-4
    )
    cpu_fraction = step_duration / (step_duration + sleep_s)
    assert cpu_fraction <= 1.0 / (1.0 + THROTTLE_RATIO) + 1e-9
