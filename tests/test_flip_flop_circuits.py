# tests/test_flip_flop_circuits.py
import os
import pytest
from circuit_loader import load_circuit
from shared_state import SharedState
from simulator.engine import SimulationEngine

CIRCUITS_DIR = os.path.join(os.path.dirname(__file__), "..", "circuits")


def make_engine(filename):
    """Charge un circuit et construit un moteur prêt à être pas-à-passé."""
    circuit = load_circuit(os.path.join(CIRCUITS_DIR, filename))
    state = SharedState()
    for cid, size in circuit.histories.items():
        state.init_histories([cid], size)
    engine = SimulationEngine(circuit, state)
    return circuit, engine, state


def run(engine, n, callback=None):
    """Exécute n pas. callback(i, t) appelé avant chaque pas (pour piloter
    les interrupteurs). Lève AssertionError si la MNA devient singulière."""
    for i in range(n):
        t = i * engine._dt
        if callback:
            callback(i, t)
        assert engine._step(t), f"MNA singuliere au pas {i} (t={t:.4f}s)"


def vmeter(engine, comp_id):
    """Dernière tension lue par un voltmètre (lecture de l'état précédent)."""
    return engine._prev_states[comp_id]["voltage"]


def component(circuit, comp_id):
    """Retourne le composant d'identifiant comp_id."""
    return next(c for c in circuit.components if c.id == comp_id)


def _transitions(samples, low=1.0, high=3.0):
    """Compte les allers-retours bas<->haut d'un signal échantillonné."""
    count, level = 0, None
    for v in samples:
        if v <= low and level != "lo":
            if level is not None:
                count += 1
            level = "lo"
        elif v >= high and level != "hi":
            if level is not None:
                count += 1
            level = "hi"
    return count


def test_astable_oscille():
    circuit, engine, _ = make_engine("flip_flop_astable.json")
    samples = []
    run(engine, 4000, callback=lambda i, t: samples.append(vmeter(engine, "VM_C1"))
        if i > 0 else None)
    samples.append(vmeter(engine, "VM_C1"))
    assert min(samples) < 1.0, f"jamais a l'etat bas (min={min(samples):.2f})"
    assert max(samples) > 3.0, f"jamais a l'etat haut (max={max(samples):.2f})"
    assert _transitions(samples) >= 4, "oscillation insuffisante"
