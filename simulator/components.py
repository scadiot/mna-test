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


# ── Condensateur ──────────────────────────────────────────────────────────────

class Capacitor(Component):
    """
    Condensateur — modèle compagnon Norton (Euler implicite) :
      i(t) = (C/dt) * v(t) - (C/dt) * v(t-1)
    Équivalent : conductance G_eq = C/dt + source de courant I_companion = G_eq * v_prev
    """

    def __init__(self, component_id, node_a, node_b, capacitance):
        super().__init__(component_id, {"capacitance": capacitance})
        self.node_a = node_a
        self.node_b = node_b
        self.capacitance = capacitance

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        g_eq = self.capacitance / dt
        v_prev = prev_state.get("voltage", 0.0)
        # Conductance compagnon
        _stamp_conductance(G, idx_a, idx_b, g_eq)
        # Source de courant compagnon : injecte g_eq*v_prev depuis idx_b vers idx_a
        _stamp_current(b, idx_a, idx_b, g_eq * v_prev)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        # Le courant réel est recalculé par le moteur depuis prev_state
        return {"voltage": va - vb, "current": 0.0}


# ── Bobine ────────────────────────────────────────────────────────────────────

class Inductor(Component):
    """
    Bobine — modèle compagnon Norton (Euler implicite) :
      i(t) = (dt/L) * v(t) + i(t-1)
    Équivalent : conductance G_eq = dt/L + source de courant I_companion = i_prev
    """

    def __init__(self, component_id, node_a, node_b, inductance):
        super().__init__(component_id, {"inductance": inductance})
        self.node_a = node_a
        self.node_b = node_b
        self.inductance = inductance

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        g_eq = dt / self.inductance
        i_prev = prev_state.get("current", 0.0)
        # Conductance compagnon
        _stamp_conductance(G, idx_a, idx_b, g_eq)
        # Source de courant compagnon : injecte i_prev depuis idx_b vers idx_a
        _stamp_current(b, idx_a, idx_b, i_prev)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        # Le courant est i(t) = G_eq*v(t) + i_prev, recalculé par le moteur depuis prev_state
        return {"voltage": voltage, "current": 0.0}


# ── Interrupteur ──────────────────────────────────────────────────────────────

class Switch(Component):
    """
    Interrupteur : résistance très grande (ouvert) ou très faible (fermé).
    Peut être basculé en temps réel via toggle().
    """

    R_OPEN = 1e9     # Ω — circuit pratiquement ouvert
    R_CLOSED = 1e-6  # Ω — quasi court-circuit

    def __init__(self, component_id, node_a, node_b, closed=False):
        super().__init__(component_id, {"closed": closed})
        self.node_a = node_a
        self.node_b = node_b
        self.closed = closed

    def toggle(self):
        """Bascule l'état de l'interrupteur."""
        self.closed = not self.closed
        self.params["closed"] = self.closed

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        r = self.R_CLOSED if self.closed else self.R_OPEN
        _stamp_conductance(G, idx_a, idx_b, 1.0 / r)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        r = self.R_CLOSED if self.closed else self.R_OPEN
        return {"voltage": voltage, "current": voltage / r}


# ── Voltmètre ─────────────────────────────────────────────────────────────────

class Voltmeter(Component):
    """
    Voltmètre : résistance très grande (n'influence pas le circuit).
    Enregistre un historique de la tension mesurée.
    """

    def __init__(self, component_id, node_a, node_b, history_size=500):
        super().__init__(component_id, {"history_size": history_size})
        self.node_a = node_a
        self.node_b = node_b
        self._history_size = history_size

    def get_nodes(self):
        return [self.node_a, self.node_b]

    @property
    def records_history(self):
        return True

    @property
    def history_size(self):
        return self._history_size

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        # 1e9 Ω → conductance 1e-9 S, pratiquement invisible pour le circuit
        _stamp_conductance(G, idx_a, idx_b, 1e-9)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        return {"voltage": voltage, "current": voltage * 1e-9}


# ── Ampèremètre ───────────────────────────────────────────────────────────────

class Ammeter(Component):
    """
    Ampèremètre : source de tension 0 V (court-circuit idéal avec mesure de courant).
    Nécessite une branche MNA supplémentaire pour mesurer le courant.
    Doit être placé en série dans le circuit (couper un fil en deux nœuds).
    """

    def __init__(self, component_id, node_a, node_b, history_size=500):
        super().__init__(component_id, {"history_size": history_size})
        self.node_a = node_a
        self.node_b = node_b
        self._history_size = history_size

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def needs_branch(self):
        return True

    @property
    def records_history(self):
        return True

    @property
    def history_size(self):
        return self._history_size

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        branch = branch_map[self.id]
        # Contrainte : V_a - V_b = 0 (ligne de branche)
        if idx_a >= 0:
            G[branch, idx_a] += 1.0
            G[idx_a, branch] += 1.0
        if idx_b >= 0:
            G[branch, idx_b] -= 1.0
            G[idx_b, branch] -= 1.0
        b[branch] = 0.0

    def get_state(self, x, node_map, branch_map):
        branch = branch_map[self.id]
        current = x[branch]   # courant mesuré = inconnue de branche
        return {"voltage": 0.0, "current": current}
