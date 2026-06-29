# Bascules flip-flop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter trois circuits JSON de type bascule (astable, bistable RS, monostable) à transistors NPN dans `circuits/`, chacun validé par un test headless qui exécute le moteur et vérifie le comportement.

**Architecture:** Chaque bascule est un fichier JSON décrivant un netlist (mêmes conventions que `circuits/transistor_switch.json`, sans coordonnées). Un fichier de test unique `tests/test_flip_flop_circuits.py` charge chaque circuit via `load_circuit`, pilote le moteur pas-à-pas via `SimulationEngine._step`, lit les tensions dans `engine._prev_states`, et vérifie les comportements dynamiques. Les valeurs R/C sont ajustées si les tests échouent.

**Tech Stack:** Python, numpy (déjà utilisé par le moteur), pytest.

## Global Constraints

- Alimentation `VCC` = 5 V DC ; masse `GND` (nœud obligatoire).
- Transistors `transistor_bjt` : `beta=100`, `vbe_threshold=0.6`, `vce_sat=0.2`.
- `dt = 1e-3` pour les trois circuits.
- Composants autorisés uniquement parmi ceux gérés par `circuit_loader.py`.
- Aucune modification du moteur (`simulator/`) ni de `circuit_loader.py`.
- Pas de bascule à AOp (AOp idéal `V+=V-` incompatible avec la réaction positive).
- Format JSON : `{ "name", "dt", "components": [ {"id","type","node_*","params"} ] }`.

---

### Task 1 : Harnais de test + bascule astable

**Files:**
- Create: `circuits/flip_flop_astable.json`
- Create: `tests/test_flip_flop_circuits.py`

**Interfaces:**
- Consumes : `circuit_loader.load_circuit(path) -> Circuit` ;
  `shared_state.SharedState` ; `simulator.engine.SimulationEngine(circuit, state)`
  avec méthode interne `_step(t) -> bool` et attribut `_prev_states[id]["voltage"]`.
- Produces : helpers de test `make_engine(filename)`, `run(engine, n, callback=None)`,
  `vmeter(engine, comp_id) -> float`, `component(circuit, comp_id)` réutilisés par
  les tâches 2 et 3.

- [ ] **Step 1 : Écrire le circuit astable**

Créer `circuits/flip_flop_astable.json` :

```json
{
  "name": "Bascule astable — multivibrateur a 2 transistors (clignotant ~1.5 Hz)",
  "dt": 1e-3,
  "components": [
    { "id": "VCC", "type": "voltage_source", "node_pos": "N_vcc", "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 5.0 } },
    { "id": "Rc1", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c1",
      "params": { "resistance": 1000.0 } },
    { "id": "Rc2", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c2",
      "params": { "resistance": 1000.0 } },
    { "id": "Rb1", "type": "resistor", "node_a": "N_vcc", "node_b": "N_b1",
      "params": { "resistance": 47000.0 } },
    { "id": "Rb2", "type": "resistor", "node_a": "N_vcc", "node_b": "N_b2",
      "params": { "resistance": 47000.0 } },
    { "id": "Ccpl1", "type": "capacitor", "node_a": "N_c1", "node_b": "N_b2",
      "params": { "capacitance": 1e-5 } },
    { "id": "Ccpl2", "type": "capacitor", "node_a": "N_c2", "node_b": "N_b1",
      "params": { "capacitance": 1.2e-5 } },
    { "id": "Q1", "type": "transistor_bjt", "node_base": "N_b1",
      "node_collector": "N_c1", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "Q2", "type": "transistor_bjt", "node_base": "N_b2",
      "node_collector": "N_c2", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "VM_C1", "type": "voltmeter", "node_a": "N_c1", "node_b": "GND",
      "params": { "history_size": 5000 } },
    { "id": "VM_C2", "type": "voltmeter", "node_a": "N_c2", "node_b": "GND",
      "params": { "history_size": 5000 } }
  ]
}
```

- [ ] **Step 2 : Écrire le harnais + le test astable (qui doit échouer)**

Créer `tests/test_flip_flop_circuits.py` :

```python
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
```

- [ ] **Step 3 : Lancer le test, vérifier l'échec attendu**

