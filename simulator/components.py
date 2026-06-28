# simulator/components.py


# ── helpers MNA ──────────────────────────────────────────────────────────────

def _stamp_conductance(G, idx_a, idx_b, g):
    """
    Ajoute une conductance g entre les nœuds idx_a et idx_b.
    idx = -1 signifie GND (pas de ligne dans la matrice).
    """
    if idx_a >= 0:
        G[idx_a, idx_a] += g
    if idx_b >= 0:
        G[idx_b, idx_b] += g
    if idx_a >= 0 and idx_b >= 0:
        G[idx_a, idx_b] -= g
        G[idx_b, idx_a] -= g


def _stamp_current(b, idx_a, idx_b, current):
    """
    Injecte un courant entrant au nœud idx_a et sortant au nœud idx_b.
    Utilisé pour les sources de courant et les modèles compagnons.
    """
    if idx_a >= 0:
        b[idx_a] += current
    if idx_b >= 0:
        b[idx_b] -= current


def _node_voltage(x, node_map, name):
    """Retourne la tension d'un nœud (0.0 si c'est GND)."""
    if name not in node_map:
        return 0.0
    return x[node_map[name]]


# ── classe de base ────────────────────────────────────────────────────────────

class Component:
    """Interface commune pour tous les composants électroniques."""

    def __init__(self, component_id, params):
        self.id = component_id
        self.params = params   # paramètres bruts (dict) affichés dans l'UI

    def get_nodes(self):
        """Retourne la liste des noms de nœuds utilisés par ce composant."""
        raise NotImplementedError

    def needs_branch(self):
        """True si le composant ajoute une inconnue de courant à la MNA."""
        return False

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        """
        Ajoute la contribution du composant à la matrice MNA.

        G          : matrice numpy (n+m) x (n+m)
        b          : vecteur source numpy (n+m)
        node_map   : {nom_nœud: indice} — GND absent
        branch_map : {component_id: indice_branche}
        dt         : pas de temps en secondes
        t          : temps courant en secondes
        prev_state : {"voltage": float, "current": float} de l'étape précédente
        """
        raise NotImplementedError

    def get_state(self, x, node_map, branch_map):
        """
        Extrait tension et courant depuis le vecteur solution x.
        Retourne {"voltage": float, "current": float}.
        """
        raise NotImplementedError

    @property
    def records_history(self):
        """True pour les voltmètres et ampèremètres (historique affiché dans l'UI)."""
        return False

    @property
    def history_size(self):
        return int(self.params.get("history_size", 500))


# ── Résistance ────────────────────────────────────────────────────────────────

class Resistor(Component):
    """Résistance linéaire : contribution en conductance dans la MNA."""

    def __init__(self, component_id, node_a, node_b, resistance):
        super().__init__(component_id, {"resistance": resistance})
        self.node_a = node_a
        self.node_b = node_b
        self.resistance = resistance

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        _stamp_conductance(G, idx_a, idx_b, 1.0 / self.resistance)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        return {"voltage": voltage, "current": voltage / self.resistance}
