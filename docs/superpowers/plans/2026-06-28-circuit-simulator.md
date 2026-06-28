# Circuit Simulator — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire un simulateur de circuit électronique en Python avec analyse temporelle (MNA), une interface Tkinter et des circuits décrits en JSON.

**Architecture:** Un thread simulateur tourne à ~1000 Hz et résout le système linéaire MNA à chaque pas de temps, en écrivant les résultats dans un `SharedState` protégé par un Lock. Le thread principal Tkinter rafraîchit l'UI à 5 Hz en lisant ce `SharedState`. Chaque composant électronique est une classe Python avec une méthode `stamp()` qui contribue à la matrice MNA.

**Tech Stack:** Python 3.10+, numpy (résolution MNA), matplotlib (courbes historiques), tkinter (UI, natif), pytest (tests).

## Global Constraints

- Commentaires en français, nommages (fonctions, classes, variables) en anglais
- Code minimaliste : aucune abstraction inutile, aucune fonctionnalité hors spec
- GND est toujours le nœud de référence (tension = 0 V)
- `node_map` : `{nom_nœud: indice}` — GND absent (on retourne 0.0 si le nom est absent)
- `branch_map` : `{component_id: indice_branche}` — pour VoltageSource et Ammeter uniquement
- Taille matrice MNA : `n_nodes + n_branches` × `n_nodes + n_branches`
- Méthode d'intégration : Euler implicite (modèles compagnons Norton pour C et L)
- Tests dans `tests/`, commande : `pytest tests/ -v`

---

## Structure des fichiers

```
mna-test/
├── main.py
├── shared_state.py
├── circuit_loader.py
├── simulator/
│   ├── __init__.py
│   ├── engine.py
│   ├── components.py
│   └── sources.py
├── ui/
│   ├── __init__.py
│   ├── app.py
│   ├── component_list.py
│   └── detail_panel.py
├── circuits/
│   ├── rc_filter.json
│   ├── rl_transient.json
│   └── transistor_switch.json
├── tests/
│   ├── __init__.py
│   ├── test_shared_state.py
│   ├── test_sources.py
│   ├── test_components.py
│   └── test_circuit_loader.py
└── requirements.txt
```

---

### Task 1 : Scaffold du projet

**Files:**
- Create: `requirements.txt`
- Create: `simulator/__init__.py`
- Create: `ui/__init__.py`
- Create: `circuits/` (répertoire vide)
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: rien
- Produces: environnement Python fonctionnel avec pytest et numpy

- [ ] **Step 1 : Créer l'arborescence**

```
mkdir -p simulator ui circuits tests
```

Puis créer les fichiers vides :
```
simulator/__init__.py   (vide)
ui/__init__.py          (vide)
tests/__init__.py       (vide)
```

- [ ] **Step 2 : Écrire requirements.txt**

```
numpy>=1.24
matplotlib>=3.7
pytest>=7.4
```

- [ ] **Step 3 : Installer les dépendances**

```bash
pip install -r requirements.txt
```

Expected: installation sans erreur de numpy, matplotlib, pytest.

- [ ] **Step 4 : Vérifier que pytest fonctionne**

```bash
pytest tests/ -v
```

Expected: `no tests ran` (pas encore de tests).

---

### Task 2 : SharedState

**Files:**
- Create: `shared_state.py`
- Create: `tests/test_shared_state.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `SharedState` — classe avec `init_histories(ids, size)`, `write(node_voltages, comp_states, history_updates)`, `read() -> dict`, `set_error(msg)`, `stop()`

- [ ] **Step 1 : Écrire le test (TDD)**

```python
# tests/test_shared_state.py
import threading
from shared_state import SharedState

def test_write_and_read():
    """Vérifie que write() puis read() retournent les bonnes valeurs."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=100)
    state.write(
        node_voltages={"N1": 5.0},
        comp_states={"R1": {"voltage": 5.0, "current": 0.005}},
        history_updates={"VM1": 3.14},
    )
    data = state.read()
    assert data["node_voltages"]["N1"] == 5.0
    assert data["comp_states"]["R1"]["voltage"] == 5.0
    assert 3.14 in data["histories"]["VM1"]

def test_history_maxlen():
    """Vérifie que l'historique respecte la taille maximale."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=3)
    for i in range(10):
        state.write({}, {}, {"VM1": float(i)})
    data = state.read()
    assert len(data["histories"]["VM1"]) == 3
    assert data["histories"]["VM1"] == [7.0, 8.0, 9.0]

def test_thread_safety():
    """Vérifie l'absence d'erreurs avec écriture et lecture simultanées."""
    state = SharedState()
    state.init_histories(["VM1"], history_size=1000)
    errors = []

    def writer():
        for i in range(200):
            state.write({"N1": float(i)}, {}, {"VM1": float(i)})

    def reader():
        for _ in range(200):
            try:
                state.read()
            except Exception as e:
                errors.append(str(e))

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert not errors

def test_set_error():
    """Vérifie que set_error() arrête la simulation et stocke le message."""
    state = SharedState()
    state.running = True
    state.set_error("matrice singulière")
    data = state.read()
    assert data["error"] == "matrice singulière"
    assert not state.running
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_shared_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared_state'`

- [ ] **Step 3 : Implémenter shared_state.py**

