# circuit_loader.py
import json
from dataclasses import dataclass, field
from simulator.components import (
    Resistor, Capacitor, Inductor, Switch,
    VoltageSource, CurrentSource,
    BJT, OpAmp, Voltmeter, Ammeter,
)
from simulator.sources import DCSource, SineSource, PulseSource, SquareSource


@dataclass
class Circuit:
    """Représentation d'un circuit chargé depuis un fichier JSON."""
    name: str
    dt: float
    components: list
    histories: dict = field(default_factory=dict)   # {component_id: history_size}


def _make_source(params):
    """Crée une instance de source depuis les paramètres JSON."""
    waveform = params.get("waveform", "dc")
    amplitude = float(params.get("amplitude", 0.0))
    if waveform == "dc":
        return DCSource(amplitude)
    elif waveform == "sine":
        return SineSource(amplitude, float(params["frequency"]),
                          float(params.get("phase", 0.0)))
    elif waveform == "pulse":
        return PulseSource(amplitude, float(params["t_start"]), float(params["t_end"]))
    elif waveform == "square":
        return SquareSource(amplitude, float(params["frequency"]),
                            float(params.get("duty_cycle", 0.5)))
    else:
        raise ValueError(f"Forme d'onde inconnue : '{waveform}'")


def _make_component(data):
    """Crée un composant depuis un dict JSON."""
    comp_id = data["id"]
    comp_type = data["type"]
    params = data.get("params", {})

    if comp_type == "resistor":
        return Resistor(comp_id, data["node_a"], data["node_b"],
                        float(params["resistance"]))
    elif comp_type == "capacitor":
        return Capacitor(comp_id, data["node_a"], data["node_b"],
                         float(params["capacitance"]))
    elif comp_type == "inductor":
        return Inductor(comp_id, data["node_a"], data["node_b"],
                        float(params["inductance"]))
    elif comp_type == "switch":
        return Switch(comp_id, data["node_a"], data["node_b"],
                      bool(params.get("closed", False)))
    elif comp_type == "voltage_source":
        return VoltageSource(comp_id, data["node_pos"], data["node_neg"],
                             _make_source(params))
    elif comp_type == "current_source":
        return CurrentSource(comp_id, data["node_a"], data["node_b"],
                             _make_source(params))
    elif comp_type == "transistor_bjt":
        return BJT(comp_id, data["node_base"], data["node_collector"],
                   data["node_emitter"],
                   beta=float(params.get("beta", 100)),
                   vce_sat=float(params.get("vce_sat", 0.2)),
                   vbe_threshold=float(params.get("vbe_threshold", 0.6)))
    elif comp_type == "opamp":
        return OpAmp(comp_id, data["node_plus"], data["node_minus"], data["node_out"])
    elif comp_type == "voltmeter":
        return Voltmeter(comp_id, data["node_a"], data["node_b"],
                         int(params.get("history_size", 500)))
    elif comp_type == "ammeter":
        return Ammeter(comp_id, data["node_a"], data["node_b"],
                       int(params.get("history_size", 500)))
    else:
        raise ValueError(f"Type de composant inconnu : '{comp_type}'")


def load_circuit(path):
    """
    Charge et valide un fichier JSON de circuit.
    Lève ValueError si le format est invalide ou si GND est absent.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name = data.get("name", "Sans nom")
    dt = float(data.get("dt", 1e-5))
    components = [_make_component(c) for c in data.get("components", [])]

    # Vérifie qu'au moins un composant est connecté à GND
    all_nodes = set()
    for comp in components:
        all_nodes.update(comp.get_nodes())
    if "GND" not in all_nodes:
        raise ValueError("Le circuit doit contenir au moins un nœud 'GND' (masse).")

    # Détecte les appareils de mesure qui enregistrent un historique
    histories = {}
    for comp in components:
        if comp.records_history:
            histories[comp.id] = comp.history_size

    return Circuit(name=name, dt=dt, components=components, histories=histories)
