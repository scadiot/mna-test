# Convergence intra-pas du moteur — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une boucle de point fixe intra-pas au moteur MNA pour faire converger les composants non-linéaires dans le pas de temps courant, puis alléger les condensateurs de découplage des trois bascules.

**Architecture:** `Component` gagne une propriété `is_nonlinear` (BJT/Diode → `True`). `SimulationEngine._step` itère « stamp → solve → re-décide les états non-linéaires → re-stamp » jusqu'à stabilité des tensions (‖Δx‖∞ < TOL) ou `MAX_ITERATIONS`, en gardant figé l'historique temporel des réactifs (C/L). La signature de `stamp` ne change pas.

**Tech Stack:** Python, numpy, pytest.

## Global Constraints

- Aucune modification de la signature de `stamp(self, G, b, node_map, branch_map, dt, t, prev_state)`.
- Pas de réécriture du heuristique de saturation du BJT ni de voltage-limiting (travail futur séparé).
- `MAX_ITERATIONS = 100`, `CONVERGENCE_TOL = 1e-9` (constantes module de `simulator/engine.py`).
- Non-convergence = best-effort : garder le dernier itéré, avancer le temps, aucune erreur, aucun compteur exposé dans `SharedState`.
- Critères de succès réalistes : pics de commutation réduits (≈ −394 V → < −50 V), **pas** éliminés ; `Rb` de l'astable reste **100 kΩ** ; condensateurs `Cc` retirés ou fortement réduits.
- Tous les tests existants du dépôt doivent rester verts (non-régression = garde-fou principal).

---

### Task 1 : Propriété `is_nonlinear` sur les composants

