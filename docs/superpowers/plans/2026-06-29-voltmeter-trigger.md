# Déclenchement (trigger) du graphe de mesure — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabiliser le graphe d'historique des voltmètres/ampèremètres en ré-ancrant l'affichage sur un front montant (trigger d'oscilloscope), activable par une case à cocher.

**Architecture:** Une fonction pure `compute_trigger_window` (nouveau module `ui/trigger.py`, sans dépendance GUI) calcule la fenêtre déclenchée. `DetailPanelWidget` l'appelle à chaque frame et ajoute une case à cocher « Déclenchement ». Le moteur, le `SharedState` et la collecte d'historique sont inchangés. Les circuits sinusoïdaux passent `history_size` à 3000 pour capturer ~3 périodes.

**Tech Stack:** Python 3.14, tkinter, matplotlib, pytest.

## Global Constraints

- Tous les commentaires, libellés UI et textes en **français** avec accents corrects.
- Aucune modification de `simulator/`, `shared_state.py`, ni de la collecte d'historique.
- `ui/trigger.py` ne doit **importer ni tkinter ni matplotlib** (testable en headless).
- Lancement des tests : `python -m pytest tests/ -v` depuis `c:\Dev\mna-test`.
- Spec de référence : [docs/superpowers/specs/2026-06-29-voltmeter-trigger-design.md](../specs/2026-06-29-voltmeter-trigger-design.md).

---

### Task 1: Fonction pure `compute_trigger_window`

**Files:**
- Create: `ui/trigger.py`
- Test: `tests/test_trigger.py`

**Interfaces:**
- Consumes: rien.
- Produces: `compute_trigger_window(history, width, level) -> tuple[int, int] | None`
  - `history` : séquence de floats (liste).
  - `width` : int, nombre d'échantillons de la fenêtre affichée.
  - `level` : float, niveau de déclenchement.
  - Renvoie `(start, end)` avec `end - start == width`, où `start` est le front
    montant le plus récent éligible (`history[start-1] < level <= history[start]`
    et `start + width <= len(history)`), ou `None` si aucun front éligible.

- [ ] **Step 1: Write the failing tests**

Créer `tests/test_trigger.py` :

```python
import math
from ui.trigger import compute_trigger_window


def test_rising_edge_detected():
    # Rampe : 0,1,2,...,9 ; level=4.5 → front montant unique à l'indice 5
    history = [float(i) for i in range(10)]
    win = compute_trigger_window(history, width=3, level=4.5)
    assert win == (5, 8)


def test_most_recent_eligible_edge_chosen():
    # Deux fronts montants (carré) ; on retient le plus récent dont start+width <= len
    # history index :   0  1  2  3  4  5  6  7  8  9 10 11
    history = [-1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0]
    # fronts montants à i=2 et i=7 (history[i-1] < 0 <= history[i])
    # width=3 → max_start = 12-3 = 9 ; le plus récent éligible est i=7
    win = compute_trigger_window(history, width=3, level=0.0)
    assert win == (7, 10)


def test_edge_too_recent_falls_back_to_earlier():
    # Front montant à i=2 et i=10 ; width=4 → max_start=8, donc i=10 inéligible, on prend i=2
    history = [-1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0]
    win = compute_trigger_window(history, width=4, level=0.0)
    assert win == (2, 6)


def test_no_edge_returns_none():
    history = [5.0] * 20  # signal continu plat
    assert compute_trigger_window(history, width=5, level=5.0) is None


def test_only_falling_edges_returns_none():
    history = [1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0]
    # front montant à i=4 (history[3]=-1 < 0 <= history[4]=1), width=6 → max_start=2 → inéligible
    assert compute_trigger_window(history, width=6, level=0.0) is None


def test_buffer_shorter_than_width_returns_none():
    assert compute_trigger_window([1.0, 2.0], width=5, level=1.5) is None


def test_phase_stability_under_shift():
    # Sinusoïde : un décalage arbitraire du buffer donne la même phase de départ
    def sine_buf(start, n):
        return [math.sin(2 * math.pi * (start + k) / 50.0) for k in range(n)]
    buf_a = sine_buf(0, 200)
    buf_b = sine_buf(7, 200)  # décalé de 7 échantillons
    win_a = compute_trigger_window(buf_a, width=80, level=0.0)
    win_b = compute_trigger_window(buf_b, width=80, level=0.0)
    assert win_a is not None and win_b is not None
    # La valeur au début de la fenêtre est proche de 0 et montante dans les deux cas
    for buf, (start, _end) in ((buf_a, win_a), (buf_b, win_b)):
        assert abs(buf[start]) < 0.15
        assert buf[start] > buf[start - 1]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_trigger.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'ui.trigger'`.