```python
# shared_state.py
import threading
from collections import deque


class SharedState:
    """Contient les données partagées entre le thread simulateur et l'UI."""

    def __init__(self):
        self._lock = threading.Lock()
        # tensions aux nœuds : {nom_nœud: float}
        self.node_voltages = {}
        # état de chaque composant : {id: {"voltage": float, "current": float}}
        self.comp_states = {}
        # historiques des appareils de mesure : {id: deque}
        self.histories = {}
        self.running = False
        self.error = None

    def init_histories(self, component_ids, history_size):
        """Initialise les deques pour les appareils de mesure."""
        with self._lock:
            for cid in component_ids:
                self.histories[cid] = deque(maxlen=history_size)

    def write(self, node_voltages, comp_states, history_updates):
        """Écrit les résultats d'un pas de simulation (appelé par le thread simulateur)."""
        with self._lock:
            self.node_voltages = node_voltages
            self.comp_states = comp_states
            for cid, value in history_updates.items():
                if cid in self.histories:
                    self.histories[cid].append(value)

    def read(self):
        """Lit les données courantes (appelé par l'UI)."""
        with self._lock:
            return {
                "node_voltages": dict(self.node_voltages),
                "comp_states": dict(self.comp_states),
                "histories": {k: list(v) for k, v in self.histories.items()},
                "running": self.running,
                "error": self.error,
            }

    def set_error(self, message):
        """Enregistre une erreur et arrête la simulation."""
        with self._lock:
            self.error = message
            self.running = False

    def stop(self):
        """Demande l'arrêt propre de la simulation."""
        with self._lock:
            self.running = False
```

- [ ] **Step 4 : Lancer les tests pour vérifier qu'ils passent**

```bash
pytest tests/test_shared_state.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add shared_state.py tests/test_shared_state.py requirements.txt simulator/__init__.py ui/__init__.py tests/__init__.py
git commit -m "feat: add SharedState and project scaffold"
```

---

### Task 3 : Générateurs de formes d'onde (sources)

**Files:**
- Create: `simulator/sources.py`
- Create: `tests/test_sources.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `DCSource(amplitude)` — `.voltage(t) -> float`
  - `SineSource(amplitude, frequency, phase=0.0)` — `.voltage(t) -> float`
  - `PulseSource(amplitude, t_start, t_end)` — `.voltage(t) -> float`
  - `SquareSource(amplitude, frequency, duty_cycle=0.5)` — `.voltage(t) -> float`

- [ ] **Step 1 : Écrire les tests**

```python
# tests/test_sources.py
import math
import pytest
from simulator.sources import DCSource, SineSource, PulseSource, SquareSource

def test_dc_source():
    """Une source DC retourne toujours la même tension."""
    src = DCSource(5.0)
    assert src.voltage(0.0) == 5.0
    assert src.voltage(100.0) == 5.0

def test_sine_source_zero_crossing():
    """Sinusoïde à t=0 doit valoir 0 (sin(0) = 0)."""
    src = SineSource(amplitude=1.0, frequency=1.0)
    assert src.voltage(0.0) == pytest.approx(0.0, abs=1e-10)

def test_sine_source_peak():
    """Sinusoïde à t=T/4 doit valoir l'amplitude."""
    src = SineSource(amplitude=3.0, frequency=2.0)  # période = 0.5 s
    assert src.voltage(0.25) == pytest.approx(3.0, abs=1e-10)

def test_sine_source_with_phase():
    """Sinusoïde avec déphasage π/2 vaut l'amplitude à t=0."""
    src = SineSource(amplitude=1.0, frequency=1.0, phase=math.pi / 2)
    assert src.voltage(0.0) == pytest.approx(1.0, abs=1e-10)

def test_pulse_before():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.05) == 0.0

def test_pulse_during():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.3) == 5.0

def test_pulse_after():
    src = PulseSource(amplitude=5.0, t_start=0.1, t_end=0.5)
    assert src.voltage(0.6) == 0.0

def test_square_high():
    """Premier demi-cycle → tension haute."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(0.0) == 5.0
    assert src.voltage(0.49) == 5.0

def test_square_low():
    """Deuxième demi-cycle → tension basse."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(0.51) == 0.0

def test_square_second_period():
    """Début de la deuxième période → retour à tension haute."""
    src = SquareSource(amplitude=5.0, frequency=1.0, duty_cycle=0.5)
    assert src.voltage(1.0) == 5.0
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_sources.py -v
```

Expected: `ModuleNotFoundError: No module named 'simulator.sources'`

- [ ] **Step 3 : Implémenter simulator/sources.py**

```python
# simulator/sources.py
import math


class DCSource:
    """Source de tension ou de courant continu (valeur constante)."""

    def __init__(self, amplitude):
        self.amplitude = amplitude

    def voltage(self, t):
        return self.amplitude


class SineSource:
    """Source sinusoïdale : A * sin(2π * f * t + φ)."""

    def __init__(self, amplitude, frequency, phase=0.0):
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase

    def voltage(self, t):
        return self.amplitude * math.sin(2 * math.pi * self.frequency * t + self.phase)


class PulseSource:
    """Impulsion rectangulaire unique entre t_start et t_end."""

    def __init__(self, amplitude, t_start, t_end):
        self.amplitude = amplitude
        self.t_start = t_start
        self.t_end = t_end

    def voltage(self, t):
        return self.amplitude if self.t_start <= t <= self.t_end else 0.0


class SquareSource:
    """Signal créneau périodique avec rapport cyclique (duty_cycle)."""

    def __init__(self, amplitude, frequency, duty_cycle=0.5):
        self.amplitude = amplitude
        self.frequency = frequency
        self.duty_cycle = duty_cycle

    def voltage(self, t):
        # position dans la période courante (entre 0 et 1)
        period = 1.0 / self.frequency
        position = (t % period) / period
        return self.amplitude if position < self.duty_cycle else 0.0
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_sources.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add simulator/sources.py tests/test_sources.py
git commit -m "feat: add waveform sources (DC, sine, pulse, square)"
```

---

### Task 4 : Classe de base Component + helpers MNA + Resistor

**Files:**
- Create: `simulator/components.py`
- Create: `tests/test_components.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `_stamp_conductance(G, idx_a, idx_b, g)` — helper interne
  - `_stamp_current(b, idx_a, idx_b, current)` — helper interne
  - `_node_voltage(x, node_map, name) -> float` — helper interne
  - `Component` — classe de base abstraite
  - `Resistor(comp_id, node_a, node_b, resistance)` — `.stamp()`, `.get_state()`, `.get_nodes()`, `.needs_branch() -> False`

