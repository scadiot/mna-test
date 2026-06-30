# tests/test_circuit_loader.py
import json, os, tempfile, pytest
from circuit_loader import load_circuit, Circuit
from simulator.components import Resistor, Capacitor, VoltageSource, Voltmeter, Potentiometer

def _write_json(data):
    """Écrit un dict en fichier JSON temporaire, retourne le chemin."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name

RC_CIRCUIT = {
    "name": "Filtre RC",
    "dt": 1e-5,
    "components": [
        {"id": "V1", "type": "voltage_source", "node_pos": "N1", "node_neg": "GND",
         "params": {"waveform": "dc", "amplitude": 5.0}},
        {"id": "R1", "type": "resistor", "node_a": "N1", "node_b": "N2",
         "params": {"resistance": 1000.0}},
        {"id": "C1", "type": "capacitor", "node_a": "N2", "node_b": "GND",
         "params": {"capacitance": 1e-6}},
        {"id": "VM1", "type": "voltmeter", "node_a": "N2", "node_b": "GND",
         "params": {"history_size": 200}},
    ],
}

def test_load_rc_circuit():
    path = _write_json(RC_CIRCUIT)
    circuit = load_circuit(path)
    os.unlink(path)
    assert circuit.name == "Filtre RC"
    assert circuit.dt == pytest.approx(1e-5)
    assert len(circuit.components) == 4
    assert isinstance(circuit.components[0], VoltageSource)
    assert isinstance(circuit.components[1], Resistor)
    assert isinstance(circuit.components[2], Capacitor)
    assert isinstance(circuit.components[3], Voltmeter)

def test_histories_detected():
    path = _write_json(RC_CIRCUIT)
    circuit = load_circuit(path)
    os.unlink(path)
    assert "VM1" in circuit.histories
    assert circuit.histories["VM1"] == 200

def test_missing_gnd_raises():
    data = {
        "name": "Sans GND",
        "dt": 1e-5,
        "components": [
            {"id": "R1", "type": "resistor", "node_a": "N1", "node_b": "N2",
             "params": {"resistance": 1000.0}},
        ],
    }
    path = _write_json(data)
    with pytest.raises(ValueError, match="GND"):
        load_circuit(path)
    os.unlink(path)

def test_unknown_type_raises():
    data = {
        "name": "Test",
        "dt": 1e-5,
        "components": [
            {"id": "X1", "type": "flux_capacitor", "node_a": "N1", "node_b": "GND",
             "params": {}},
        ],
    }
    path = _write_json(data)
    with pytest.raises(ValueError, match="flux_capacitor"):
        load_circuit(path)
    os.unlink(path)

def test_load_potentiometer():
    """Charge un circuit avec un potentiomètre et vérifie les paramètres."""
    data = {
        "name": "Test POT",
        "dt": 1e-5,
        "components": [
            {"id": "V1", "type": "voltage_source", "node_pos": "N1", "node_neg": "GND",
             "params": {"waveform": "dc", "amplitude": 10.0}},
            {"id": "POT1", "type": "potentiometer",
             "node_a": "N1", "node_wiper": "N2", "node_b": "GND",
             "params": {"resistance": 5000.0, "ratio": 0.3}},
        ],
    }
    path = _write_json(data)
    circuit = load_circuit(path)
    os.unlink(path)
    assert len(circuit.components) == 2
    pot = circuit.components[1]
    assert isinstance(pot, Potentiometer)
    assert pot.resistance == pytest.approx(5000.0)
    assert pot.ratio == pytest.approx(0.3)
    assert pot.node_a == "N1"
    assert pot.node_wiper == "N2"
    assert pot.node_b == "GND"

def test_load_potentiometer_defaults():
    """Paramètres omis → valeurs par défaut resistance=1000, ratio=0.5."""
    data = {
        "name": "Test POT défauts",
        "dt": 1e-5,
        "components": [
            {"id": "POT1", "type": "potentiometer",
             "node_a": "N1", "node_wiper": "N2", "node_b": "GND",
             "params": {}},
        ],
    }
    path = _write_json(data)
    circuit = load_circuit(path)
    os.unlink(path)
    pot = circuit.components[0]
    assert pot.resistance == pytest.approx(1000.0)
    assert pot.ratio == pytest.approx(0.5)


def test_build_circuit_from_dict_without_file():
    from circuit_loader import build_circuit
    data = {
        "name": "En mémoire",
        "dt": 1e-5,
        "components": [
            {"id": "V1", "type": "voltage_source", "node_pos": "N1", "node_neg": "GND",
             "params": {"waveform": "dc", "amplitude": 5.0}},
            {"id": "R1", "type": "resistor", "node_a": "N1", "node_b": "GND",
             "params": {"resistance": 1000.0}},
        ],
    }
    circuit = build_circuit(data)
    assert isinstance(circuit, Circuit)
    assert circuit.name == "En mémoire"
    assert circuit.dt == 1e-5
    assert len(circuit.components) == 2


def test_build_circuit_requires_gnd():
    from circuit_loader import build_circuit
    data = {"name": "Sans masse", "dt": 1e-5,
            "components": [{"id": "R1", "type": "resistor",
                            "node_a": "N1", "node_b": "N2",
                            "params": {"resistance": 1000.0}}]}
    with pytest.raises(ValueError):
        build_circuit(data)