Run: `python -m pytest tests/test_flip_flop_circuits.py::test_astable_oscille -v`
Expected : soit PASS directement (si l'oscillation démarre), soit FAIL sur une
assertion (`jamais a l'etat haut/bas` ou `oscillation insuffisante`) — ce qui
indique que le démarrage ou les constantes de temps doivent être ajustés.

- [ ] **Step 4 : Si échec, ajuster pour obtenir l'oscillation**

Si le test échoue, ajuster dans cet ordre (re-lancer le test après chaque
changement) :
1. Accentuer la dissymétrie de démarrage : `Ccpl2` 1.2e-5 → 1.5e-5, ou `Rb1`
   47000 → 39000 (Q1 démarre plus tôt).
2. Si aucune transition : augmenter le couplage en réduisant `Rb1`/`Rb2`
   (47000 → 33000) pour garantir la saturation alternée.
3. Si oscillation trop lente/rapide pour la fenêtre de 4000 pas : ajuster
   `Ccpl1`/`Ccpl2` (capacité ↑ = période ↑).

Re-lancer jusqu'à : `python -m pytest tests/test_flip_flop_circuits.py::test_astable_oscille -v` → PASS

- [ ] **Step 5 : Commit**

```bash
git add circuits/flip_flop_astable.json tests/test_flip_flop_circuits.py
git commit -m "feat(circuits): bascule astable (multivibrateur) + test headless"
```

---

### Task 2 : Bascule bistable RS

**Files:**
- Create: `circuits/flip_flop_bistable_rs.json`
- Modify: `tests/test_flip_flop_circuits.py` (ajout d'un test)

**Interfaces:**
- Consumes : helpers `make_engine`, `run`, `vmeter`, `component` de la tâche 1.
- Produces : rien de nouveau pour les tâches suivantes.

- [ ] **Step 1 : Écrire le circuit bistable**

Créer `circuits/flip_flop_bistable_rs.json` :

```json
{
  "name": "Bascule bistable RS — 2 transistors croises, Set/Reset par interrupteurs",
  "dt": 1e-3,
  "components": [
    { "id": "VCC", "type": "voltage_source", "node_pos": "N_vcc", "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 5.0 } },
    { "id": "Rc1", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c1",
      "params": { "resistance": 1000.0 } },
    { "id": "Rc2", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c2",
      "params": { "resistance": 1000.0 } },
    { "id": "Rcpl1", "type": "resistor", "node_a": "N_c1", "node_b": "N_b2",
      "params": { "resistance": 10000.0 } },
    { "id": "Rcpl2", "type": "resistor", "node_a": "N_c2", "node_b": "N_b1",
      "params": { "resistance": 10000.0 } },
    { "id": "Rb1", "type": "resistor", "node_a": "N_b1", "node_b": "GND",
      "params": { "resistance": 47000.0 } },
    { "id": "Rb2", "type": "resistor", "node_a": "N_b2", "node_b": "GND",
      "params": { "resistance": 47000.0 } },
    { "id": "R_set", "type": "resistor", "node_a": "N_set", "node_b": "N_b1",
      "params": { "resistance": 4700.0 } },
    { "id": "R_reset", "type": "resistor", "node_a": "N_reset", "node_b": "N_b2",
      "params": { "resistance": 4700.0 } },
    { "id": "S_set", "type": "switch", "node_a": "N_vcc", "node_b": "N_set",
      "params": { "closed": false } },
    { "id": "S_reset", "type": "switch", "node_a": "N_vcc", "node_b": "N_reset",
      "params": { "closed": false } },
    { "id": "Q1", "type": "transistor_bjt", "node_base": "N_b1",
      "node_collector": "N_c1", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "Q2", "type": "transistor_bjt", "node_base": "N_b2",
      "node_collector": "N_c2", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "VM_C1", "type": "voltmeter", "node_a": "N_c1", "node_b": "GND",
      "params": { "history_size": 2000 } },
    { "id": "VM_C2", "type": "voltmeter", "node_a": "N_c2", "node_b": "GND",
      "params": { "history_size": 2000 } }
  ]
}
```

- [ ] **Step 2 : Écrire le test bistable (qui doit échouer)**

Ajouter à la fin de `tests/test_flip_flop_circuits.py` :

```python
def test_bistable_set_reset_memorise():
    circuit, engine, _ = make_engine("flip_flop_bistable_rs.json")
    s_set = component(circuit, "S_set")
    s_reset = component(circuit, "S_reset")

    # SET : ferme S_set 200 pas, puis le rouvre
    s_set.closed = True
    run(engine, 200)
    s_set.closed = False
    run(engine, 200)
    # Q1 conduit -> collecteur 1 bas, collecteur 2 haut, et l'etat PERSISTE
    assert vmeter(engine, "VM_C1") < 1.0, "Set: C1 devrait etre bas"
    assert vmeter(engine, "VM_C2") > 3.0, "Set: C2 devrait etre haut"

    # RESET : ferme S_reset, puis rouvre -> etat inverse memorise
    s_reset.closed = True
    run(engine, 200)
    s_reset.closed = False
    run(engine, 200)
    assert vmeter(engine, "VM_C2") < 1.0, "Reset: C2 devrait etre bas"
    assert vmeter(engine, "VM_C1") > 3.0, "Reset: C1 devrait etre haut"
```

- [ ] **Step 3 : Lancer le test, vérifier le résultat**

Run: `python -m pytest tests/test_flip_flop_circuits.py::test_bistable_set_reset_memorise -v`
Expected : PASS si le verrouillage fonctionne ; sinon FAIL sur une assertion
indiquant quel état n'a pas été atteint ou mémorisé.

- [ ] **Step 4 : Si échec, ajuster le couplage**

Si le test échoue, ajuster (re-lancer après chaque changement) :
1. État non atteint après Set/Reset : réduire `R_set`/`R_reset` (4700 → 2200)
   pour forcer plus franchement la base.
2. État non mémorisé (les deux collecteurs reviennent au même niveau) : réduire
   le couplage `Rcpl1`/`Rcpl2` (10000 → 6800) pour renforcer la rétroaction, ou
   augmenter `Rb1`/`Rb2` (47000 → 68000) pour que le collecteur haut maintienne
   mieux la base opposée passante.
3. Si la durée de 200 pas est insuffisante pour stabiliser : augmenter à 500.

Re-lancer jusqu'à PASS.

- [ ] **Step 5 : Commit**

```bash
git add circuits/flip_flop_bistable_rs.json tests/test_flip_flop_circuits.py
git commit -m "feat(circuits): bascule bistable RS + test de memorisation"
```

---

### Task 3 : Bascule monostable

**Files:**
- Create: `circuits/flip_flop_monostable.json`
- Modify: `tests/test_flip_flop_circuits.py` (ajout d'un test)

**Interfaces:**
- Consumes : helpers `make_engine`, `run`, `vmeter`, `component` de la tâche 1.
- Produces : rien.

- [ ] **Step 1 : Écrire le circuit monostable**

Créer `circuits/flip_flop_monostable.json` :

```json
{
  "name": "Bascule monostable — impulsion calibree (~0.3 s) sur declenchement",
  "dt": 1e-3,
  "components": [
    { "id": "VCC", "type": "voltage_source", "node_pos": "N_vcc", "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 5.0 } },
    { "id": "Rc1", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c1",
      "params": { "resistance": 1000.0 } },
    { "id": "Rc2", "type": "resistor", "node_a": "N_vcc", "node_b": "N_c2",
      "params": { "resistance": 1000.0 } },
    { "id": "Rb2", "type": "resistor", "node_a": "N_vcc", "node_b": "N_b2",
      "params": { "resistance": 47000.0 } },
    { "id": "Rcpl", "type": "resistor", "node_a": "N_c2", "node_b": "N_b1",
      "params": { "resistance": 47000.0 } },
    { "id": "Ctmg", "type": "capacitor", "node_a": "N_c1", "node_b": "N_b2",
      "params": { "capacitance": 1e-5 } },
    { "id": "R_trig", "type": "resistor", "node_a": "N_trig", "node_b": "N_b1",
      "params": { "resistance": 4700.0 } },
    { "id": "S_trig", "type": "switch", "node_a": "N_vcc", "node_b": "N_trig",
      "params": { "closed": false } },
    { "id": "Q1", "type": "transistor_bjt", "node_base": "N_b1",
      "node_collector": "N_c1", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "Q2", "type": "transistor_bjt", "node_base": "N_b2",
      "node_collector": "N_c2", "node_emitter": "GND",
      "params": { "beta": 100, "vce_sat": 0.2, "vbe_threshold": 0.6 } },
    { "id": "VM_C1", "type": "voltmeter", "node_a": "N_c1", "node_b": "GND",
      "params": { "history_size": 3000 } },
    { "id": "VM_C2", "type": "voltmeter", "node_a": "N_c2", "node_b": "GND",
      "params": { "history_size": 3000 } }
  ]
}
```

- [ ] **Step 2 : Écrire le test monostable (qui doit échouer)**

Ajouter à la fin de `tests/test_flip_flop_circuits.py` :

```python
def test_monostable_impulsion():
    circuit, engine, _ = make_engine("flip_flop_monostable.json")
    s_trig = component(circuit, "S_trig")

    # Repos : Q2 passant -> C2 bas, Q1 bloque -> C1 haut
    run(engine, 300)
    assert vmeter(engine, "VM_C2") < 1.0, "repos: C2 devrait etre bas"
    assert vmeter(engine, "VM_C1") > 3.0, "repos: C1 devrait etre haut"

    # Declenchement : impulsion breve sur la base de Q1
    s_trig.closed = True
    run(engine, 20)
    s_trig.closed = False

    # Pendant l'impulsion, C2 passe haut (Q2 bloque)
    samples_c2 = []
    run(engine, 600, callback=lambda i, t: samples_c2.append(vmeter(engine, "VM_C2")))
    assert max(samples_c2) > 3.0, "C2 n'est jamais passe haut apres declenchement"

    # Retour au repos apres l'impulsion
    run(engine, 600)
    assert vmeter(engine, "VM_C2") < 1.0, "C2 n'est pas revenu au repos (bas)"
    assert vmeter(engine, "VM_C1") > 3.0, "C1 n'est pas revenu au repos (haut)"
```

- [ ] **Step 3 : Lancer le test, vérifier le résultat**

Run: `python -m pytest tests/test_flip_flop_circuits.py::test_monostable_impulsion -v`
Expected : PASS si l'impulsion se produit puis retombe ; sinon FAIL indiquant
l'étape qui n'a pas eu lieu.

- [ ] **Step 4 : Si échec, ajuster**

Si le test échoue, ajuster (re-lancer après chaque changement) :
1. Repos incorrect (C2 pas bas) : réduire `Rb2` (47000 → 33000) pour saturer Q2.
2. Pas de basculement au déclenchement : réduire `R_trig` (4700 → 2200) ou
   allonger l'impulsion de gâchette (20 → 40 pas).
3. Durée d'impulsion trop courte/longue : ajuster `Ctmg` (capacité ↑ = impulsion
   plus longue). Adapter alors les longueurs de `run` du test en conséquence.
4. Pas de retour au repos : vérifier `Rcpl` (47000) qui rétablit la polarisation
   de Q1 ; réduire si Q1 reste bloqué trop longtemps.

Re-lancer jusqu'à PASS.

- [ ] **Step 5 : Lancer toute la suite de tests**

Run: `python -m pytest tests/ -v`
Expected : tous les tests passent (les 3 nouveaux + les existants inchangés).

- [ ] **Step 6 : Commit**

```bash
git add circuits/flip_flop_monostable.json tests/test_flip_flop_circuits.py
git commit -m "feat(circuits): bascule monostable + test d'impulsion"
```

---

## Self-Review

**Spec coverage :**
- Astable (spec §1) → Task 1. ✅
- Bistable RS (spec §2) → Task 2. ✅
- Monostable (spec §3) → Task 3. ✅
- Conventions communes (VCC 5 V, β/seuils, dt=1e-3, voltmètres) → présentes dans
  les trois JSON. ✅
- Validation par exécution du simulateur (spec « Validation ») → tests headless
  dans chaque tâche, plus étapes d'ajustement. ✅
- Hors périmètre (pas d'AOp, pas d'ampèremètre, pas de modif moteur) → respecté. ✅

**Placeholder scan :** aucun TODO/TBD ; tout le code JSON et Python est complet.

**Type consistency :** helpers `make_engine`/`run`/`vmeter`/`component` définis en
Task 1, réutilisés à l'identique en Tasks 2 et 3. Les ids de composants
(`VM_C1`, `VM_C2`, `S_set`, `S_reset`, `S_trig`) correspondent entre JSON et tests.
`SimulationEngine._step` et `engine._prev_states` correspondent au code réel lu
dans `simulator/engine.py`.

**Note d'exécution :** les tests encodent le comportement attendu (oscillation,
mémorisation, impulsion) avec des seuils larges (bas < 1 V, haut > 3 V). Si un
test échoue, le travail consiste à ajuster les valeurs R/C du circuit (étapes
« Si échec »), pas à relâcher les seuils.
