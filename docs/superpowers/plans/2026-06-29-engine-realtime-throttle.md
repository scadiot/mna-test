# Throttle temps réel du moteur — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empêcher le moteur de simulation de saturer un cœur CPU quand un circuit est trop lourd pour le temps réel, en ralentissant proprement au lieu de spinner.

**Architecture :** Extraire la décision de cadencement dans une fonction pure `_compute_sleep`, testable sans thread ni horloge réelle, puis recâbler `_run_loop` pour l'utiliser avec une échéance ré-ancrée et un throttle proportionnel au coût du pas.

**Tech Stack :** Python 3, `numpy`, `pytest`, module `time` (standard).

## Global Constraints

- Fichier de code modifié : `simulator/engine.py` uniquement.
- Aucun changement d'API publique (`__init__`, `start`, `stop`, `_step`, `_build_maps` inchangés).
- Aucun changement du format de circuit JSON.
- `THROTTLE_RATIO = 1.0` (plafonne l'usage d'un cœur à ~50 %).
- La fonction de timing doit être pure (aucun effet de bord, pas d'accès horloge/thread).

---

### Task 1 : Fonction de cadencement pure `_compute_sleep`

**Files:**
- Modify: `simulator/engine.py` (ajout d'une constante de module et d'une fonction au niveau module, avant la classe `SimulationEngine`)
- Test: `tests/test_engine.py` (ajout de tests)

**Interfaces:**
- Consumes: rien (fonction autonome).
- Produces:
  - Constante module `THROTTLE_RATIO: float = 1.0`
  - Fonction `_compute_sleep(step_duration: float, now: float, next_deadline: float, dt: float) -> tuple[float, float]`
    retournant `(sleep_seconds, new_deadline)`.
    - Si `next_deadline - now > 0` (en avance) : `sleep_seconds = next_deadline - now`, `new_deadline = next_deadline + dt`.
    - Sinon (en retard ou pile à l'heure) : `sleep_seconds = step_duration * THROTTLE_RATIO`, `new_deadline = now + dt`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_engine.py` :

```python
from simulator.engine import _compute_sleep, THROTTLE_RATIO


def test_compute_sleep_when_ahead_sleeps_until_deadline():
    # now avant l'échéance → on dort le slack, échéance avancée de dt
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.00001, now=100.0, next_deadline=100.0003, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.0003)
    assert new_deadline == pytest.approx(100.0003 + 1e-4)


def test_compute_sleep_when_behind_throttles_and_reanchors():
    # now après l'échéance → throttle proportionnel au coût du pas, ré-ancrage sur now
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.002, now=100.5, next_deadline=100.0, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.002 * THROTTLE_RATIO)
    assert new_deadline == pytest.approx(100.5 + 1e-4)


def test_compute_sleep_exactly_on_time_is_treated_as_behind():
    # slack nul → branche "en retard" : throttle appliqué, ré-ancrage sur now
    sleep_s, new_deadline = _compute_sleep(
        step_duration=0.0005, now=100.0, next_deadline=100.0, dt=1e-4
    )
    assert sleep_s == pytest.approx(0.0005 * THROTTLE_RATIO)
    assert new_deadline == pytest.approx(100.0 + 1e-4)


def test_compute_sleep_behind_caps_cpu_fraction():
    # La fraction d'occupation CPU ne dépasse pas 1/(1+THROTTLE_RATIO)
    step_duration = 0.003
    sleep_s, _ = _compute_sleep(
        step_duration=step_duration, now=100.5, next_deadline=100.0, dt=1e-4
    )
    cpu_fraction = step_duration / (step_duration + sleep_s)
    assert cpu_fraction <= 1.0 / (1.0 + THROTTLE_RATIO) + 1e-9
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `python -m pytest tests/test_engine.py -k compute_sleep -v`
Expected: FAIL — `ImportError: cannot import name '_compute_sleep'`.

- [ ] **Step 3: Implémenter la fonction et la constante**

Dans `simulator/engine.py`, après les imports (ligne 5) et avant `class SimulationEngine`, insérer :

```python
# Plafond d'occupation CPU d'un cœur quand le moteur est en retard : la durée
# de sommeil vaut step_duration * THROTTLE_RATIO, ce qui borne la fraction CPU
# à 1 / (1 + THROTTLE_RATIO). 1.0 → ~50 % d'un cœur au maximum.
THROTTLE_RATIO = 1.0


def _compute_sleep(step_duration, now, next_deadline, dt):
    """
    Décide combien de temps dormir après un pas de simulation (fonction pure).

    step_duration : durée d'exécution réelle du pas qui vient d'être calculé (s)
    now           : instant courant (time.monotonic())
    next_deadline : échéance temps réel visée pour ce pas
    dt            : pas de temps simulé (s)

    Retourne (sleep_seconds, new_deadline).
      - En avance (now < next_deadline) : on dort le slack restant et l'échéance
        suivante avance de dt → cadence temps réel pour les circuits légers.
      - En retard (now >= next_deadline) : on ne spinne pas. On dort une durée
        proportionnelle au coût du pas (throttle) et on ré-ancre l'échéance sur
        now pour ne pas accumuler de dette → slow-motion à CPU borné.
    """
    slack = next_deadline - now
    if slack > 0:
        return slack, next_deadline + dt
    return step_duration * THROTTLE_RATIO, now + dt
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_engine.py -k compute_sleep -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add simulator/engine.py tests/test_engine.py
git commit -m "feat(engine): add pure _compute_sleep timing helper with CPU throttle"
```

---

### Task 2 : Recâbler `_run_loop` sur `_compute_sleep`

**Files:**
- Modify: `simulator/engine.py:98-125` (corps de `_run_loop`)
- Test: `tests/test_engine.py` (tests existants `test_rc_charges_to_source_voltage`, `test_no_error_on_valid_circuit` servent de garde-fou de non-régression)

**Interfaces:**
- Consumes: `_compute_sleep`, `THROTTLE_RATIO` (Task 1).
- Produces: `_run_loop` qui chronomètre chaque pas, appelle `_compute_sleep`, dort le résultat et reprend la nouvelle échéance.

- [ ] **Step 1: Remplacer le corps de `_run_loop`**

Remplacer intégralement la méthode `_run_loop` (actuellement [engine.py:98-125](../../../simulator/engine.py#L98-L125)) par :

```python
    def _run_loop(self):
        """Boucle principale du simulateur (tourne dans un thread séparé)."""
        t = 0.0
        with self._state._lock:
            self._state.running = True

        # Échéance temps réel glissante : ré-ancrée quand le moteur prend du
        # retard (cf. _compute_sleep) pour ne jamais saturer un cœur CPU.
        next_deadline = time.monotonic() + self._dt

        while True:
            # Vérifie si l'arrêt a été demandé
            with self._state._lock:
                if not self._state.running:
                    break

            step_start = time.monotonic()
            ok = self._step(t)
            if not ok:
                break   # erreur MNA → arrêt propre
            step_duration = time.monotonic() - step_start

            t += self._dt

            sleep_s, next_deadline = _compute_sleep(
                step_duration, time.monotonic(), next_deadline, self._dt
            )
            if sleep_s > 0:
                time.sleep(sleep_s)
```

- [ ] **Step 2: Lancer la suite de tests moteur (non-régression)**

Run: `python -m pytest tests/test_engine.py -v`
Expected: PASS — tous les tests, y compris `test_rc_charges_to_source_voltage` et `test_no_error_on_valid_circuit` (le RC se charge toujours à ~5 V, aucune erreur MNA).

- [ ] **Step 3: Vérifier la suite complète**

Run: `python -m pytest -v`
Expected: PASS — aucune régression ailleurs.

- [ ] **Step 4: Commit**

```bash
git add simulator/engine.py
git commit -m "fix(engine): throttle real-time loop to avoid CPU saturation"
```

---

## Notes d'exécution

- Sur Windows, `time.sleep` a une granularité limitée ; le throttle proportionnel
  reste correct car il borne la fraction CPU indépendamment de la granularité (un
  sommeil plus long que demandé ne fait que ralentir davantage, sans saturer).
- Vérification manuelle facultative après implémentation : lancer l'app sur
  `circuits/potar_transistor.json` et observer que l'usage CPU reste modéré.