- [ ] **Step 1 : Écrire les tests**

```python
# tests/test_components.py
import pytest
import numpy as np
from simulator.components import Resistor

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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_components.py -v
```

Expected: `ModuleNotFoundError: No module named 'simulator.components'`

- [ ] **Step 3 : Implémenter simulator/components.py (base + Resistor)**

```python
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
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_components.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat: add Component base class and Resistor"
```

---

### Task 5 : Condensateur + Bobine (modèles compagnons Euler implicite)

**Files:**
- Modify: `simulator/components.py` (ajouter Capacitor et Inductor)
- Modify: `tests/test_components.py` (ajouter tests)

**Interfaces:**
- Consumes: `_stamp_conductance`, `_stamp_current`, `_node_voltage`, `Component`
- Produces:
  - `Capacitor(comp_id, node_a, node_b, capacitance)` — modèle Norton : G_eq = C/dt, I_companion = G_eq * v_prev
  - `Inductor(comp_id, node_a, node_b, inductance)` — modèle Norton : G_eq = dt/L, I_companion = i_prev

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter dans tests/test_components.py
from simulator.components import Capacitor, Inductor

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
    # La source compagnon injecte i_prev depuis N2 vers N1
    assert b[0] == pytest.approx(0.5)
    assert b[1] == pytest.approx(-0.5)
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_components.py -v -k "capacitor or inductor"
```

Expected: `ImportError`

- [ ] **Step 3 : Ajouter Capacitor et Inductor dans simulator/components.py**

```python
# Ajouter après la classe Resistor dans simulator/components.py

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
        # conductance compagnon
        _stamp_conductance(G, idx_a, idx_b, g_eq)
        # source de courant compagnon : injecte g_eq*v_prev depuis idx_b vers idx_a
        _stamp_current(b, idx_a, idx_b, g_eq * v_prev)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        return {"voltage": va - vb, "current": 0.0}   # courant recalculé en post-traitement


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
        # conductance compagnon
        _stamp_conductance(G, idx_a, idx_b, g_eq)
        # source de courant compagnon : injecte i_prev depuis idx_b vers idx_a
        _stamp_current(b, idx_a, idx_b, i_prev)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        # le courant est i(t) = G_eq*v(t) + i_prev, mais on ne connaît pas i_prev ici
        # le moteur le recalcule depuis prev_state — on retourne 0.0 temporairement
        return {"voltage": voltage, "current": 0.0}
```

> **Note :** Le courant réel de l'inductance est recalculé dans l'engine à partir des états précédents. La méthode `get_state` retourne 0.0 pour le courant car ce calcul appartient au moteur qui connaît `prev_state`.

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_components.py -v
```

Expected: tous les tests PASS (y compris Task 4).

- [ ] **Step 5 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat: add Capacitor and Inductor with implicit Euler companion models"
```

---

### Task 6 : Switch + Voltmètre + Ampèremètre

**Files:**
- Modify: `simulator/components.py`
- Modify: `tests/test_components.py`

**Interfaces:**
- Consumes: `_stamp_conductance`, `Component`
- Produces:
  - `Switch(comp_id, node_a, node_b, closed=False)` — `.toggle()`, `.needs_branch() -> False`
  - `Voltmeter(comp_id, node_a, node_b, history_size=500)` — `.records_history -> True`
  - `Ammeter(comp_id, node_a, node_b, history_size=500)` — `.needs_branch() -> True`, `.records_history -> True`

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter dans tests/test_components.py
from simulator.components import Switch, Voltmeter, Ammeter

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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_components.py -v -k "switch or voltmeter or ammeter"
```

Expected: `ImportError`

- [ ] **Step 3 : Ajouter Switch, Voltmeter et Ammeter dans simulator/components.py**

```python
# Ajouter dans simulator/components.py

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
        # 1e9 Ω → pratiquement invisible pour le circuit
        _stamp_conductance(G, idx_a, idx_b, 1e-9)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        voltage = va - vb
        return {"voltage": voltage, "current": voltage * 1e-9}


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
        # contrainte : V_a - V_b = 0 (ligne de branche)
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
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_components.py -v
```

Expected: tous les tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat: add Switch, Voltmeter, and Ammeter components"
```

---

### Task 7 : VoltageSource + CurrentSource (composants)

**Files:**
- Modify: `simulator/components.py`
- Modify: `tests/test_components.py`

**Interfaces:**
- Consumes: `Component`, `_stamp_current`, sources du Task 3
- Produces:
  - `VoltageSource(comp_id, node_pos, node_neg, source)` — `.needs_branch() -> True`
  - `CurrentSource(comp_id, node_a, node_b, source)` — `.needs_branch() -> False`

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter dans tests/test_components.py
from simulator.components import VoltageSource, CurrentSource
from simulator.sources import DCSource

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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_components.py -v -k "voltage_source or current_source"
```

- [ ] **Step 3 : Ajouter VoltageSource et CurrentSource**