- [ ] **Step 3: Write the minimal implementation**

Créer `ui/trigger.py` :

```python
"""Calcul de la fenêtre d'affichage déclenchée (trigger d'oscilloscope).

Module sans dépendance GUI : volontairement testable en headless.
"""


def compute_trigger_window(history, width, level):
    """Renvoie (start, end) de la fenêtre déclenchée, ou None.

    Cherche le front montant le plus récent — indice i tel que
    history[i-1] < level <= history[i] — qui laisse assez d'échantillons
    pour afficher `width` points (i + width <= len(history)). Comme tous
    les fronts montants partagent la même phase, retenir le plus récent
    rend la trace affichée stable d'une frame à l'autre.
    """
    n = len(history)
    if width <= 0 or n < width:
        return None
    max_start = n - width
    for i in range(max_start, 0, -1):
        if history[i - 1] < level <= history[i]:
            return (i, i + width)
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_trigger.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/trigger.py tests/test_trigger.py
git commit -m "feat(ui): pure compute_trigger_window for scope-style triggering"
```

---

### Task 2: Intégrer le trigger et la case à cocher dans le panneau de détail

**Files:**
- Modify: `ui/detail_panel.py`

**Interfaces:**
- Consumes: `compute_trigger_window(history, width, level)` (Task 1).
- Produces: comportement UI ; pas d'API consommée par d'autres tâches.

- [ ] **Step 1: Importer la fonction et initialiser la case à cocher**

Dans `ui/detail_panel.py`, ajouter l'import après les imports existants
(lignes 1-3) :

```python
from ui.trigger import compute_trigger_window
```

