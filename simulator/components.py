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
        # Source de courant compagnon : le courant de branche i(t)=g_eq*v(t)+i_prev
        # circule de idx_a vers idx_b, donc i_prev quitte idx_a (injection négative).
        _stamp_current(b, idx_a, idx_b, -i_prev)

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


# ── Source de tension ─────────────────────────────────────────────────────────

class VoltageSource(Component):
    """
    Source de tension (DC, sinus, impulsion ou créneau).
    Impose V_pos - V_neg = source.voltage(t) via une branche MNA.
    """

    def __init__(self, component_id, node_pos, node_neg, source):
        # Paramètres statiques incluant les valeurs de la source
        source_params = {k: v for k, v in source.__dict__.items()}
        super().__init__(component_id, {"waveform": type(source).__name__, **source_params})
        self.node_pos = node_pos
        self.node_neg = node_neg
        self.source = source   # instance de DCSource, SineSource, etc.

    def get_nodes(self):
        return [self.node_pos, self.node_neg]

    def needs_branch(self):
        return True

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_pos = node_map.get(self.node_pos, -1)
        idx_neg = node_map.get(self.node_neg, -1)
        branch = branch_map[self.id]
        voltage = self.source.voltage(t)
        # Ligne de branche : impose V_pos - V_neg = voltage
        if idx_pos >= 0:
            G[branch, idx_pos] += 1.0
            G[idx_pos, branch] += 1.0
        if idx_neg >= 0:
            G[branch, idx_neg] -= 1.0
            G[idx_neg, branch] -= 1.0
        b[branch] = voltage

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_pos)
        vb = _node_voltage(x, node_map, self.node_neg)
        branch = branch_map[self.id]
        current = -x[branch]   # courant fourni par la source (convention générateur)
        return {"voltage": va - vb, "current": current}


# ── Source de courant ─────────────────────────────────────────────────────────

class CurrentSource(Component):
    """
    Source de courant (DC, sinus, impulsion ou créneau).
    Injecte source.voltage(t) ampères du nœud node_b vers node_a.
    """

    def __init__(self, component_id, node_a, node_b, source):
        # Paramètres statiques incluant les valeurs de la source
        source_params = {k: v for k, v in source.__dict__.items()}
        super().__init__(component_id, {"waveform": type(source).__name__, **source_params})
        self.node_a = node_a
        self.node_b = node_b
        self.source = source

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def needs_branch(self):
        return False

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        current = self.source.voltage(t)   # voltage() retourne l'amplitude du courant
        # Injecte 'current' ampères entrant en idx_a, sortant de idx_b
        _stamp_current(b, idx_a, idx_b, current)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        return {"voltage": va - vb, "current": 0.0}


# ── Transistor bipolaire NPN ──────────────────────────────────────────────────