```python
# Ajouter dans simulator/components.py

class VoltageSource(Component):
    """
    Source de tension (DC, sinus, impulsion ou créneau).
    Impose V_pos - V_neg = source.voltage(t) via une branche MNA.
    """

    def __init__(self, component_id, node_pos, node_neg, source):
        super().__init__(component_id, {"waveform": type(source).__name__})
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


class CurrentSource(Component):
    """
    Source de courant (DC, sinus, impulsion ou créneau).
    Injecte source.current(t) ampères du nœud node_b vers node_a.
    """

    def __init__(self, component_id, node_a, node_b, source):
        super().__init__(component_id, {"waveform": type(source).__name__})
        self.node_a = node_a
        self.node_b = node_b
        self.source = source

    def get_nodes(self):
        return [self.node_a, self.node_b]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_a = node_map.get(self.node_a, -1)
        idx_b = node_map.get(self.node_b, -1)
        current = self.source.voltage(t)   # voltage() retourne l'amplitude du courant
        # injecte 'current' ampères entrant en idx_a, sortant de idx_b
        _stamp_current(b, idx_a, idx_b, current)

    def get_state(self, x, node_map, branch_map):
        va = _node_voltage(x, node_map, self.node_a)
        vb = _node_voltage(x, node_map, self.node_b)
        return {"voltage": va - vb, "current": 0.0}
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_components.py -v
```

Expected: tous les tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat: add VoltageSource and CurrentSource components"
```

---

### Task 8 : Transistor BJT idéal + Ampli-op idéal

**Files:**
- Modify: `simulator/components.py`
- Modify: `tests/test_components.py`

**Interfaces:**
- Consumes: `_stamp_conductance`, `_stamp_current`, `Component`
- Produces:
  - `BJT(comp_id, node_base, node_collector, node_emitter, beta=100, vce_sat=0.2, vbe_threshold=0.6)` — 3 états : bloqué / actif / saturé
  - `OpAmp(comp_id, node_plus, node_minus, node_out)` — `.needs_branch() -> True`, contrainte V+ = V−

- [ ] **Step 1 : Ajouter les tests**

```python
# Ajouter dans tests/test_components.py
from simulator.components import BJT, OpAmp

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
    # Source de courant de collector vers emitter : b[2] += 1.0, b[1] -= 1.0
    assert b[2] == pytest.approx(1.0)    # I_C entre dans emitter
    assert b[1] == pytest.approx(-1.0)   # I_C sort du collector

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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_components.py -v -k "bjt or opamp"
```

- [ ] **Step 3 : Ajouter BJT et OpAmp dans simulator/components.py**

```python
# Ajouter dans simulator/components.py

class BJT(Component):
    """
    Transistor bipolaire NPN idéal — 3 états :
      - Bloqué  (cut-off)   : V_BE < vbe_threshold → résistance infinie CE
      - Actif   (active)    : V_CE > vce_sat → source de courant I_C = β * I_B
      - Saturé  (saturated) : V_CE <= vce_sat → court-circuit avec Vce_sat
    L'état est déterminé depuis prev_state (valeurs du pas précédent).
    """

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

    def get_nodes(self):
        return [self.node_base, self.node_collector, self.node_emitter]

    def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
        idx_b = node_map.get(self.node_base, -1)
        idx_c = node_map.get(self.node_collector, -1)
        idx_e = node_map.get(self.node_emitter, -1)

        vbe = prev_state.get("vbe", 0.0)
        vce = prev_state.get("vce", 0.0)
        i_b = prev_state.get("current", 0.0)

        if vbe < self.vbe_threshold:
            # Bloqué : résistance très grande entre collector et emitter
            _stamp_conductance(G, idx_c, idx_e, 1e-9)
        elif vce > self.vce_sat:
            # Actif : source de courant contrôlée I_C = β * I_B (de collector vers emitter)
            i_c = self.beta * i_b
            _stamp_current(b, idx_e, idx_c, i_c)   # I_C entre dans emitter, sort de collector
        else:
            # Saturé : Vce = Vce_sat (résistance très faible + source de tension)
            # Approximation simple : résistance très faible entre C et E
            _stamp_conductance(G, idx_c, idx_e, 1e6)

    def get_state(self, x, node_map, branch_map):
        vb = _node_voltage(x, node_map, self.node_base)
        vc = _node_voltage(x, node_map, self.node_collector)
        ve = _node_voltage(x, node_map, self.node_emitter)
        vbe = vb - ve
        vce = vc - ve
        # courant de base approximé (résistance base-emitter = 1kΩ par défaut)
        i_b = vbe / 1000.0 if vbe >= self.vbe_threshold else 0.0
        return {"voltage": vce, "current": i_b, "vbe": vbe, "vce": vce}


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
        # Colonne : le courant de sortie est injecté sur node_out
        if idx_o >= 0:
            G[idx_o, branch] += 1.0
        b[branch] = 0.0

    def get_state(self, x, node_map, branch_map):
        vout = _node_voltage(x, node_map, self.node_out)
        branch = branch_map[self.id]
        i_out = x[branch]
        return {"voltage": vout, "current": i_out}
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_components.py -v
```

Expected: tous les tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat: add BJT transistor and ideal OpAmp components"
```

---

### Task 9 : Circuit loader

**Files:**
- Create: `circuit_loader.py`
- Create: `tests/test_circuit_loader.py`

**Interfaces:**
- Consumes: toutes les classes de `simulator/components.py`, `simulator/sources.py`
- Produces:
  - `Circuit` dataclass : `.name`, `.dt`, `.components: list[Component]`, `.histories: dict`
  - `load_circuit(path: str) -> Circuit` — lève `ValueError` si JSON invalide

- [ ] **Step 1 : Écrire les tests**

```python
# tests/test_circuit_loader.py
import json, os, tempfile, pytest
from circuit_loader import load_circuit, Circuit
from simulator.components import Resistor, Capacitor, VoltageSource, Voltmeter

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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_circuit_loader.py -v
```

