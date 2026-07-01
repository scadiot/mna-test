# Rectangle cliquable de bascule des switches — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher sur chaque switch un petit rectangle coloré cliquable qui bascule l'état (fermé/ouvert) sans sélectionner le composant, en mode EDIT (paramètre initial) comme en mode RUN (bascule live).

**Architecture:** La logique pure (bascule du paramètre modèle, indicateur d'état) est ajoutée/testée hors Tkinter. Le rendu du rectangle et la détection du clic vivent dans `EditorCanvas` (Tkinter, vérifiés manuellement — conforme au projet qui n'a aucun test instanciant Tk). Le canvas délègue la bascule live via un callback câblé par `UnifiedApp`.

**Tech Stack:** Python 3.14, Tkinter, pytest.

## Global Constraints

- Aucune dépendance nouvelle. Réutiliser Tkinter et le style de dessin existant.
- Ne pas instancier `tk.Tk()` dans les tests : le projet n'a aucun test canvas ; les parties Tkinter sont vérifiées par exécution manuelle de l'application.
- Interface, texte et couleurs en français (« fermé » vert, « ouvert » rouge), cohérents avec `voltage_color`/`state_indicator` existants.
- `Switch.toggle()` (déjà présent et testé) reste la seule voie de bascule live ; ne pas dupliquer sa logique.
- Ne pas modifier le format de fichier ni le modèle de données (on réutilise `params["closed"]`).

---

### Task 1 : Méthode modèle `CircuitModel.toggle_switch`

Rend la bascule EDIT testable sans Tkinter : le canvas appellera cette méthode.

**Files:**
- Modify: `editor/circuit_model.py` (ajouter une méthode après `disconnect_pin`, vers la ligne 82)
- Test: `tests/test_editor_model.py`

**Interfaces:**
- Consumes: `CircuitModel.get_component(comp_id) -> ComponentData | None`, `ComponentData.params: dict`, `CircuitModel._touch()`.
- Produces: `CircuitModel.toggle_switch(comp_id: str) -> bool` — inverse `params["closed"]` du composant, appelle `_touch()`, renvoie le nouvel état (`True`=fermé). Renvoie `False` sans effet si le composant est absent ou n'a pas de clé `closed`.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_editor_model.py` :

```python
def make_switch(id="SW1", closed=False):
    return ComponentData(id=id, type="switch", x=100.0, y=100.0, rotation=0,
                         params={"closed": closed}, pin_connections={})

def test_toggle_switch_inverts_and_marks_dirty():
    m = CircuitModel()
    m.add_component(make_switch(closed=False))
    m.mark_clean()
    assert m.toggle_switch("SW1") is True
    assert m.get_component("SW1").params["closed"] is True
    assert m.is_dirty is True
    assert m.toggle_switch("SW1") is False
    assert m.get_component("SW1").params["closed"] is False

def test_toggle_switch_missing_or_no_closed_is_noop():
    m = CircuitModel()
    m.add_component(make_resistor())
    assert m.toggle_switch("R1") is False       # pas de clé "closed"
    assert m.toggle_switch("UNKNOWN") is False   # composant absent
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_editor_model.py::test_toggle_switch_inverts_and_marks_dirty tests/test_editor_model.py::test_toggle_switch_missing_or_no_closed_is_noop -v`
Expected: FAIL avec `AttributeError: 'CircuitModel' object has no attribute 'toggle_switch'`.

- [ ] **Step 3 : Implémenter la méthode**

Dans `editor/circuit_model.py`, après la méthode `disconnect_pin` :

```python
    def toggle_switch(self, comp_id: str) -> bool:
        """Inverse l'état closed d'un switch. Renvoie le nouvel état.

        No-op renvoyant False si le composant est absent ou n'a pas de
        paramètre 'closed'.
        """
        comp = self.get_component(comp_id)
        if comp is None or "closed" not in comp.params:
            return False
        comp.params["closed"] = not comp.params["closed"]
        self._touch()
        return comp.params["closed"]
```