class BJT(Component):
    """
    Transistor bipolaire NPN — modèle compagnon linéarisé par morceaux (3 états),
    l'état étant déterminé depuis prev_state (valeurs du pas précédent) :
      - Bloqué  (cut-off)   : V_BE < vbe_threshold → jonction B-E ouverte, C-E ouvert
      - Actif   (active)    : V_CE > vce_sat → source de courant I_C = β * I_B
      - Saturé  (saturated) : V_CE <= vce_sat → quasi court-circuit C-E

    La jonction base-émetteur est explicitement modélisée (conductance R_BE_ON +
    offset de seuil) de sorte que le **courant de base traverse réellement le
    circuit externe** : V_BE ≈ vbe_threshold + R_BE_ON·I_B. C'est ce courant de
    base, fixé par la résistance de base externe, qui pilote I_C = β·I_B.
    """

    R_BE_ON  = 10.0    # Ω — résistance dynamique de la jonction B-E passante
    R_BE_OFF = 1e9     # Ω — jonction B-E bloquée
    R_CE_OFF = 1e-9    # S — conductance C-E bloquée (quasi ouvert)
    R_CE_SAT = 1.0     # Ω — résistance C-E saturée (V_CE ≈ vce_sat)

    def __init__(self, component_id, node_base, node_collector, node_emitter,
                 beta=100, vce_sat=0.2, vbe_threshold=0.6):
        super().__init__(component_id, {
            "beta": beta, "vce_sat": vce_sat, "vbe_threshold": vbe_threshold
        })
        self.node_base = node_base
        self.node_collector = node_collector
        self.node_emitter = node_emitter
        self.beta = beta
        self.vce_sat = vce_sat
        self.vbe_threshold = vbe_threshold
        # États du dernier stamp(), relus par get_state() pour rester cohérent
        self._on = False    # jonction base-émetteur passante
        self._sat = False   # transistor saturé

    def get_nodes(self):
        return [self.node_base, self.node_collector, self.node_emitter]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_b = node_map.get(self.node_base, -1)
        idx_c = node_map.get(self.node_collector, -1)
        idx_e = node_map.get(self.node_emitter, -1)

        vbe = prev_state.get("vbe", 0.0)
        vce = prev_state.get("vce", 0.0)
        i_b = prev_state.get("current", 0.0)
        sat_prev = prev_state.get("saturated", False)
        ic_prev = prev_state.get("ic", 0.0)

        if vbe < self.vbe_threshold:
            # Bloqué : jonction B-E quasi ouverte, C-E quasi ouvert.
            self._on = False
            self._sat = False
            _stamp_conductance(G, idx_b, idx_e, 1.0 / self.R_BE_OFF)
            _stamp_conductance(G, idx_c, idx_e, self.R_CE_OFF)
            return

        # Jonction base-émetteur passante : I_B = (V_BE - vbe_threshold) / R_BE_ON.
        # Le courant de base traverse donc la résistance de base externe.
        self._on = True
        _stamp_conductance(G, idx_b, idx_e, 1.0 / self.R_BE_ON)
        _stamp_current(b, idx_b, idx_e, self.vbe_threshold / self.R_BE_ON)

        i_c_drive = self.beta * max(i_b, 0.0)
        # Décision actif/saturé. En saturation V_CE est figé près de vce_sat ; on
        # ne peut donc pas relire vce pour décider de sortir de saturation. On
        # compare alors le courant demandé par la base (β·I_B) au courant que le
        # circuit collecteur fournit réellement (ic_prev) : tant que la base
        # sur-pilote, on reste saturé ; sinon on repasse en régime actif.
        if sat_prev:
            self._sat = i_c_drive >= ic_prev
        else:
            self._sat = vce <= self.vce_sat

        if self._sat:
            # Saturé : V_CE ≈ vce_sat (modèle compagnon résistance + offset)
            _stamp_conductance(G, idx_c, idx_e, 1.0 / self.R_CE_SAT)
            _stamp_current(b, idx_c, idx_e, self.vce_sat / self.R_CE_SAT)
        else:
            # Actif : source de courant contrôlée I_C = β·I_B (collector → emitter)
            _stamp_current(b, idx_e, idx_c, i_c_drive)

    def get_state(self, x, node_map, branch_map):
        vb = _node_voltage(x, node_map, self.node_base)
        vc = _node_voltage(x, node_map, self.node_collector)
        ve = _node_voltage(x, node_map, self.node_emitter)
        vbe = vb - ve
        vce = vc - ve
        # Courant de base cohérent avec l'état réellement stampé (0 si bloqué)
        i_b = max((vbe - self.vbe_threshold) / self.R_BE_ON, 0.0) if self._on else 0.0
        # Courant collecteur : mesuré aux bornes en saturation, sinon β·I_B
        if self._sat:
            i_c = (vce - self.vce_sat) / self.R_CE_SAT
        else:
            i_c = self.beta * i_b
        return {
            "voltage": vce, "current": i_b,
            "vbe": vbe, "vce": vce, "ic": i_c, "saturated": self._sat,
        }


# ── Diode ─────────────────────────────────────────────────────────────────────