- [ ] **Step 3 : Implémenter circuit_loader.py**

```python
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
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_circuit_loader.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add circuit_loader.py tests/test_circuit_loader.py
git commit -m "feat: add circuit loader with JSON parsing and validation"
```

---

### Task 10 : Moteur de simulation (MNA engine)

**Files:**
- Create: `simulator/engine.py`

**Interfaces:**
- Consumes: `Circuit` (Task 9), `SharedState` (Task 2), toutes les classes `Component`
- Produces:
  - `SimulationEngine(circuit, shared_state)` — `.start()`, `.stop()`

> **Note :** Les tests du moteur sont des tests d'intégration sur un circuit RC complet. Pas de mock — on utilise de vrais composants et on vérifie la convergence physique.

- [ ] **Step 1 : Écrire le test d'intégration**

```python
# tests/test_engine.py
import time, pytest
from circuit_loader import load_circuit, Circuit
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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
pytest tests/test_engine.py -v
```

- [ ] **Step 3 : Implémenter simulator/engine.py**

```python
# simulator/engine.py
import time
import threading
import numpy as np


class SimulationEngine:
    """
    Moteur de simulation MNA.
    Tourne dans un thread séparé à ~1000 Hz (ou dt Hz si dt < 1ms).
    """

    def __init__(self, circuit, shared_state):
        self._circuit = circuit
        self._state = shared_state
        self._dt = circuit.dt
        self._components = circuit.components
        self._thread = None

        # Table des nœuds : {nom: indice} — GND exclu (toujours 0V)
        self._node_map = {}
        # Table des branches : {component_id: indice} — pour sources de tension et ampèremètres
        self._branch_map = {}
        self._build_maps()

        # État précédent de chaque composant pour les modèles compagnons
        self._prev_states = {c.id: {"voltage": 0.0, "current": 0.0} for c in self._components}

    def _build_maps(self):
        """Attribue un indice à chaque nœud non-GND et à chaque branche de tension."""
        node_set = set()
        for comp in self._components:
            for node in comp.get_nodes():
                if node != "GND":
                    node_set.add(node)

        # tri alphabétique pour un ordre déterministe
        for i, name in enumerate(sorted(node_set)):
            self._node_map[name] = i

        branch_idx = len(self._node_map)
        for comp in self._components:
            if comp.needs_branch():
                self._branch_map[comp.id] = branch_idx
                branch_idx += 1

    def _step(self, t):
        """Effectue un pas de simulation MNA à l'instant t."""
        size = len(self._node_map) + len(self._branch_map)
        G = np.zeros((size, size))
        b = np.zeros(size)

        # Chaque composant ajoute sa contribution à G et b
        for comp in self._components:
            prev = self._prev_states[comp.id]
            comp.stamp(G, b, self._node_map, self._branch_map, self._dt, t, prev)

        # Résolution du système linéaire G·x = b
        try:
            x = np.linalg.solve(G, b)
        except np.linalg.LinAlgError as e:
            self._state.set_error(f"Matrice singulière à t={t:.6f}s : {e}")
            return False

        # Extraction des tensions aux nœuds
        node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
        node_voltages["GND"] = 0.0

        # Extraction de l'état de chaque composant
        comp_states = {}
        history_updates = {}
        for comp in self._components:
            state = comp.get_state(x, self._node_map, self._branch_map)
            comp_states[comp.id] = state
            if comp.records_history:
                history_updates[comp.id] = state["voltage"]

        # Recalcul du courant pour les composants réactifs
        # (get_state ne connaît pas prev_state, donc current=0 par défaut)
        from simulator.components import Inductor, Capacitor
        for comp in self._components:
            va = float(x[self._node_map[comp.node_a]]) if hasattr(comp, "node_a") and comp.node_a in self._node_map else 0.0
            vb = float(x[self._node_map[comp.node_b]]) if hasattr(comp, "node_b") and comp.node_b in self._node_map else 0.0
            if isinstance(comp, Inductor):
                g_eq = self._dt / comp.inductance
                i_prev = self._prev_states[comp.id].get("current", 0.0)
                comp_states[comp.id]["current"] = g_eq * (va - vb) + i_prev
            elif isinstance(comp, Capacitor):
                g_eq = comp.capacitance / self._dt
                v_prev = self._prev_states[comp.id].get("voltage", 0.0)
                comp_states[comp.id]["current"] = g_eq * (comp_states[comp.id]["voltage"] - v_prev)

        self._prev_states = comp_states
        self._state.write(node_voltages, comp_states, history_updates)
        return True

    def _run_loop(self):
        """Boucle principale du simulateur (tourne dans un thread séparé)."""
        t = 0.0
        with self._state._lock:
            self._state.running = True

        while True:
            # Vérifie si l'arrêt a été demandé
            with self._state._lock:
                if not self._state.running:
                    break

            ok = self._step(t)
            if not ok:
                break   # erreur MNA → arrêt

            t += self._dt
            time.sleep(self._dt)

    def start(self):
        """Démarre la simulation dans un thread daemon."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Arrête proprement la simulation."""
        self._state.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
```

- [ ] **Step 4 : Lancer les tests**

```bash
pytest tests/test_engine.py -v
```

Expected: 2 tests PASS (le test attend 15ms, donc rapide).

- [ ] **Step 5 : Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS.

- [ ] **Step 6 : Commit**

```bash
git add simulator/engine.py tests/test_engine.py
git commit -m "feat: add MNA simulation engine with threading"
```

---

### Task 11 : Widget liste de composants (UI)

**Files:**
- Create: `ui/component_list.py`