**Files:**
- Modify: `simulator/components.py` (classe `Component` ; classes `BJT`, `Diode`)
- Test: `tests/test_components.py` (ajout d'un test)

**Interfaces:**
- Consumes: rien.
- Produces: `Component.is_nonlinear -> bool` (propriété ; `False` par défaut, `True` sur `BJT` et `Diode`). Consommée par `SimulationEngine._step` en Task 2.

- [ ] **Step 1 : Écrire le test (échec attendu)**

Ajouter à la fin de `tests/test_components.py` :

```python
def test_is_nonlinear_flags():
    from simulator.components import Resistor, Capacitor, Inductor, BJT, Diode, Switch
    assert Resistor("R", "A", "B", 1000.0).is_nonlinear is False
    assert Capacitor("C", "A", "B", 1e-6).is_nonlinear is False
    assert Inductor("L", "A", "B", 1e-3).is_nonlinear is False
    assert Switch("S", "A", "B", False).is_nonlinear is False
    assert BJT("Q", "b", "c", "e").is_nonlinear is True
    assert Diode("D", "a", "k").is_nonlinear is True
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python -m pytest tests/test_components.py::test_is_nonlinear_flags -v`
Expected : FAIL (`AttributeError: 'Resistor' object has no attribute 'is_nonlinear'`).

- [ ] **Step 3 : Ajouter la propriété sur la classe de base**

Dans `simulator/components.py`, classe `Component`, juste après la propriété `history_size` (vers la ligne 82) :

```python
    @property
    def is_nonlinear(self):
        """True pour les composants dont l'état dépend de la solution du pas
        courant (itérés par le moteur dans la boucle de convergence intra-pas)."""
        return False
```

- [ ] **Step 4 : Surcharger sur `BJT` et `Diode`**

Dans la classe `BJT` (après `get_nodes`, vers la ligne 425) :

```python
    @property
    def is_nonlinear(self):
        return True
```

Dans la classe `Diode` (après `get_nodes`, vers la ligne 509) :

```python
    @property
    def is_nonlinear(self):
        return True
```

- [ ] **Step 5 : Lancer le test, vérifier le succès**

Run: `python -m pytest tests/test_components.py::test_is_nonlinear_flags -v`
Expected : PASS.

- [ ] **Step 6 : Commit**

```bash
git add simulator/components.py tests/test_components.py
git commit -m "feat(engine): propriete is_nonlinear sur les composants"
```

---

### Task 2 : Boucle de convergence intra-pas dans `_step`

**Files:**
- Modify: `simulator/engine.py` (constantes module ; `SimulationEngine.__init__` ligne 56 ; `SimulationEngine._step` lignes 76-124)
- Test: `tests/test_engine.py` (ajout de tests + un helper)

**Interfaces:**
- Consumes: `Component.is_nonlinear` (Task 1).
- Produces: `SimulationEngine._last_iterations -> int` (nombre d'itérations du dernier pas, attribut interne pour les tests) ; constantes `MAX_ITERATIONS`, `CONVERGENCE_TOL`.

- [ ] **Step 1 : Écrire le helper astable + le test de réduction des pics (échec attendu)**

Ajouter dans `tests/test_engine.py` (les classes utilisées — `VoltageSource`,
`Resistor`, `Capacitor`, `Voltmeter`, `BJT` — et `DCSource`, `Circuit`,
`SimulationEngine`, `SharedState` sont déjà importées en tête du fichier ;
n'ajouter aucun import) :

```python
def _make_astable(rb=100000.0, ccpl1=10e-6, ccpl2=12e-6):
    """Multivibrateur astable à 2 NPN croisés, SANS condensateurs de découplage.
    Sert à vérifier que la convergence borne les excursions de tension."""
    return Circuit(
        name="astable test",
        dt=1e-3,
        components=[
            VoltageSource("VCC", "N_vcc", "GND", DCSource(5.0)),
            Resistor("Rc1", "N_vcc", "N_c1", 1000.0),
            Resistor("Rc2", "N_vcc", "N_c2", 1000.0),
            Resistor("Rb1", "N_vcc", "N_b1", rb),
            Resistor("Rb2", "N_vcc", "N_b2", rb),
            Capacitor("Ccpl1", "N_c1", "N_b2", ccpl1),
            Capacitor("Ccpl2", "N_c2", "N_b1", ccpl2),
            BJT("Q1", "N_b1", "N_c1", "GND", beta=100),
            BJT("Q2", "N_b2", "N_c2", "GND", beta=100),
            Voltmeter("VM_C1", "N_c1", "GND", history_size=5000),
        ],
        histories={},
    )


def _run_collect(circuit, n, node_comp_id="VM_C1"):
    """Avance n pas et renvoie (engine, state, liste des tensions du voltmètre)."""
    state = SharedState()
    engine = SimulationEngine(circuit, state)
    samples = []
    for k in range(n):
        engine._step(k * circuit.dt)
        samples.append(engine._prev_states[node_comp_id]["voltage"])
    return engine, state, samples


def _count_transitions(samples, low=1.0, high=3.0):
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


def test_convergence_borne_les_excursions_astable():
    """Avec convergence intra-pas, l'astable Rb=100k SANS condensateurs de
    découplage oscille et ne plonge plus à ~-394 V."""
    _, _, samples = _run_collect(_make_astable(), 4000)
    assert min(samples) > -50.0, f"excursion trop négative : {min(samples):.1f} V"
    assert max(samples) > 3.0
    assert _count_transitions(samples) >= 4, "n'oscille pas"
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python -m pytest tests/test_engine.py::test_convergence_borne_les_excursions_astable -v`
Expected : FAIL sur `min(samples) > -50.0` (le solve unique actuel descend à ≈ −394 V).

- [ ] **Step 3 : Ajouter les constantes et l'attribut `_last_iterations`**

Dans `simulator/engine.py`, après la constante `THROTTLE_RATIO` (ligne 11) :

```python
# Convergence intra-pas : on itère stamp/solve jusqu'à ce que les tensions se
# stabilisent (‖Δx‖∞ < CONVERGENCE_TOL) ou que MAX_ITERATIONS soit atteint.
MAX_ITERATIONS = 100
CONVERGENCE_TOL = 1e-9
```

Dans `SimulationEngine.__init__`, juste après la ligne
`self._prev_states = {c.id: {"voltage": 0.0, "current": 0.0} for c in self._components}` (ligne 56) :

```python
        # Nombre d'itérations du dernier pas (diagnostic / tests)
        self._last_iterations = 0
```

- [ ] **Step 4 : Réécrire `_step` avec la boucle de point fixe**

Remplacer entièrement la méthode `_step` (lignes 76-124) par :

```python
    def _step(self, t):
        """Effectue un pas de simulation MNA à l'instant t.

        Boucle de point fixe : les composants non-linéaires (is_nonlinear)
        re-décident leur état d'après la solution courante jusqu'à stabilité
        des tensions. L'historique temporel des réactifs (C/L) reste figé sur
        l'état du pas précédent (self._prev_states) pendant toute l'itération.
        """
        size = len(self._node_map) + len(self._branch_map)

        # États passés à stamp() : figés pour les réactifs, ré-itérés pour les
        # non-linéaires. Initialisés depuis l'historique du pas précédent.
        iter_states = {c.id: dict(self._prev_states[c.id]) for c in self._components}

        x = None
        x_prev = None
        comp_states = {}
        iterations = 0
        for k in range(MAX_ITERATIONS):
            iterations = k + 1
            G = np.zeros((size, size))
            b = np.zeros(size)
            for comp in self._components:
                comp.stamp(G, b, self._node_map, self._branch_map,
                           self._dt, t, iter_states[comp.id])

            try:
                x = np.linalg.solve(G, b)
            except np.linalg.LinAlgError as e:
                self._state.set_error(f"Matrice singulière à t={t:.6f}s : {e}")
                return False

            comp_states = {
                comp.id: comp.get_state(x, self._node_map, self._branch_map)
                for comp in self._components
            }

            if x_prev is not None and np.max(np.abs(x - x_prev)) < CONVERGENCE_TOL:
                break

            x_prev = x
            # Seuls les non-linéaires sont ré-injectés ; les réactifs gardent
            # l'historique figé du pas précédent.
            for comp in self._components:
                if comp.is_nonlinear:
                    iter_states[comp.id] = comp_states[comp.id]

        self._last_iterations = iterations

        # Tensions aux nœuds (depuis la dernière solution)
        node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
        node_voltages["GND"] = 0.0

        # Historique des appareils de mesure
        history_updates = {}
        for comp in self._components:
            if comp.records_history:
                state = comp_states[comp.id]
                history_updates[comp.id] = state["current"] if isinstance(comp, Ammeter) else state["voltage"]

        # Recalcul du courant des composants réactifs depuis l'historique figé
        # (self._prev_states n'est réassigné qu'après ce bloc).
        for comp in self._components:
            if isinstance(comp, Inductor):
                va = float(x[self._node_map[comp.node_a]]) if comp.node_a in self._node_map else 0.0
                vb = float(x[self._node_map[comp.node_b]]) if comp.node_b in self._node_map else 0.0
                g_eq = self._dt / comp.inductance
                i_prev = self._prev_states[comp.id].get("current", 0.0)
                comp_states[comp.id]["current"] = g_eq * (va - vb) + i_prev
            elif isinstance(comp, Capacitor):
                v_prev = self._prev_states[comp.id].get("voltage", 0.0)
                g_eq = comp.capacitance / self._dt
                comp_states[comp.id]["current"] = g_eq * (comp_states[comp.id]["voltage"] - v_prev)

        self._prev_states = comp_states
        self._state.write(node_voltages, comp_states, history_updates)
        return True
```

- [ ] **Step 5 : Lancer le test de réduction des pics, vérifier le succès**

Run: `python -m pytest tests/test_engine.py::test_convergence_borne_les_excursions_astable -v`
Expected : PASS (`min(samples)` ≈ −36 V > −50, oscillation ≥ 4 transitions).

- [ ] **Step 6 : Ajouter les tests de convergence nominale et de best-effort**

Ajouter dans `tests/test_engine.py` :

```python
from simulator.engine import MAX_ITERATIONS


def test_convergence_nominale_circuit_lineaire():
    """Un circuit purement linéaire (RC) converge en 2 itérations
    (la 2e solution est identique à la 1re)."""
    circuit = _make_rc_circuit()
    state = SharedState()
    engine = SimulationEngine(circuit, state)
    engine._step(0.0)
    assert engine._last_iterations == 2


def test_convergence_nominale_bjt_actif():
    """Un BJT en régime actif stable converge bien en deçà du plafond."""
    circuit = _make_bjt_amplifier(ratio=0.5)
    state = SharedState()
    engine = SimulationEngine(circuit, state)
    for k in range(50):          # laisse le point de fonctionnement se stabiliser
        engine._step(k * circuit.dt)
    assert engine._last_iterations < MAX_ITERATIONS


def test_best_effort_aucune_erreur_sur_astable():
    """Même quand certains pas ne convergent pas (commutations), la simulation
    ne lève jamais d'erreur et continue d'avancer."""
    _, state, _ = _run_collect(_make_astable(), 4000)
    assert state.read()["error"] is None
```

- [ ] **Step 7 : Lancer les nouveaux tests + la suite complète**

Run: `python -m pytest tests/test_engine.py -v`
Expected : tous les tests de `test_engine.py` passent (nouveaux + existants : RC, BJT amplificateur, `_compute_sleep`).

Run: `python -m pytest tests/ -q`
Expected : toute la suite passe (non-régression sur RLC, diodes, AOp, bascules, etc.). Sortie propre.

- [ ] **Step 8 : Commit**

```bash
git add simulator/engine.py tests/test_engine.py
git commit -m "feat(engine): convergence par point fixe intra-pas des non-lineaires"
```

---

### Task 3 : Allègement des condensateurs de découplage des bascules

**Files:**
- Modify: `circuits/flip_flop_astable.json`, `circuits/flip_flop_bistable_rs.json`, `circuits/flip_flop_monostable.json`
- Modify (si nécessaire) : `tests/test_flip_flop_circuits.py` (uniquement le seuil anti-pic de `test_astable_oscille`, voir règle ci-dessous)

**Interfaces:**
- Consumes: la convergence intra-pas (Task 2).
- Produces: rien.

Règle commune : après chaque modification, lancer le(s) test(s) de comportement concerné(s) ; les seuils de comportement (bas < 1 V, haut > 3 V, transitions / mémorisation / impulsion) **ne doivent pas être relâchés**.

- [ ] **Step 1 : Astable — retirer puis, si besoin, réduire fortement `Cc`**

Dans `circuits/flip_flop_astable.json`, supprimer les composants `Cc1` et `Cc2` (les deux `capacitor` 2e-4 sur N_c1→GND et N_c2→GND). Conserver `Rb1=Rb2=100000`, `Ccpl1=1e-5`, `Ccpl2=1.2e-5`.

Lancer : `python -m pytest tests/test_flip_flop_circuits.py::test_astable_oscille -v`

Décision selon le résultat :
- Le test `test_astable_oscille` contient `assert min(samples) > -10.0`. Sans `Cc`, la convergence borne le pic vers ≈ −36 V → cette assertion échoue.
- **Option préférée** : réintroduire `Cc1`/`Cc2` avec une valeur **fortement réduite**, strictement inférieure aux condensateurs de couplage (< 10 µF). Essayer 4.7e-6, puis augmenter (6.8e-6, 1e-5 max exclu) jusqu'à ce que `min(samples) > -10.0` repasse, en gardant ≥ 4 transitions. C'est la preuve tangible : la valeur passe de 200 µF à quelques µF.
- **Option de repli** (si aucune valeur < 10 µF ne tient le seuil −10 V) : retirer `Cc` totalement et remplacer dans `tests/test_flip_flop_circuits.py`, fonction `test_astable_oscille`, l'assertion `assert min(samples) > -10.0` par `assert min(samples) > -50.0` (cohérent avec le critère moteur). Documenter ce choix par un commentaire.

Relancer jusqu'à : `python -m pytest tests/test_flip_flop_circuits.py::test_astable_oscille -v` → PASS.

- [ ] **Step 2 : Bistable — retirer `Cc` et ré-évaluer la dissymétrie**

Dans `circuits/flip_flop_bistable_rs.json`, supprimer `Cc1` et `Cc2` (les deux `capacitor` collecteur→GND : `Cc1`=4.7e-5, `Cc2`=1e-7).

Lancer les deux tests du bistable :
`python -m pytest tests/test_flip_flop_circuits.py::test_bistable_set_reset_memorise tests/test_flip_flop_circuits.py::test_bistable_power_on_etat_defini -v`

Décision selon le résultat :
- Si les **deux** passent : terminé pour le bistable (la convergence a rendu les `Cc` inutiles).
- Si `test_bistable_power_on_etat_defini` échoue (état de démarrage non défini ou tension < −1 V) : réintroduire une dissymétrie **résistive minimale** plutôt que capacitive — passer `Rb1` de 47000 à 39000 (laisser `Rb2=47000`). Re-tester les deux. Augmenter l'écart (Rb1=33000) seulement si nécessaire, sans casser `test_bistable_set_reset_memorise`.

Relancer jusqu'à : les deux tests du bistable → PASS.

- [ ] **Step 3 : Monostable — retirer `Cc`**

Dans `circuits/flip_flop_monostable.json`, supprimer `Cc1` et `Cc2` (les deux `capacitor` 1e-7 collecteur→GND). **Conserver `Ctmg` (1e-5)** qui est le condensateur temporisateur, à ne pas confondre.

Lancer : `python -m pytest tests/test_flip_flop_circuits.py::test_monostable_impulsion -v`

Décision selon le résultat :
- Si PASS : terminé.
- Si échec (repos non atteint, ou tension absurde) : réintroduire `Cc1`/`Cc2` réduits à 1e-6 (au lieu de 1e-7 d'origine ils étaient déjà petits — ici on teste si la convergence permet de s'en passer ; sinon remettre 1e-7). Re-tester.

Relancer jusqu'à PASS.

- [ ] **Step 4 : Suite complète**

Run: `python -m pytest tests/ -q`
Expected : toute la suite passe, sortie propre.

- [ ] **Step 5 : Commit**

```bash
git add circuits/flip_flop_astable.json circuits/flip_flop_bistable_rs.json circuits/flip_flop_monostable.json tests/test_flip_flop_circuits.py
git commit -m "refactor(circuits): allege les condensateurs de decouplage des bascules"
```

---

## Self-Review

**Spec coverage :**
- `is_nonlinear` sur BJT/Diode (spec §Conception 1) → Task 1. ✅
- Réécriture de `_step` avec boucle, TOL, MAX_ITERATIONS, best-effort, `_last_iterations`, recalcul réactif inchangé (spec §Conception 2) → Task 2. ✅
- Signature `stamp` inchangée (spec §Insight) → respecté (aucune tâche ne la modifie). ✅
- Heuristique BJT non réécrit (spec §Conception 3) → respecté (hors périmètre). ✅
- Tests : non-régression, suppression des excursions absurdes (−50 V), convergence nominale (`_last_iterations < MAX_ITERATIONS`), best-effort (spec §Conception 4) → Task 2 Steps 1/6/7. ✅
- Simplification des bascules : retrait/réduction `Cc`, `Rb=100k` conservé, dissymétrie ré-évaluée (spec §Conception 5) → Task 3. ✅
- Critères de succès réalistes (spec §Critères) → seuils des tests alignés (−50 V moteur, −10 V flip-flop avec règle de repli). ✅

**Placeholder scan :** aucun TODO/TBD ; tout le code Python et JSON est explicite. Les étapes empiriques (Task 3) donnent des valeurs de départ concrètes et des règles de décision, pas des « à ajuster » vagues.

**Type consistency :** `is_nonlinear` (propriété bool) défini en Task 1, consommé en Task 2 via `comp.is_nonlinear`. `_last_iterations` (int) produit en Task 2, lu par les tests de Task 2. Constantes `MAX_ITERATIONS`/`CONVERGENCE_TOL` définies et importées de façon cohérente. Helpers de test (`_make_astable`, `_run_collect`, `_count_transitions`) définis en Task 2 Step 1 et réutilisés en Step 6.

**Note d'exécution :** le risque principal est la non-régression (Task 2 change la boucle commune à tous les circuits). Les Steps 7 (Task 2) et 4 (Task 3) lancent la suite complète comme garde-fou. Si un test existant non lié casse, c'est un signal d'effet de bord de la convergence à diagnostiquer avant de continuer.
