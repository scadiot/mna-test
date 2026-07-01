# Vue combinée multi-courbes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher les historiques de tous les voltmètres et ampèremètres d'un circuit sur un seul graphe (une couleur par courbe) pour observer les déphasages, comme vue par défaut du panneau droit en mode RUN quand aucun appareil n'est sélectionné.

**Architecture:** Toute la logique pure (choix de la fenêtre déclenchée partagée, construction des séries à tracer, choix de l'unité de temps) est isolée dans un nouveau module headless `ui/plot_utils.py`, testé unitairement. Un nouveau widget GUI `CombinedGraphWidget` (`ui/combined_panel.py`) consomme ces helpers et dessine avec matplotlib. `ui/unified_app.py` permute désormais trois panneaux dans la zone droite (props / detail / combined) et route les rafraîchissements selon l'état de sélection. Aucune modification du simulateur ni de `SharedState`.

**Tech Stack:** Python, Tkinter, matplotlib (backend TkAgg), pytest.

## Global Constraints

- Les modules de logique pure restent **sans dépendance GUI** (testables en headless), cf. `ui/trigger.py`.
- Les appareils de mesure sont les composants dont `records_history` vaut `True` (`Voltmeter`, `Ammeter`).
- L'unité d'un appareil se déduit de son nom de classe : `"V"` si `"voltmeter"` est dans `type(comp).__name__.lower()`, sinon `"A"` (même heuristique que `ui/detail_panel.py`).
- Les historiques sont des listes de `float` (issues de `SharedState.read()["histories"]`), toutes de même longueur car alimentées d'un `append` par pas de simulation.
- Commentaires et libellés d'interface en français.

---

### Task 1: Module de logique pure `ui/plot_utils.py`

Isole trois fonctions pures testables : `time_unit` (déplacée depuis `detail_panel`), `shared_trigger_window` (fenêtre déclenchée commune), `build_combined_series` (séries à tracer). Refactore `detail_panel` pour réutiliser `time_unit`.

**Files:**
- Create: `ui/plot_utils.py`
- Create: `tests/test_plot_utils.py`
- Modify: `ui/detail_panel.py` (retire `_time_unit` local, importe `time_unit`)

**Interfaces:**
- Produces:
  - `time_unit(duration: float) -> tuple[str, float]` — renvoie `(libellé, facteur)` tel que `valeur_en_s * facteur` donne la valeur dans l'unité.
  - `shared_trigger_window(ref_history: list[float], trigger_on: bool) -> tuple[int, int] | None` — renvoie `(start, end)` pour découper toutes les courbes, ou `None` (= afficher le buffer complet). `None` si `trigger_on` faux, `ref_history` vide, ou aucun front trouvé.
  - `build_combined_series(histories: dict[str, list[float]], comp_objects: dict, window: tuple[int, int] | None) -> list[tuple[str, list[float]]]` — renvoie `[(label, ys), ...]` pour chaque appareil ayant `records_history` et un historique non vide, dans l'ordre d'itération de `comp_objects`. `label` = `f"{id} ({unité})"`. `ys` = `hist[start:end]` si `window`, sinon `hist` complet.

- [ ] **Step 1: Écrire les tests de `time_unit`**

Créer `tests/test_plot_utils.py` :

```python
import math
import pytest
from ui.plot_utils import time_unit, shared_trigger_window, build_combined_series
from simulator.components import Voltmeter, Ammeter


def test_time_unit_seconds():
    assert time_unit(2.0) == ("s", 1.0)


def test_time_unit_milliseconds():
    assert time_unit(5e-3) == ("ms", 1e3)


def test_time_unit_microseconds():
    assert time_unit(5e-6) == ("µs", 1e6)


def test_time_unit_nanoseconds():
    assert time_unit(5e-9) == ("ns", 1e9)
```

- [ ] **Step 2: Lancer les tests → échec attendu**

Run: `python -m pytest tests/test_plot_utils.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'ui.plot_utils'`

- [ ] **Step 3: Créer `ui/plot_utils.py` avec `time_unit`**

```python
"""Helpers de tracé sans dépendance GUI (testables en headless).

Regroupe le choix d'unité de temps et la préparation des données pour les
graphes des appareils de mesure (voltmètres / ampèremètres).
"""
from ui.trigger import compute_trigger_window


def time_unit(duration):
    """Choisit une unité de temps lisible pour une durée donnée (en s).

    Renvoie (libellé, facteur) tel que `valeur_en_s * facteur` donne la
    valeur exprimée dans l'unité retournée.
    """
    if duration >= 1.0:
        return "s", 1.0
    if duration >= 1e-3:
        return "ms", 1e3
    if duration >= 1e-6:
        return "µs", 1e6
    return "ns", 1e9
```

- [ ] **Step 4: Lancer les tests `time_unit` → succès**

Run: `python -m pytest tests/test_plot_utils.py -v -k time_unit`
Expected: 4 tests PASS

- [ ] **Step 5: Écrire les tests de `shared_trigger_window`**

Ajouter à `tests/test_plot_utils.py` :

```python
def test_shared_window_off_returns_none():
    assert shared_trigger_window([1.0, 2.0, 3.0, 4.0], trigger_on=False) is None


def test_shared_window_empty_returns_none():
    assert shared_trigger_window([], trigger_on=True) is None


def test_shared_window_on_matches_compute():
    # Rampe 0..19 ; width = 20//2 = 10 ; level = moyenne = 9.5
    # front montant à i=10 (history[9]=9 < 9.5 <= history[10]=10) ; max_start = 10
    hist = [float(i) for i in range(20)]
    assert shared_trigger_window(hist, trigger_on=True) == (10, 20)


def test_shared_window_preserves_phase_offset():
    # Deux sinusoïdes échantillonnées sur la MÊME base de temps, l'une déphasée.
    # La fenêtre calculée sur la référence, appliquée aux deux, conserve l'écart.
    n = 200
    ref = [math.sin(2 * math.pi * k / 50.0) for k in range(n)]
    other = [math.sin(2 * math.pi * k / 50.0 + math.pi / 2) for k in range(n)]
    win = shared_trigger_window(ref, trigger_on=True)
    assert win is not None
    start, end = win
    ref_slice = ref[start:end]
    other_slice = other[start:end]
    # même longueur, indices alignés → l'écart de phase est préservé
    assert len(ref_slice) == len(other_slice)
    # à l'index 0 de la fenêtre : ref ≈ 0 montant, other ≈ cos(0) = 1
    assert abs(ref_slice[0]) < 0.15
    assert other_slice[0] > 0.9
```

- [ ] **Step 6: Lancer → échec attendu**

Run: `python -m pytest tests/test_plot_utils.py -v -k shared_window`
Expected: FAIL avec `AttributeError` / `ImportError` (fonction absente)

- [ ] **Step 7: Implémenter `shared_trigger_window`**

Ajouter à `ui/plot_utils.py` :

```python
def shared_trigger_window(ref_history, trigger_on):
    """Fenêtre (start, end) commune à toutes les courbes, ou None.

    Calculée sur le signal de référence : demi-buffer affiché, demi réservé
    à la recherche de front, niveau = moyenne du signal. Renvoie None (=
    afficher le buffer complet) si le déclenchement est désactivé, si la
    référence est vide, ou si aucun front n'est trouvé.
    """
    if not trigger_on or not ref_history:
        return None
    width = len(ref_history) // 2 or len(ref_history)
    level = sum(ref_history) / len(ref_history)
    return compute_trigger_window(ref_history, width, level)
```

- [ ] **Step 8: Lancer → succès**

Run: `python -m pytest tests/test_plot_utils.py -v -k shared_window`
Expected: 4 tests PASS

- [ ] **Step 9: Écrire les tests de `build_combined_series`**

Ajouter à `tests/test_plot_utils.py` :

```python
def test_build_series_labels_and_units():
    comp_objects = {
        "V1": Voltmeter("V1", "a", "b"),
        "A1": Ammeter("A1", "b", "c"),
    }
    histories = {"V1": [1.0, 2.0, 3.0], "A1": [0.1, 0.2, 0.3]}
    series = build_combined_series(histories, comp_objects, window=None)
    assert series == [("V1 (V)", [1.0, 2.0, 3.0]), ("A1 (A)", [0.1, 0.2, 0.3])]


def test_build_series_applies_window():
    comp_objects = {"V1": Voltmeter("V1", "a", "b")}
    histories = {"V1": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]}
    series = build_combined_series(histories, comp_objects, window=(2, 5))
    assert series == [("V1 (V)", [2.0, 3.0, 4.0])]


def test_build_series_skips_empty_and_non_recording():
    class Dummy:
        records_history = False
    comp_objects = {
        "V1": Voltmeter("V1", "a", "b"),
        "V2": Voltmeter("V2", "c", "d"),  # historique absent
        "R1": Dummy(),                     # n'enregistre pas
    }
    histories = {"V1": [1.0], "V2": []}
    series = build_combined_series(histories, comp_objects, window=None)
    assert series == [("V1 (V)", [1.0])]
```

- [ ] **Step 10: Lancer → échec attendu**

Run: `python -m pytest tests/test_plot_utils.py -v -k build_series`
Expected: FAIL (fonction absente)

- [ ] **Step 11: Implémenter `build_combined_series`**

Ajouter à `ui/plot_utils.py` :

```python
def _meter_unit(comp):
    """Renvoie 'V' pour un voltmètre, 'A' sinon (heuristique par nom de classe)."""
    return "V" if "voltmeter" in type(comp).__name__.lower() else "A"


def build_combined_series(histories, comp_objects, window):
    """Prépare les courbes à tracer pour la vue combinée.

    Renvoie [(label, ys), ...] pour chaque appareil ayant `records_history`
    et un historique non vide, dans l'ordre de `comp_objects`. `label` porte
    l'ID et l'unité. `ys` est découpé selon `window=(start, end)` si fourni,
    sinon le buffer complet.
    """
    series = []
    for cid, comp in comp_objects.items():
        if not getattr(comp, "records_history", False):
            continue
        hist = histories.get(cid)
        if not hist:
            continue
        if window is not None:
            start, end = window
            ys = list(hist[start:end])
        else:
            ys = list(hist)
        series.append((f"{cid} ({_meter_unit(comp)})", ys))
    return series
```

- [ ] **Step 12: Lancer tout le fichier → succès**

Run: `python -m pytest tests/test_plot_utils.py -v`
Expected: tous les tests PASS

- [ ] **Step 13: Refactorer `detail_panel.py` pour réutiliser `time_unit`**

Dans `ui/detail_panel.py`, remplacer l'import et supprimer la fonction locale.

Remplacer les lignes d'en-tête (1-19) :

```python
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.trigger import compute_trigger_window


def _time_unit(duration):
    """Choisit une unité de temps lisible pour une durée donnée (en s).

    Renvoie (libellé, facteur) tel que `valeur_en_s * facteur` donne la
    valeur exprimée dans l'unité retournée.
    """
    if duration >= 1.0:
        return "s", 1.0
    if duration >= 1e-3:
        return "ms", 1e3
    if duration >= 1e-6:
        return "µs", 1e6
    return "ns", 1e9
```

par :

```python
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.trigger import compute_trigger_window
from ui.plot_utils import time_unit
```

Puis remplacer l'unique appel `unit, scale = _time_unit(x_max * dt)` par `unit, scale = time_unit(x_max * dt)`.

- [ ] **Step 14: Lancer la suite complète → aucune régression**

Run: `python -m pytest -q`
Expected: tous les tests PASS (dont `tests/test_plot_utils.py`), aucune régression

- [ ] **Step 15: Commit**

```bash
git add ui/plot_utils.py tests/test_plot_utils.py ui/detail_panel.py
git commit -m "feat(ui): module plot_utils (time_unit, fenetre commune, series combinees)"
```

---

### Task 2: Widget GUI `CombinedGraphWidget`

Crée le panneau qui trace toutes les courbes avec une couleur par appareil, une légende, un menu déroulant de référence et une case « Déclenchement ». Consomme les helpers de la Task 1.

**Files:**
- Create: `ui/combined_panel.py`

**Interfaces:**
- Consumes: `ui.plot_utils.time_unit`, `ui.plot_utils.shared_trigger_window`, `ui.plot_utils.build_combined_series`.
- Produces:
  - `CombinedGraphWidget(parent: tk.Widget)` — `tk.Frame`.
  - `.set_meters(comp_objects: dict) -> None` — peuple le menu déroulant avec les IDs des appareils ayant `records_history`; sélectionne le premier par défaut. Appelé une fois au démarrage RUN.
  - `.update(histories: dict, comp_objects: dict, dt: float | None) -> None` — redessine toutes les courbes à chaque rafraîchissement.

- [ ] **Step 1: Écrire un test fumée d'import/construction**

Le tracé GUI n'est pas testé unitairement (cohérent avec `detail_panel`). On vérifie seulement que le module s'importe et expose la bonne interface. Créer `tests/test_combined_panel.py` :

```python
import inspect
import ui.combined_panel as cp


def test_widget_exposes_interface():
    assert hasattr(cp, "CombinedGraphWidget")
    for name in ("set_meters", "update"):
        assert callable(getattr(cp.CombinedGraphWidget, name))

    sig = inspect.signature(cp.CombinedGraphWidget.update)
    assert list(sig.parameters) == ["self", "histories", "comp_objects", "dt"]
```

- [ ] **Step 2: Lancer → échec attendu**

Run: `python -m pytest tests/test_combined_panel.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'ui.combined_panel'`

- [ ] **Step 3: Implémenter `ui/combined_panel.py`**

```python
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.plot_utils import time_unit, shared_trigger_window, build_combined_series

# Palette cyclique : une couleur par courbe (cycle matplotlib « tab10 »).
_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


class CombinedGraphWidget(tk.Frame):
    """Panneau RUN affiché quand aucun appareil n'est sélectionné.

    Trace les historiques de tous les appareils de mesure sur un seul axe,
    une couleur par courbe, pour comparer les déphasages. Déclenchement
    optionnel sur un appareil de référence choisi dans un menu déroulant.
    """

    def __init__(self, parent):
        super().__init__(parent, relief=tk.SUNKEN, bd=1)

        # Barre de contrôles : case déclenchement + menu de référence
        controls = tk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=6)

        self._trigger_var = tk.BooleanVar(value=True)
        tk.Checkbutton(controls, text="Déclenchement",
                       variable=self._trigger_var).pack(side=tk.LEFT)

        tk.Label(controls, text="Réf. :").pack(side=tk.LEFT, padx=(10, 2))
        self._ref_var = tk.StringVar(value="")
        self._ref_menu = ttk.Combobox(
            controls, textvariable=self._ref_var, state="readonly", width=12
        )
        self._ref_menu.pack(side=tk.LEFT)

        # Figure matplotlib
        self._fig = Figure(figsize=(4, 2.5), dpi=90)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True,
                                          padx=5, pady=5)

    def set_meters(self, comp_objects):
        """Peuple le menu déroulant avec les IDs des appareils de mesure."""
        ids = [cid for cid, comp in comp_objects.items()
               if getattr(comp, "records_history", False)]
        self._ref_menu["values"] = ids
        if ids:
            self._ref_var.set(ids[0])
        else:
            self._ref_var.set("")

    def update(self, histories, comp_objects, dt=None):
        """Redessine toutes les courbes (appelé à 5 Hz en mode RUN)."""
        self._ax.clear()

        ref_id = self._ref_var.get()
        ref_history = histories.get(ref_id, [])
        window = shared_trigger_window(ref_history, self._trigger_var.get())
        series = build_combined_series(histories, comp_objects, window)

        if not series:
            self._ax.text(0.5, 0.5, "Aucun appareil de mesure",
                          ha="center", va="center", transform=self._ax.transAxes,
                          color="#888888")
            self._canvas.draw_idle()
            return

        # Longueur commune = plus courte série (buffers alignés en début de fenêtre)
        length = min(len(ys) for _label, ys in series)
        if dt:
            unit, scale = time_unit(max(length - 1, 1) * dt)
            xs = [k * dt * scale for k in range(length)]
            xlabel = f"Temps ({unit})"
        else:
            xs = list(range(length))
            xlabel = "Échantillons"

        for idx, (label, ys) in enumerate(series):
            color = _PALETTE[idx % len(_PALETTE)]
            self._ax.plot(xs, ys[:length], color=color, linewidth=0.8, label=label)

        self._ax.axhline(0, color="#888888", linewidth=0.8, linestyle="--")
        self._ax.set_xlabel(xlabel)
        self._ax.set_ylabel("Valeur (V / A)")
        self._ax.grid(True, alpha=0.3)
        self._ax.legend(loc="upper right", fontsize=7)
        self._fig.tight_layout()
        self._canvas.draw_idle()
```

- [ ] **Step 4: Lancer le test fumée → succès**

Run: `python -m pytest tests/test_combined_panel.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/combined_panel.py tests/test_combined_panel.py
git commit -m "feat(ui): widget CombinedGraphWidget (toutes les courbes sur un graphe)"
```

---

### Task 3: Intégration dans `unified_app` (permutation à trois panneaux)

Ajoute le panneau combiné dans la zone droite et route l'affichage/rafraîchissement selon l'état de sélection en mode RUN.

**Files:**
- Modify: `ui/unified_app.py` (imports, `_build_ui`, ajout `_show_combined_panel`, `_start_run`, `_on_selection`, `_refresh`)

**Interfaces:**
- Consumes: `ui.combined_panel.CombinedGraphWidget` et son API `set_meters` / `update`.

- [ ] **Step 1: Importer le widget**

Dans `ui/unified_app.py`, après la ligne `from ui.detail_panel import DetailPanelWidget` :

```python
from ui.detail_panel import DetailPanelWidget
from ui.combined_panel import CombinedGraphWidget
```

- [ ] **Step 2: Instancier le panneau combiné dans `_build_ui`**

Dans `_build_ui`, après `self._detail = DetailPanelWidget(self._right)` :

```python
self._detail = DetailPanelWidget(self._right)
self._combined = CombinedGraphWidget(self._right)
self._props.pack(fill=tk.BOTH, expand=True)
```

(la ligne `self._props.pack(...)` existe déjà juste après ; ne pas la dupliquer — insérer seulement la ligne `self._combined = ...`)

- [ ] **Step 3: Ajouter le helper de permutation**

Après la méthode `_show_detail_panel` :

```python
    def _show_detail_panel(self):
        self._props.pack_forget()
        self._combined.pack_forget()
        self._detail.pack(fill=tk.BOTH, expand=True)

    def _show_combined_panel(self):
        self._props.pack_forget()
        self._detail.pack_forget()
        self._combined.pack(fill=tk.BOTH, expand=True)
```

(remplacer l'actuel `_show_detail_panel` par cette version qui masque aussi `_combined`, et ajouter `_show_combined_panel`. Mettre aussi à jour `_show_props_panel` pour masquer `_combined` — voir Step 4.)

- [ ] **Step 4: Mettre à jour `_show_props_panel`**

Remplacer :

```python
    def _show_props_panel(self):
        self._detail.pack_forget()
        self._props.pack(fill=tk.BOTH, expand=True)
```

par :

```python
    def _show_props_panel(self):
        self._detail.pack_forget()
        self._combined.pack_forget()
        self._props.pack(fill=tk.BOTH, expand=True)
```

- [ ] **Step 5: Afficher le combiné au démarrage RUN**

Dans `_start_run`, remplacer la ligne `self._show_detail_panel()` par :

```python
        self._combined.set_meters(self._comp_objects)
        self._show_combined_panel()
```

- [ ] **Step 6: Router la sélection RUN**

Dans `_on_selection`, remplacer le bloc du mode RUN :

```python
        if self._mode == "RUN":
            if comp_id and comp_id in self._comp_objects:
                self._selected_run_id = comp_id
                self._detail.show_component(self._comp_objects[comp_id])
            else:
                self._selected_run_id = None
            return
```

par :

```python
        if self._mode == "RUN":
            if comp_id and comp_id in self._comp_objects:
                self._selected_run_id = comp_id
                self._detail.show_component(self._comp_objects[comp_id])
                self._show_detail_panel()
            else:
                self._selected_run_id = None
                self._show_combined_panel()
            return
```

- [ ] **Step 7: Router le rafraîchissement**

Dans `_refresh`, remplacer :

```python
        if self._selected_run_id:
            cs = data["comp_states"].get(self._selected_run_id, {})
            history = data["histories"].get(self._selected_run_id, [])
            self._detail.update(cs, history, self._circuit.dt)
```

par :

```python
        if self._selected_run_id:
            cs = data["comp_states"].get(self._selected_run_id, {})
            history = data["histories"].get(self._selected_run_id, [])
            self._detail.update(cs, history, self._circuit.dt)
        else:
            self._combined.update(
                data["histories"], self._comp_objects, self._circuit.dt)
```

- [ ] **Step 8: Vérifier la suite de tests → aucune régression**

Run: `python -m pytest -q`
Expected: tous les tests PASS

- [ ] **Step 9: Vérification manuelle**

Run: `python main.py`
Attendu :
1. Ouvrir un circuit contenant au moins deux appareils de mesure (ex. deux voltmètres sur un circuit alternatif) et cliquer sur ▶ Démarrer.
2. Sans rien sélectionner, le panneau droit montre **toutes** les courbes sur un seul graphe, chacune d'une couleur, avec une légende (`V1 (V)`, `A1 (A)`, ...).
3. La case « Déclenchement » stabilise la forme d'onde ; le menu « Réf. » change l'appareil de référence.
4. Cliquer sur un appareil bascule sur la vue détaillée d'un seul ; cliquer dans le vide (désélection) revient à la vue combinée.
5. Arrêter (⏹) revient au panneau de propriétés (mode EDIT).

- [ ] **Step 10: Commit**

```bash
git add ui/unified_app.py
git commit -m "feat(ui): vue combinee par defaut en RUN, permutation props/detail/combined"
```

---

## Self-Review

- **Couverture du spec :** Task 1 = logique pure (fenêtre commune, séries, unité de temps) ; Task 2 = widget (un axe, valeurs brutes, palette + légende, menu de référence + case déclenchement, message si aucun appareil) ; Task 3 = accès (vue par défaut si rien sélectionné, permutation à trois panneaux, routage sélection/refresh). Refactor `time_unit` couvert (Task 1, steps 13-14). Tous les points du spec sont couverts.
- **Placeholders :** aucun ; tout le code et tous les tests sont fournis intégralement.
- **Cohérence des types :** `shared_trigger_window`, `build_combined_series`, `time_unit`, `set_meters`, `update(histories, comp_objects, dt)` sont utilisés avec des signatures identiques entre les tâches.