**Interfaces:**
- Consumes: `tkinter`
- Produces:
  - `ComponentListWidget(parent, on_select_callback)` — `.populate(components)`, `.update_states(comp_states)`
  - Callback `on_select_callback(component)` appelé au clic

> Pas de tests automatisés pour Tkinter. Vérification manuelle au Task 13.

- [ ] **Step 1 : Implémenter ui/component_list.py**

```python
# ui/component_list.py
import tkinter as tk
from tkinter import ttk


class ComponentListWidget(tk.Frame):
    """
    Widget affichant la liste des composants du circuit.
    Appelle on_select_callback(component) quand l'utilisateur clique sur un composant.
    """

    def __init__(self, parent, on_select_callback):
        super().__init__(parent)
        self._callback = on_select_callback
        self._components = []   # liste des objets Component dans l'ordre affiché

        # Titre
        tk.Label(self, text="Composants", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )

        # Listbox avec scrollbar
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(
            frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE,
            activestyle="dotbox", font=("Courier", 9)
        )
        scrollbar.config(command=self._listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._listbox.bind("<<ListboxSelect>>", self._on_click)

    def populate(self, components):
        """Remplit la liste depuis les composants du circuit chargé."""
        self._components = list(components)
        self._listbox.delete(0, tk.END)
        for comp in self._components:
            label = f"{comp.id:<8} {type(comp).__name__}"
            self._listbox.insert(tk.END, label)

    def update_states(self, comp_states):
        """Rafraîchit les libellés avec l'état courant (tension)."""
        for i, comp in enumerate(self._components):
            state = comp_states.get(comp.id, {})
            v = state.get("voltage", 0.0)
            label = f"{comp.id:<8} {type(comp).__name__:<14} {v:+.3f}V"
            self._listbox.delete(i)
            self._listbox.insert(i, label)

    def _on_click(self, event):
        """Appelle le callback avec le composant sélectionné."""
        selection = self._listbox.curselection()
        if selection and self._callback:
            idx = selection[0]
            self._callback(self._components[idx])
```

- [ ] **Step 2 : Commit**

```bash
git add ui/component_list.py
git commit -m "feat: add ComponentListWidget"
```

---

### Task 12 : Widget panneau de détail (UI)

**Files:**
- Create: `ui/detail_panel.py`

**Interfaces:**
- Consumes: `tkinter`, `matplotlib.backends.backend_tkagg`
- Produces:
  - `DetailPanelWidget(parent)` — `.show_component(component)`, `.update(comp_state, history)`

- [ ] **Step 1 : Implémenter ui/detail_panel.py**

```python
# ui/detail_panel.py
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DetailPanelWidget(tk.Frame):
    """
    Panneau droit de l'UI : affiche les paramètres et l'état d'un composant sélectionné.
    Pour les voltmètres et ampèremètres, affiche aussi un graphique d'historique.
    """

    def __init__(self, parent):
        super().__init__(parent, relief=tk.SUNKEN, bd=1)
        self._current_component = None

        # Zone texte pour les paramètres et l'état
        self._info_var = tk.StringVar(value="Sélectionnez un composant")
        tk.Label(self, textvariable=self._info_var, justify=tk.LEFT,
                 font=("Courier", 9), anchor="nw").pack(
            fill=tk.X, padx=10, pady=10
        )

        # Graphique matplotlib (visible seulement pour les appareils de mesure)
        self._fig = Figure(figsize=(4, 2.5), dpi=90)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas_widget = self._canvas.get_tk_widget()
        # masqué par défaut — affiché seulement si records_history

        # Bouton toggle pour les interrupteurs
        self._toggle_btn = None

    def show_component(self, component):
        """Affiche les informations statiques d'un composant (appel au clic)."""
        self._current_component = component

        # Supprime le bouton toggle précédent s'il existe
        if self._toggle_btn:
            self._toggle_btn.destroy()
            self._toggle_btn = None

        # Affiche les paramètres JSON du composant
        lines = [f"ID      : {component.id}",
                 f"Type    : {type(component).__name__}",
                 "─" * 30,
                 "Paramètres :"]
        for key, val in component.params.items():
            lines.append(f"  {key:<14}: {val}")
        self._info_var.set("\n".join(lines))

        # Bouton toggle pour l'interrupteur
        from simulator.components import Switch
        if isinstance(component, Switch):
            self._toggle_btn = tk.Button(
                self, text="Basculer l'interrupteur",
                command=component.toggle
            )
            self._toggle_btn.pack(pady=5)

        # Affiche ou masque le graphique
        if component.records_history:
            self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            self._canvas_widget.pack_forget()

    def update(self, comp_state, history):
        """Rafraîchit l'état dynamique et le graphique (appelé à 5 Hz)."""
        if self._current_component is None:
            return

        comp = self._current_component
        v = comp_state.get("voltage", 0.0)
        i = comp_state.get("current", 0.0)

        lines = [f"ID      : {comp.id}",
                 f"Type    : {type(comp).__name__}",
                 "─" * 30,
                 "Paramètres :"]
        for key, val in comp.params.items():
            lines.append(f"  {key:<14}: {val}")
        lines += ["─" * 30,
                  f"  Tension  : {v:+.4f} V",
                  f"  Courant  : {i:+.6f} A"]
        self._info_var.set("\n".join(lines))

        # Mise à jour du graphique pour les appareils de mesure
        if comp.records_history and history:
            self._ax.clear()
            self._ax.plot(history, color="#1f77b4", linewidth=0.8)
            self._ax.set_ylabel("Tension (V)" if "voltmeter" in type(comp).__name__.lower()
                                else "Courant (A)")
            self._ax.set_xlabel("Échantillons")
            self._ax.grid(True, alpha=0.3)
            self._fig.tight_layout()
            self._canvas.draw_idle()
```