class Diode(Component):
    """
    Diode — modèle linéaire par morceaux basé sur prev_state :
      V_AK > vf → passante (R_on très faible)
      V_AK ≤ vf → bloquée (R_off très grande)
    """

    R_ON  = 0.1    # Ω
    R_OFF = 1e9    # Ω

    def __init__(self, component_id, node_anode, node_cathode, vf=0.6):
        super().__init__(component_id, {"vf": vf})
        self.node_anode   = node_anode
        self.node_cathode = node_cathode
        self.vf = vf

    def get_nodes(self):
        return [self.node_anode, self.node_cathode]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_anode,   -1)
        idx_k = node_map.get(self.node_cathode, -1)
        v_prev = prev_state.get("voltage", 0.0)
        if v_prev > self.vf:
            # Passante : V_AK = vf + R_ON*I  →  conductance + source de courant offset
            # Sans l'offset vf, le modèle oscille : V_AK calculé ≈ 0 < vf → coupe à l'étape suivante
            _stamp_conductance(G, idx_a, idx_k, 1.0 / self.R_ON)
            _stamp_current(b, idx_a, idx_k, self.vf / self.R_ON)
        else:
            _stamp_conductance(G, idx_a, idx_k, 1.0 / self.R_OFF)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_anode)
        vk = _node_voltage(x, node_map, self.node_cathode)
        voltage = va - vk
        if voltage > self.vf:
            return {"voltage": voltage, "current": (voltage - self.vf) / self.R_ON}
        return {"voltage": voltage, "current": voltage / self.R_OFF}


# ── Amplificateur opérationnel idéal ──────────────────────────────────────────

class OpAmp(Component):
    """
    Amplificateur opérationnel idéal.
    Contrainte : V(node_plus) = V(node_minus) (gain infini avec rétroaction négative).
    Le courant de sortie est l'inconnue de branche — il est injecté sur node_out.
    """

    def __init__(self, component_id, node_plus, node_minus, node_out):
        super().__init__(component_id, {})
        self.node_plus = node_plus
        self.node_minus = node_minus
        self.node_out = node_out

    def get_nodes(self):
        return [self.node_plus, self.node_minus, self.node_out]

    def needs_branch(self):
        return True

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_p = node_map.get(self.node_plus, -1)
        idx_n = node_map.get(self.node_minus, -1)
        idx_o = node_map.get(self.node_out, -1)
        branch = branch_map[self.id]
        # Ligne de branche : impose V(plus) - V(minus) = 0
        if idx_p >= 0:
            G[branch, idx_p] += 1.0
        if idx_n >= 0:
            G[branch, idx_n] -= 1.0
        # Colonne KCL : le courant de sortie est injecté sur node_out
        if idx_o >= 0:
            G[idx_o, branch] += 1.0
        b[branch] = 0.0

    def get_state(self, x, node_map, branch_map):
        vout = _node_voltage(x, node_map, self.node_out)
        branch = branch_map[self.id]
        i_out = x[branch]
        return {"voltage": vout, "current": i_out}


# ── Potentiomètre ─────────────────────────────────────────────────────────────

class Potentiometer(Component):
    """
    Potentiomètre 3 broches — modélisé par deux conductances en série :
      G1 = 1 / (ratio × R)       entre node_a et node_wiper
      G2 = 1 / ((1-ratio) × R)   entre node_wiper et node_b
    Le ratio est clampé à [0.01, 0.99] dans stamp() pour éviter les divisions
    par zéro aux extrêmes. set_ratio() stocke la valeur brute.
    """

    def __init__(self, component_id, node_a, node_wiper, node_b,
                 resistance, ratio=0.5):
        super().__init__(component_id, {"resistance": resistance, "ratio": ratio})
        self.node_a = node_a
        self.node_wiper = node_wiper
        self.node_b = node_b
        self.resistance = resistance
        self.ratio = ratio

    def get_nodes(self):
        return [self.node_a, self.node_wiper, self.node_b]

    def set_ratio(self, value: float) -> None:
        self.ratio = value
        self.params["ratio"] = value

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_w = node_map.get(self.node_wiper, -1)
        idx_b = node_map.get(self.node_b, -1)
        ratio_clamped = max(0.01, min(0.99, self.ratio))
        g1 = 1.0 / (ratio_clamped * self.resistance)
        g2 = 1.0 / ((1.0 - ratio_clamped) * self.resistance)
        _stamp_conductance(G, idx_a, idx_w, g1)
        _stamp_conductance(G, idx_w, idx_b, g2)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vw = _node_voltage(x, node_map, self.node_wiper)
        vb = _node_voltage(x, node_map, self.node_b)
        ratio_clamped = max(0.01, min(0.99, self.ratio))
        g1 = 1.0 / (ratio_clamped * self.resistance)
        return {"voltage": va - vb, "current": g1 * (va - vw)}