Dans `__init__`, après le bloc `self._toggle_btn = None` / `self._ratio_slider = None`
/ `self._ratio_label = None` (lignes 30-33), ajouter la variable d'état et la
référence à la case (créée à la sélection d'un appareil de mesure) :

```python
        # Case à cocher de déclenchement (créée pour les appareils de mesure)
        self._trigger_chk = None
        self._trigger_var = tk.BooleanVar(value=True)
```

- [ ] **Step 2: Gérer le cycle de vie de la case dans `show_component`**

Dans `show_component`, après le bloc qui détruit `self._ratio_slider`
(lignes 48-50), ajouter la destruction de la case précédente :

```python
        if self._trigger_chk:
            self._trigger_chk.destroy()
            self._trigger_chk = None
```

Puis, remplacer le bloc d'affichage/masquage du graphique (lignes 80-84) :

```python
        # Affiche ou masque le graphique
        if component.records_history:
            self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            self._canvas_widget.pack_forget()
```

par une version qui crée aussi la case à cocher pour les appareils de mesure :

```python
        # Graphique et case de déclenchement pour les appareils de mesure
        if component.records_history:
            self._trigger_chk = tk.Checkbutton(
                self, text="Déclenchement", variable=self._trigger_var
            )
            self._trigger_chk.pack()
            self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            self._canvas_widget.pack_forget()
```

- [ ] **Step 3: Brancher le trigger dans `update`**

Remplacer le bloc de tracé du graphique dans `update` (lignes 106-127, depuis
`# Mise à jour du graphique pour les appareils de mesure` jusqu'à
`self._canvas.draw_idle()`) par :

```python
        # Mise à jour du graphique pour les appareils de mesure
        if comp.records_history and history:
            self._ax.clear()

            if self._trigger_var.get():
                # Fenêtre déclenchée : moitié du buffer affichée, moitié réservée
                # à la recherche de front. Axe X figé à 0..width-1.
                width = len(history) // 2 or len(history)
                level = sum(history) / len(history)
                win = compute_trigger_window(history, width, level)
                if win is not None:
                    start, end = win
                    ys = history[start:end]
                    xs = range(len(ys))
                else:
                    # Repli : derniers échantillons alignés à droite
                    ys = history[-width:]
                    xs = range(width - len(ys), width)
                x_max = width - 1
            else:
                # Comportement historique : tout le buffer aligné à droite
                n = comp.history_size
                ys = history
                xs = range(n - len(history), n)
                x_max = n - 1

            self._ax.plot(xs, ys, color="#1f77b4", linewidth=0.8)
            self._ax.axhline(0, color="#888888", linewidth=0.8, linestyle="--")
            self._ax.set_xlim(0, x_max)
            self._ax.set_ylabel("Tension (V)" if "voltmeter" in type(comp).__name__.lower()
                                else "Courant (A)")
            self._ax.set_xlabel("Échantillons")
            self._ax.grid(True, alpha=0.3)
            # Garantit que la ligne des 0 reste visible
            ymin, ymax = self._ax.get_ylim()
            if ymin > 0:
                self._ax.set_ylim(bottom=0)
            elif ymax < 0:
                self._ax.set_ylim(top=0)
            self._fig.tight_layout()
            self._canvas.draw_idle()
```

- [ ] **Step 4: Vérifier que la suite de tests passe toujours**

Run: `python -m pytest tests/ -v`
Expected: PASS (aucune régression ; les tests existants n'importent pas le GUI).

- [ ] **Step 5: Vérification manuelle de l'UI**

Run: `python main.py`
1. Ouvrir `circuits/opamp_noninverting.json`, démarrer la simulation.
2. Cliquer sur `VM_out` : la case « Déclenchement » est présente et cochée.
3. La sinusoïde affichée doit être **stable** (ne défile plus de façon erratique).
4. Décocher « Déclenchement » : la trace redéfile comme avant.
5. Re-cocher : la trace se re-stabilise.

Note : à cette étape `history_size` vaut encore 500 (½ période) ; la stabilité
sera nettement meilleure après la Task 3. Vérifier surtout l'absence de crash et
le bon fonctionnement de la case.

- [ ] **Step 6: Commit**

```bash
git add ui/detail_panel.py
git commit -m "feat(ui): scope-style trigger toggle on meter graph"
```

---

### Task 3: Augmenter la fenêtre de capture des circuits sinusoïdaux + doc

**Files:**
- Modify: `circuits/opamp_noninverting.json`
- Modify: `circuits/opamp_inverting.json`
- Modify: `circuits/rc_filter.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: rien.
- Produces: rien (données + doc).

- [ ] **Step 1: Passer `history_size` à 3000 dans les voltmètres sinusoïdaux**

Dans `circuits/opamp_noninverting.json`, remplacer les deux occurrences
`"history_size": 500` (composants `VM_in` et `VM_out`) par `"history_size": 3000`.

Dans `circuits/opamp_inverting.json`, faire de même pour tous les voltmètres
(`"history_size": 500` → `"history_size": 3000`).

Dans `circuits/rc_filter.json`, remplacer les deux `"history_size": 500`
(`VM_in` et `VM_out`) par `"history_size": 3000`.

- [ ] **Step 2: Vérifier que les circuits se chargent toujours**

Run: `python -m pytest tests/test_circuit_loader.py -v`
Expected: PASS.

Puis valider le JSON des trois fichiers :

Run: `python -c "import json; [json.load(open(f, encoding='utf-8')) for f in ['circuits/opamp_noninverting.json','circuits/opamp_inverting.json','circuits/rc_filter.json']]; print('OK')"`
Expected: `OK`.

- [ ] **Step 3: Documenter le déclenchement dans le README**

Dans `README.md`, dans la section « Utilisation », remplacer la ligne 4 :

```markdown
4. Les voltmètres et ampèremètres affichent un graphique d'historique
```

par :

```markdown
4. Les voltmètres et ampèremètres affichent un graphique d'historique. Une case
   **« Déclenchement »** (cochée par défaut) stabilise la trace des signaux
   périodiques en la ré-ancrant sur un front montant (comme un oscilloscope).
   Pour qu'il soit efficace, `history_size` doit valoir au moins ~2× la durée
   d'affichage souhaitée (afin de laisser une marge de recherche de front) :
   à `dt = 1e-5` et 100 Hz (1000 échantillons/période), `history_size = 3000`
   capture ~3 périodes.
```

- [ ] **Step 4: Vérification manuelle**

Run: `python main.py`
Ouvrir `circuits/opamp_noninverting.json`, démarrer, cliquer sur `VM_out` :
la sinusoïde doit afficher ~1,5 période et rester **stable** (case cochée).

- [ ] **Step 5: Commit**

```bash
git add circuits/opamp_noninverting.json circuits/opamp_inverting.json circuits/rc_filter.json README.md
git commit -m "feat(circuits): widen capture window for trigger; document toggle"
```

---

## Notes d'implémentation

- **Nom de fonction** : la spec mentionnait `_compute_trigger_window` ; comme
  elle vit dans un module dédié et est importée, on utilise le nom public
  `compute_trigger_window` (sans underscore), conformément à la convention Python.
- **`diode_bridge*.json`** : signaux redressés (quasi-DC pulsé), le déclenchement
  y est peu pertinent — laissés inchangés (repli automatique). À traiter
  seulement si l'utilisateur le demande.
- **Hors périmètre** : la logique qui force la ligne 0 V visible peut aplatir un
  signal à fort offset DC ; non modifiée (cf. spec).