- [ ] **Step 2 : Commit**

```bash
git add ui/detail_panel.py
git commit -m "feat: add DetailPanelWidget with matplotlib history graph"
```

---

### Task 13 : Application principale Tkinter + point d'entrée

**Files:**
- Create: `ui/app.py`
- Create: `main.py`

**Interfaces:**
- Consumes: `ComponentListWidget`, `DetailPanelWidget`, `SimulationEngine`, `SharedState`, `load_circuit`
- Produces: application Tkinter complète, lançable avec `python main.py`

- [ ] **Step 1 : Implémenter ui/app.py**

```python
# ui/app.py
import tkinter as tk
from tkinter import filedialog, messagebox

from shared_state import SharedState
from circuit_loader import load_circuit
from simulator.engine import SimulationEngine
from ui.component_list import ComponentListWidget
from ui.detail_panel import DetailPanelWidget


class App(tk.Tk):
    """Fenêtre principale du simulateur de circuit électronique."""

    REFRESH_MS = 200   # rafraîchissement UI à 5 Hz

    def __init__(self):
        super().__init__()
        self.title("Simulateur de circuit")
        self.geometry("900x550")
        self.minsize(700, 400)

        self._state = SharedState()
        self._engine = None
        self._circuit = None
        self._selected_component = None

        self._build_ui()
        self._schedule_refresh()

    def _build_ui(self):
        """Construit la mise en page : barre supérieure + liste + panneau détail."""
        # ── Barre supérieure ──────────────────────────────────────────────────
        bar = tk.Frame(self, bd=1, relief=tk.RIDGE)
        bar.pack(fill=tk.X, side=tk.TOP)

        tk.Button(bar, text="Ouvrir circuit...", command=self._open_file).pack(
            side=tk.LEFT, padx=5, pady=4
        )
        self._file_label = tk.Label(bar, text="Aucun circuit chargé", fg="gray")
        self._file_label.pack(side=tk.LEFT, padx=10)

        self._run_btn = tk.Button(bar, text="▶  Démarrer", state=tk.DISABLED,
                                  command=self._toggle_simulation)
        self._run_btn.pack(side=tk.RIGHT, padx=5, pady=4)

        self._status_label = tk.Label(bar, text="", fg="red")
        self._status_label.pack(side=tk.RIGHT, padx=10)

        # ── Corps : liste à gauche, détail à droite ───────────────────────────
        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        self._comp_list = ComponentListWidget(body, on_select_callback=self._on_select)
        self._comp_list.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=5)

        ttk_sep = tk.Frame(body, width=2, bd=1, relief=tk.SUNKEN)
        ttk_sep.pack(side=tk.LEFT, fill=tk.Y, padx=3)

        self._detail = DetailPanelWidget(body)
        self._detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _open_file(self):
        """Ouvre un fichier JSON et charge le circuit."""
        path = filedialog.askopenfilename(
            title="Ouvrir un circuit",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return

        # Arrête la simulation en cours si nécessaire
        self._stop_simulation()

        try:
            self._circuit = load_circuit(path)
        except (ValueError, KeyError, Exception) as e:
            messagebox.showerror("Erreur de chargement", str(e))
            return

        # Réinitialise le SharedState
        self._state = SharedState()
        for comp_id, hist_size in self._circuit.histories.items():
            self._state.init_histories([comp_id], hist_size)

        self._file_label.config(text=self._circuit.name, fg="black")
        self._comp_list.populate(self._circuit.components)
        self._run_btn.config(state=tk.NORMAL, text="▶  Démarrer")
        self._status_label.config(text="")
        self._selected_component = None

    def _toggle_simulation(self):
        """Démarre ou arrête la simulation."""
        if self._engine and self._state.running:
            self._stop_simulation()
        else:
            self._start_simulation()

    def _start_simulation(self):
        if self._circuit is None:
            return
        self._engine = SimulationEngine(self._circuit, self._state)
        self._engine.start()
        self._run_btn.config(text="⏹  Arrêter")

    def _stop_simulation(self):
        if self._engine:
            self._engine.stop()
            self._engine = None
        self._run_btn.config(text="▶  Démarrer")

    def _on_select(self, component):
        """Appelé quand l'utilisateur clique sur un composant dans la liste."""
        self._selected_component = component
        self._detail.show_component(component)

    def _schedule_refresh(self):
        """Programme le prochain rafraîchissement de l'UI (5 Hz)."""
        self._refresh()
        self.after(self.REFRESH_MS, self._schedule_refresh)

    def _refresh(self):
        """Lit le SharedState et met à jour l'UI."""
        data = self._state.read()

        # Affiche une erreur si le moteur a planté
        if data["error"]:
            self._status_label.config(text=f"Erreur : {data['error']}")
            self._run_btn.config(text="▶  Démarrer")

        # Rafraîchit la liste des composants
        if data["comp_states"]:
            self._comp_list.update_states(data["comp_states"])

        # Rafraîchit le panneau de détail si un composant est sélectionné
        if self._selected_component:
            comp_id = self._selected_component.id
            comp_state = data["comp_states"].get(comp_id, {})
            history = data["histories"].get(comp_id, [])
            self._detail.update(comp_state, history)
```

- [ ] **Step 2 : Implémenter main.py**

```python
# main.py
from ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
```

- [ ] **Step 3 : Vérifier que l'application démarre**

```bash
python main.py
```

Expected: fenêtre Tkinter s'ouvre sans erreur. Le bouton "Ouvrir circuit..." est cliquable.

- [ ] **Step 4 : Commit**

```bash
git add ui/app.py main.py
git commit -m "feat: add main Tkinter app and entry point"
```