- [ ] **Step 4 : Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_editor_model.py -v`
Expected: PASS (tous).

- [ ] **Step 5 : Commit**

```bash
git add editor/circuit_model.py tests/test_editor_model.py
git commit -m "feat(editor): CircuitModel.toggle_switch (bascule etat initial)"
```

---

### Task 2 : Retirer la branche Switch de `state_indicator`

Le rectangle cliquable remplace le texte « fermé/ouvert » en RUN ; on évite le doublon.

**Files:**
- Modify: `editor/overlay.py:20-23` (branche `isinstance(component, Switch)`)
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `state_indicator(component, comp_state) -> tuple[str, str] | None`.
- Produces: `state_indicator` renvoie désormais `None` pour un `Switch` (branches BJT/Diode inchangées).

- [ ] **Step 1 : Mettre à jour le test qui échoue**

Dans `tests/test_overlay.py`, remplacer `test_state_indicator_switch` par :

```python
def test_state_indicator_switch_returns_none():
    sw_open = Switch("SW1", "A", "B", closed=False)
    sw_closed = Switch("SW2", "A", "B", closed=True)
    assert state_indicator(sw_open, {}) is None
    assert state_indicator(sw_closed, {}) is None
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_overlay.py::test_state_indicator_switch_returns_none -v`
Expected: FAIL — `state_indicator` renvoie encore `("ouvert", ...)` au lieu de `None`.

- [ ] **Step 3 : Retirer la branche Switch**

Dans `editor/overlay.py`, supprimer les lignes :

```python
    if isinstance(component, Switch):
        if component.closed:
            return ("fermé", "#118811")
        return ("ouvert", "#aa2222")
```

L'import `Switch` reste inutilisé dans `overlay.py` : remplacer la ligne
`from simulator.components import Switch, BJT, Diode` par
`from simulator.components import BJT, Diode`.

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_overlay.py -v`
Expected: PASS (tous).

- [ ] **Step 5 : Commit**

```bash
git add editor/overlay.py tests/test_overlay.py
git commit -m "refactor(overlay): switch sans indicateur texte (remplace par rect cliquable)"
```

---

### Task 3 : Rendu et clic du rectangle dans `EditorCanvas`

Dessine le rectangle en EDIT et en RUN, le détecte au clic, bascule sans sélectionner. Partie Tkinter → vérification manuelle (aucun test Tk dans le projet).

**Files:**
- Modify: `editor/editor_canvas.py` (constructeur, `_item_at`, `_on_press`, `_draw_component`, `draw_live_overlay`, + nouvelle méthode `_draw_switch_toggle`, + `set_on_switch_toggle`)

**Interfaces:**
- Consumes: `CircuitModel.toggle_switch(comp_id) -> bool` (Task 1) ; `self._read_only: bool` ; `comp_objects[comp.id].closed: bool` (objet `Switch`) via `draw_live_overlay`.
- Produces:
  - `EditorCanvas.set_on_switch_toggle(cb)` — enregistre `cb(comp_id: str)` appelé lors d'un clic sur le rectangle en mode RUN.
  - `_draw_switch_toggle(comp, closed: bool, overlay: bool)` — dessine le rectangle tag `swtoggle_{comp.id}`.
  - `_item_at` renvoie `("switch_toggle", comp_id)` pour un clic sur le rectangle.

- [ ] **Step 1 : Ajouter l'attribut callback dans le constructeur**

Dans `__init__` de `EditorCanvas`, après `self._on_model_change = None` (ligne ~54) :

```python
        self._on_switch_toggle = None
```

- [ ] **Step 2 : Ajouter le setter du callback**

Après `set_on_model_change` (vers la ligne 320) :

```python
    def set_on_switch_toggle(self, cb):
        self._on_switch_toggle = cb
```

- [ ] **Step 3 : Ajouter la méthode de dessin `_draw_switch_toggle`**

Après `_draw_component` (vers la ligne 397, avant `_draw_node`) :

