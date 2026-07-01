# editor/overlay.py
from simulator.components import BJT, Diode


def voltage_color(v: float, vmin: float, vmax: float) -> str:
    """Couleur hex sur une échelle bleu (vmin) -> rouge (vmax), bornée."""
    span = vmax - vmin
    if span < 1e-12:
        t = 0.5
    else:
        t = (v - vmin) / span
        t = max(0.0, min(1.0, t))
    r = round(255 * t)
    bl = round(255 * (1.0 - t))
    return f"#{r:02x}00{bl:02x}"


def state_indicator(component, comp_state: dict):
    """(libellé, couleur) pour les composants à état visible, sinon None."""
    if isinstance(component, BJT):
        i_b = comp_state.get("current", 0.0)
        if i_b <= 1e-9:
            return ("bloqué", "#888888")
        if comp_state.get("saturated"):
            return ("saturé", "#aa6600")
        return ("actif", "#118811")
    if isinstance(component, Diode):
        if comp_state.get("current", 0.0) > 1e-6:
            return ("passante", "#118811")
        return ("bloquée", "#888888")
    return None