---

### Task 14 : Fichiers JSON de circuits d'exemple

**Files:**
- Create: `circuits/rc_filter.json`
- Create: `circuits/rl_transient.json`
- Create: `circuits/transistor_switch.json`

**Interfaces:**
- Consumes: format JSON défini en spec
- Produces: 3 circuits utilisables directement depuis l'UI

- [ ] **Step 1 : Créer circuits/rc_filter.json**

```json
{
  "name": "Filtre RC passe-bas (100 Hz, 5V sinus)",
  "dt": 1e-5,
  "components": [
    {
      "id": "V1",
      "type": "voltage_source",
      "node_pos": "N1",
      "node_neg": "GND",
      "params": { "waveform": "sine", "amplitude": 5.0, "frequency": 100.0 }
    },
    {
      "id": "R1",
      "type": "resistor",
      "node_a": "N1",
      "node_b": "N2",
      "params": { "resistance": 1000.0 }
    },
    {
      "id": "C1",
      "type": "capacitor",
      "node_a": "N2",
      "node_b": "GND",
      "params": { "capacitance": 1.59e-6 }
    },
    {
      "id": "VM_in",
      "type": "voltmeter",
      "node_a": "N1",
      "node_b": "GND",
      "params": { "history_size": 500 }
    },
    {
      "id": "VM_out",
      "type": "voltmeter",
      "node_a": "N2",
      "node_b": "GND",
      "params": { "history_size": 500 }
    }
  ]
}
```

> Note : C = 1/(2π×100×1000) ≈ 1.59 µF → fréquence de coupure fc = 100 Hz.

- [ ] **Step 2 : Créer circuits/rl_transient.json**

```json
{
  "name": "Circuit RL — réponse à l'échelon (interrupteur)",
  "dt": 1e-6,
  "components": [
    {
      "id": "V1",
      "type": "voltage_source",
      "node_pos": "N1",
      "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 12.0 }
    },
    {
      "id": "SW1",
      "type": "switch",
      "node_a": "N1",
      "node_b": "N2",
      "params": { "closed": false }
    },
    {
      "id": "R1",
      "type": "resistor",
      "node_a": "N2",
      "node_b": "N3",
      "params": { "resistance": 100.0 }
    },
    {
      "id": "L1",
      "type": "inductor",
      "node_a": "N3",
      "node_b": "GND",
      "params": { "inductance": 0.01 }
    },
    {
      "id": "VM1",
      "type": "voltmeter",
      "node_a": "N3",
      "node_b": "GND",
      "params": { "history_size": 500 }
    }
  ]
}
```

> Constante de temps τ = L/R = 10mH / 100Ω = 0.1 ms. Fermer SW1 dans l'UI pour observer la montée du courant.

- [ ] **Step 3 : Créer circuits/transistor_switch.json**

```json
{
  "name": "Transistor NPN en commutation (signal créneau 10 Hz)",
  "dt": 1e-5,
  "components": [
    {
      "id": "V_base",
      "type": "voltage_source",
      "node_pos": "N_base_in",
      "node_neg": "GND",
      "params": { "waveform": "square", "amplitude": 5.0, "frequency": 10.0 }
    },
    {
      "id": "R_base",
      "type": "resistor",
      "node_a": "N_base_in",
      "node_b": "N_base",
      "params": { "resistance": 10000.0 }
    },
    {
      "id": "V_cc",
      "type": "voltage_source",
      "node_pos": "N_vcc",
      "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 12.0 }
    },
    {
      "id": "R_collector",
      "type": "resistor",
      "node_a": "N_vcc",
      "node_b": "N_collector",
      "params": { "resistance": 1000.0 }
    },
    {
      "id": "Q1",
      "type": "transistor_bjt",
      "node_base": "N_base",
      "node_collector": "N_collector",
      "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 }
    },
    {
      "id": "VM_col",
      "type": "voltmeter",
      "node_a": "N_collector",
      "node_b": "GND",
      "params": { "history_size": 500 }
    }
  ]
}
```

- [ ] **Step 4 : Vérifier que les 3 circuits se chargent sans erreur**

```bash
python -c "
from circuit_loader import load_circuit
for f in ['circuits/rc_filter.json', 'circuits/rl_transient.json', 'circuits/transistor_switch.json']:
    c = load_circuit(f)
    print(f'OK: {c.name} — {len(c.components)} composants')
"
```

Expected:
```
OK: Filtre RC passe-bas (100 Hz, 5V sinus) — 5 composants
OK: Circuit RL — réponse à l'échelon (interrupteur) — 5 composants
OK: Transistor NPN en commutation (signal créneau 10 Hz) — 6 composants
```

- [ ] **Step 5 : Lancer tous les tests une dernière fois**

```bash
pytest tests/ -v
```

Expected: tous les tests PASS.

- [ ] **Step 6 : Lancer l'application et tester manuellement les 3 circuits**

```bash
python main.py
```

Vérifications manuelles :
- Charger `rc_filter.json` → démarrer → cliquer sur `VM_out` → vérifier que la courbe oscille à 100 Hz avec amplitude réduite
- Charger `rl_transient.json` → démarrer → cliquer sur `SW1` → bouton toggle visible → basculer → vérifier que la tension sur `VM1` monte exponentiellement
- Charger `transistor_switch.json` → démarrer → cliquer sur `VM_col` → vérifier l'inversion du signal (12V → 0.2V quand base = haute)

- [ ] **Step 7 : Commit final**

```bash
git add circuits/rc_filter.json circuits/rl_transient.json circuits/transistor_switch.json
git commit -m "feat: add three example circuits (RC filter, RL transient, BJT switch)"
```