```python
    def _draw_switch_toggle(self, comp: ComponentData, closed: bool, overlay: bool):
        """Dessine le rectangle cliquable de bascule d'un switch.

        Placé en bas de la boîte, vert « fermé » / rouge « ouvert ».
        Tag swtoggle_{id} pour la détection au clic ; tag « overlay » en RUN
        pour être nettoyé/redessiné à chaque rafraîchissement.
        """
        half = COMP_SIZE // 2
        w, h = 44, 18
        cx, cy = comp.x, comp.y + half - h // 2 - 4
        x0, y0 = cx - w // 2, cy - h // 2
        x1, y1 = cx + w // 2, cy + h // 2
        fill = "#33aa33" if closed else "#cc4444"
        label = "fermé" if closed else "ouvert"
        tags = [f"swtoggle_{comp.id}"]
        if overlay:
            tags.append("overlay")
        tags = tuple(tags)
        self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill,
                                     outline="#222222", width=1, tags=tags)
        self.canvas.create_text(cx, cy, text=label,
                                font=("TkDefaultFont", 7, "bold"),
                                fill="white", tags=tags)
```

- [ ] **Step 4 : Dessiner le rectangle en EDIT depuis `_draw_component`**

À la fin de `_draw_component` (après la boucle des pins, vers la ligne 409) :

```python
        if comp.type == "switch" and not self._read_only:
            self._draw_switch_toggle(comp, bool(comp.params.get("closed", False)),
                                     overlay=False)
```

- [ ] **Step 5 : Dessiner le rectangle en RUN depuis `draw_live_overlay`**

Dans `draw_live_overlay`, remplacer la boucle « Composants : indicateur d'état »
(vers les lignes 368-379) par :

```python
        # Composants : switch → rectangle cliquable ; autres → indicateur texte
        from simulator.components import Switch
        for comp in self.model.components:
            obj = comp_objects.get(comp.id)
            if obj is None:
                continue
            if isinstance(obj, Switch):
                self._draw_switch_toggle(comp, obj.closed, overlay=True)
                continue
            indicator = state_indicator(obj, comp_states.get(comp.id, {}))
            if indicator is None:
                continue
            label, color = indicator
            self.canvas.create_text(
                comp.x, comp.y + COMP_SIZE // 2 - 6,
                text=label, font=("TkDefaultFont", 7, "bold"),
                fill=color, tags=("overlay",))
```

- [ ] **Step 6 : Reconnaître le tag `swtoggle_` dans `_item_at`**

Dans `_item_at`, dans la boucle `for tag in tags:`, ajouter en **premier** test
(avant `if tag.startswith("pin_")`, vers la ligne 82) :

```python
                if tag.startswith("swtoggle_"):
                    return ("switch_toggle", tag[len("swtoggle_"):])
```

- [ ] **Step 7 : Basculer sans sélectionner dans `_on_press`**

Dans `_on_press`, juste après `self._drag_start = (event.x, event.y)` (ligne ~123),
avant le bloc `if self._read_only:` :

```python
        if hit and hit[0] == "switch_toggle":
            comp_id = hit[1]
            if self._read_only:
                if self._on_switch_toggle:
                    self._on_switch_toggle(comp_id)
            else:
                self.model.toggle_switch(comp_id)
                self.redraw()
                self._notify_model()
            self._state = "IDLE"
            return
```

- [ ] **Step 8 : Vérification manuelle (EDIT)**

Run: `python main.py`
- Déposer un `switch` sur le canvas : un rectangle rouge « ouvert » apparaît en bas de la boîte.
- Cliquer sur le rectangle : il passe vert « fermé », le titre affiche `*` (modifié), **le composant n'est pas sélectionné** (panneau droit inchangé, boîte non surlignée en orange).
- Cliquer ailleurs sur la boîte : le composant se sélectionne normalement (panneau propriétés).
Fermer la fenêtre.

- [ ] **Step 9 : Vérifier la non-régression des tests**

Run: `python -m pytest -q`
Expected: PASS (aucune régression).

- [ ] **Step 10 : Commit**

```bash
git add editor/editor_canvas.py
git commit -m "feat(editor): rectangle cliquable de bascule des switches sur le canvas"
```

---

### Task 4 : Câblage de la bascule live dans `UnifiedApp`

Fournit le callback RUN : bascule l'objet `Switch` et redessine l'overlay immédiatement.

**Files:**
- Modify: `ui/unified_app.py` (`_build_ui`, `_refresh`, + nouvelle méthode `_on_switch_toggle`)

**Interfaces:**
- Consumes: `EditorCanvas.set_on_switch_toggle(cb)` (Task 3) ; `self._comp_objects: dict[str, Component]` ; `Switch.toggle()`.
- Produces: `UnifiedApp._on_switch_toggle(comp_id: str)` ; `self._last_data` (dernier `state.read()`).

- [ ] **Step 1 : Câbler le callback dans `_build_ui`**

Dans `_build_ui`, après `self.canvas.set_on_model_change(self._on_model_change)` (ligne ~94) :

```python
        self.canvas.set_on_switch_toggle(self._on_switch_toggle)
```

- [ ] **Step 2 : Mémoriser les dernières données dans `_refresh`**

Dans `_refresh`, juste après `data = self._state.read()` (ligne ~199) :

```python
        self._last_data = data
```

Et initialiser l'attribut dans `__init__`, après `self._selected_run_id = None` (ligne ~36) :

```python
        self._last_data = None
```

- [ ] **Step 3 : Ajouter `_on_switch_toggle`**

Après la méthode `_on_selection` (vers la ligne 137) :

```python
    def _on_switch_toggle(self, comp_id):
        """Bascule live d'un switch en RUN, avec redessin immédiat de l'overlay."""
        if self._mode != "RUN":
            return
        obj = self._comp_objects.get(comp_id)
        if obj is None or not hasattr(obj, "toggle"):
            return
        obj.toggle()
        if self._last_data:
            self.canvas.redraw()
            self.canvas.draw_live_overlay(
                self._last_data["node_voltages"],
                self._last_data["comp_states"],
                self._comp_objects)
```

- [ ] **Step 4 : Vérification manuelle (RUN)**

Run: `python main.py`
- Ouvrir `circuits/rc_switch.json` (Ctrl+O), puis « ▶ Démarrer ».
- Le switch affiche son rectangle (rouge « ouvert » ou vert « fermé » selon l'état).
- Cliquer sur le rectangle : l'état bascule **immédiatement** (couleur + libellé), la simulation réagit (les tensions/courbes changent), **le panneau détail ne s'ouvre pas** (pas de sélection).
- Cliquer ailleurs sur la boîte du switch : le panneau détail s'ouvre normalement.
- « ⏹ Arrêter » : retour en EDIT, le rectangle reflète de nouveau `params["closed"]`.
Fermer la fenêtre.

- [ ] **Step 5 : Vérifier la non-régression des tests**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add ui/unified_app.py
git commit -m "feat(ui): bascule live des switches en RUN via rectangle cliquable"
```

---

## Notes de revue (auto-relecture)

- **Couverture de la spec** : rectangle EDIT (Task 1+3), rectangle RUN + bascule live (Task 3+4), remplacement du texte d'état par le rectangle (Task 2+3), pas de sélection au clic (Task 3 step 7), retour visuel immédiat en RUN (Task 4 step 3). ✓
- **Sûreté threads** : `Switch.toggle()` réaffecte un booléen sous GIL, pris en compte au pas suivant — aucun verrou ajouté (conforme à la spec). ✓
- **Cohérence des types** : `toggle_switch(comp_id) -> bool` défini Task 1, consommé Task 3 step 7 ; `set_on_switch_toggle`/`_on_switch_toggle` cohérents entre Task 3 et Task 4 ; tag `swtoggle_{comp.id}` cohérent entre dessin (step 3) et détection (step 6). ✓
- **Parties non testées automatiquement** : dessin/clic Tkinter (Task 3-4) vérifiés manuellement, faute de tests Tk dans le projet ; logique pure couverte par pytest (Task 1-2). ✓
