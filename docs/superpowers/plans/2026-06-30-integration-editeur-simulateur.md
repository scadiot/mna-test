# Intégration éditeur + simulateur — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fusionner l'éditeur et le simulateur en une seule application où un canvas unique sert à dessiner le circuit (mode EDIT) puis à afficher les résultats live en superposition (mode RUN), sans passer par le disque.

**Architecture:** Un nouvel orchestrateur `UnifiedApp(tk.Tk)` coordonne les widgets existants (`EditorCanvas`, `ComponentPanel`, `PropertiesPanel`, `DetailPanelWidget`) et gère une machine à états EDIT ↔ RUN, le `SimulationEngine` et le `SharedState`. Le pont de données réutilise le fait que le dict sérialisé par l'éditeur est exactement le format lu par le simulateur : on factorise `build_circuit(dict)` dans `circuit_loader` et on construit le `Circuit` en mémoire via `model_to_dict(model)`.

**Tech Stack:** Python 3.10+, Tkinter, NumPy, Matplotlib, pytest.

## Global Constraints

- Python 3.10+ ; dépendances limitées à `numpy`, `matplotlib`, Tkinter (stdlib). Pas de nouvelle dépendance.
- Tous les libellés et messages destinés à l'utilisateur sont en français, avec accents corrects.
- TDD pour toute logique pure (sans Tk). Le rendu Tkinter (canvas, overlay, fenêtre) n'est **pas** testé unitairement — il est vérifié manuellement, conformément à la spec.
- `pytest tests/ -v` doit rester vert à chaque commit (aucune régression).
- Commits fréquents, un par tâche au minimum.

---

### Task 1 : Factoriser `build_circuit(dict)` dans `circuit_loader`

**Files:**
- Modify: `circuit_loader.py` (fonction `load_circuit`, lignes 91-116)
- Test: `tests/test_circuit_loader.py`

**Interfaces:**
- Produces: `build_circuit(data: dict) -> Circuit` — construit un `Circuit` depuis un dict déjà désérialisé (mêmes règles que `load_circuit` : création des composants, exigence d'un nœud `"GND"`, détection des historiques). `load_circuit(path)` est conservé et délègue à `build_circuit`.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_circuit_loader.py` :

```python
def test_build_circuit_from_dict_without_file():
    from circuit_loader import build_circuit
    data = {
        "name": "En mémoire",
        "dt": 1e-5,
        "components": [
            {"id": "V1", "type": "voltage_source", "node_pos": "N1", "node_neg": "GND",
             "params": {"waveform": "dc", "amplitude": 5.0}},
            {"id": "R1", "type": "resistor", "node_a": "N1", "node_b": "GND",
             "params": {"resistance": 1000.0}},
        ],
    }
    circuit = build_circuit(data)
    assert isinstance(circuit, Circuit)
    assert circuit.name == "En mémoire"
    assert circuit.dt == 1e-5
    assert len(circuit.components) == 2


def test_build_circuit_requires_gnd():
    from circuit_loader import build_circuit
    data = {"name": "Sans masse", "dt": 1e-5,
            "components": [{"id": "R1", "type": "resistor",
                            "node_a": "N1", "node_b": "N2",
                            "params": {"resistance": 1000.0}}]}
    with pytest.raises(ValueError):
        build_circuit(data)
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `pytest tests/test_circuit_loader.py::test_build_circuit_from_dict_without_file -v`
Expected: FAIL avec `ImportError: cannot import name 'build_circuit'`.

- [ ] **Step 3 : Refactorer `load_circuit`**

Remplacer la fonction `load_circuit` (lignes 91-116) par :

```python
def build_circuit(data):
    """
    Construit un Circuit depuis un dict déjà désérialisé.
    Lève ValueError si le format est invalide ou si GND est absent.
    """
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


def load_circuit(path):
    """
    Charge et valide un fichier JSON de circuit.
    Lève ValueError si le format est invalide ou si GND est absent.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return build_circuit(data)
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `pytest tests/test_circuit_loader.py -v`
Expected: PASS (anciens + nouveaux tests).

- [ ] **Step 5 : Commit**

```bash
git add circuit_loader.py tests/test_circuit_loader.py
git commit -m "refactor(loader): extrait build_circuit(dict) reutilisable sans disque"
```

---

### Task 2 : `model_to_dict` dans `editor/io.py`

**Files:**
- Modify: `editor/io.py` (fonction `save_circuit`, lignes 79-101)
- Test: `tests/test_editor_io.py`

**Interfaces:**
- Consumes: `circuit_loader.build_circuit` (Task 1), `editor.circuit_model.CircuitModel`.
- Produces: `model_to_dict(model: CircuitModel) -> dict` — produit le dict JSON (clés `name`, `dt`, `nodes`, `components`) identique à ce qu'écrit `save_circuit`. `save_circuit` est réécrit pour déléguer à `model_to_dict`.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_editor_io.py` :

```python
def test_model_to_dict_matches_save_circuit(tmp_path):
    from editor.io import model_to_dict, save_circuit
    from editor.circuit_model import CircuitModel, ComponentData, NodeData
    import json

    model = CircuitModel()
    model.name = "T"
    model.add_node(NodeData(id="GND", x=10, y=10, is_gnd=True))
    model.add_node(NodeData(id="N1", x=20, y=20))
    model.add_component(ComponentData(
        id="R1", type="resistor", x=30, y=30, rotation=0,
        params={"resistance": 1000.0},
        pin_connections={"node_a": "N1", "node_b": "GND"}))

    path = tmp_path / "c.json"
    save_circuit(model, str(path))
    with open(path, encoding="utf-8") as f:
        written = json.load(f)

    assert model_to_dict(model) == written


def test_model_to_dict_feeds_build_circuit():
    from editor.io import model_to_dict
    from circuit_loader import build_circuit, Circuit
    from editor.circuit_model import CircuitModel, ComponentData, NodeData

    model = CircuitModel()
    model.add_node(NodeData(id="GND", x=0, y=0, is_gnd=True))
    model.add_node(NodeData(id="N1", x=0, y=0))
    model.add_component(ComponentData(
        id="R1", type="resistor", x=0, y=0, rotation=0,
        params={"resistance": 1000.0},
        pin_connections={"node_a": "N1", "node_b": "GND"}))

    circuit = build_circuit(model_to_dict(model))
    assert isinstance(circuit, Circuit)
    assert len(circuit.components) == 1
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `pytest tests/test_editor_io.py::test_model_to_dict_matches_save_circuit -v`
Expected: FAIL avec `ImportError: cannot import name 'model_to_dict'`.

- [ ] **Step 3 : Ajouter `model_to_dict` et réécrire `save_circuit`**

Remplacer la fonction `save_circuit` (lignes 79-101) par :

```python
def model_to_dict(model: CircuitModel) -> dict:
    nodes = [{"id": n.id, "x": n.x, "y": n.y} for n in model.nodes]

    components = []
    for c in model.components:
        obj: dict = {
            "id": c.id,
            "type": c.type,
            "x": c.x,
            "y": c.y,
            "rotation": c.rotation,
        }
        obj.update(c.pin_connections)
        obj["params"] = c.params
        components.append(obj)

    return {"name": model.name, "dt": model.dt,
            "nodes": nodes, "components": components}


def save_circuit(model: CircuitModel, path: str) -> None:
    data = model_to_dict(model)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    model.mark_clean()
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `pytest tests/test_editor_io.py -v`
Expected: PASS (anciens + nouveaux tests).

- [ ] **Step 5 : Commit**

```bash
git add editor/io.py tests/test_editor_io.py
git commit -m "feat(editor): model_to_dict pour construire un circuit en memoire"
```

---

### Task 3 : Validation pré-simulation

**Files:**
- Create: `editor/validation.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Consumes: `editor.circuit_model.CircuitModel`, `editor.editor_canvas.COMPONENT_TEMPLATES`.
- Produces: `validate_for_simulation(model: CircuitModel) -> list[str]` — liste des messages d'erreur (vide si le circuit est simulable). Vérifie : circuit non vide, toutes les pattes connectées, un nœud `"GND"` connecté.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_validation.py` :

```python
from editor.validation import validate_for_simulation
from editor.circuit_model import CircuitModel, ComponentData, NodeData


def _model_with(components, nodes):
    m = CircuitModel()
    for n in nodes:
        m.add_node(n)
    for c in components:
        m.add_component(c)
    return m


def test_valid_circuit_returns_no_errors():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "N1", "node_b": "GND"})],
        [NodeData(id="N1", x=0, y=0), NodeData(id="GND", x=0, y=0, is_gnd=True)])
    assert validate_for_simulation(m) == []


def test_empty_circuit_is_invalid():
    assert validate_for_simulation(CircuitModel()) != []


def test_unconnected_pin_is_reported():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "GND"})],
        [NodeData(id="GND", x=0, y=0, is_gnd=True)])
    errors = validate_for_simulation(m)
    assert any("node_b" in e for e in errors)


def test_missing_gnd_is_reported():
    m = _model_with(
        [ComponentData(id="R1", type="resistor", x=0, y=0, rotation=0,
                       params={"resistance": 1000.0},
                       pin_connections={"node_a": "N1", "node_b": "N2"})],
        [NodeData(id="N1", x=0, y=0), NodeData(id="N2", x=0, y=0)])
    errors = validate_for_simulation(m)
    assert any("GND" in e for e in errors)
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `pytest tests/test_validation.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'editor.validation'`.

- [ ] **Step 3 : Implémenter la validation**

Créer `editor/validation.py` :

```python
# editor/validation.py
from editor.circuit_model import CircuitModel
from editor.editor_canvas import COMPONENT_TEMPLATES


def validate_for_simulation(model: CircuitModel) -> list[str]:
    """Retourne la liste des erreurs empêchant de simuler le circuit.

    Liste vide => le circuit peut être simulé.
    """
    errors: list[str] = []

    if not model.components:
        errors.append("Le circuit est vide.")

    # Toutes les pattes de chaque composant doivent être connectées à un nœud.
    for comp in model.components:
        template = COMPONENT_TEMPLATES.get(comp.type, {})
        for pin in template.get("pins", []):
            if pin.name not in comp.pin_connections:
                errors.append(f"{comp.id} : patte '{pin.name}' non connectée.")

    # Au moins un nœud GND doit être relié à un composant.
    connected_nodes = set()
    for comp in model.components:
        connected_nodes.update(comp.pin_connections.values())
    if "GND" not in connected_nodes:
        errors.append("Aucun nœud 'GND' (masse) connecté à un composant.")

    return errors
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `pytest tests/test_validation.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add editor/validation.py tests/test_validation.py
git commit -m "feat(editor): validation pre-simulation (pattes, GND, circuit vide)"
```

---

### Task 4 : Helpers d'overlay (couleur tension + indicateur d'état)

**Files:**
- Create: `editor/overlay.py`
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `simulator.components.{Switch, BJT, Diode}`.
- Produces:
  - `voltage_color(v: float, vmin: float, vmax: float) -> str` — couleur hex `#rrggbb` sur une échelle bleu (vmin) → rouge (vmax). Borné à `[vmin, vmax]`. Si `vmax == vmin`, renvoie une couleur médiane.
  - `state_indicator(component, comp_state: dict) -> tuple[str, str] | None` — `(libellé, couleur_hex)` pour Switch / BJT / Diode, sinon `None`.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_overlay.py` :

```python
from editor.overlay import voltage_color, state_indicator
from simulator.components import Switch, BJT, Diode


def test_voltage_color_extremes():
    assert voltage_color(0.0, 0.0, 10.0) == "#0000ff"   # bleu = min
    assert voltage_color(10.0, 0.0, 10.0) == "#ff0000"  # rouge = max


def test_voltage_color_clamps_and_handles_flat_range():
    # hors bornes -> clampé
    assert voltage_color(-5.0, 0.0, 10.0) == "#0000ff"
    assert voltage_color(99.0, 0.0, 10.0) == "#ff0000"
    # plage plate -> pas de division par zéro, couleur médiane
    c = voltage_color(3.0, 3.0, 3.0)
    assert c.startswith("#") and len(c) == 7


def test_state_indicator_switch():
    sw_open = Switch("SW1", "A", "B", closed=False)
    sw_closed = Switch("SW2", "A", "B", closed=True)
    assert state_indicator(sw_open, {})[0] == "ouvert"
    assert state_indicator(sw_closed, {})[0] == "fermé"


def test_state_indicator_bjt():
    q = BJT("Q1", "b", "c", "e")
    assert state_indicator(q, {"current": 0.0})[0] == "bloqué"
    assert state_indicator(q, {"current": 1e-3, "saturated": True})[0] == "saturé"
    assert state_indicator(q, {"current": 1e-3, "saturated": False})[0] == "actif"


def test_state_indicator_diode():
    d = Diode("D1", "a", "k")
    assert state_indicator(d, {"current": 1e-3})[0] == "passante"
    assert state_indicator(d, {"current": 0.0})[0] == "bloquée"


def test_state_indicator_other_returns_none():
    from simulator.components import Resistor
    assert state_indicator(Resistor("R1", "a", "b", 1000.0), {"current": 1.0}) is None
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run: `pytest tests/test_overlay.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'editor.overlay'`.

- [ ] **Step 3 : Implémenter les helpers**

Créer `editor/overlay.py` :

```python
# editor/overlay.py
from simulator.components import Switch, BJT, Diode


def voltage_color(v: float, vmin: float, vmax: float) -> str:
    """Couleur hex sur une échelle bleu (vmin) -> rouge (vmax), bornée."""
    span = vmax - vmin
    if span < 1e-12:
        t = 0.5
    else:
        t = (v - vmin) / span
        t = max(0.0, min(1.0, t))
    r = round(255 * t)
    bl = round(255 * (1.0 - t))
    return f"#{r:02x}00{bl:02x}"


def state_indicator(component, comp_state: dict):
    """(libellé, couleur) pour les composants à état visible, sinon None."""
    if isinstance(component, Switch):
        if component.closed:
            return ("fermé", "#118811")
        return ("ouvert", "#aa2222")
    if isinstance(component, BJT):
        i_b = comp_state.get("current", 0.0)
        if i_b <= 1e-9:
            return ("bloqué", "#888888")
        if comp_state.get("saturated"):
            return ("saturé", "#aa6600")
        return ("actif", "#118811")
    if isinstance(component, Diode):
        if comp_state.get("current", 0.0) > 1e-6:
            return ("passante", "#118811")
        return ("bloquée", "#888888")
    return None
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `pytest tests/test_overlay.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5 : Commit**

```bash
git add editor/overlay.py tests/test_overlay.py
git commit -m "feat(editor): helpers overlay (couleur tension, indicateur d'etat)"
```

---

### Task 5 : Mode lecture seule du canvas

**Files:**
- Modify: `editor/editor_canvas.py` (`__init__` ligne 39-57, `_on_press` 114-156, `_on_motion` 158-196, `_on_double_click` 220-231, `_on_delete` 233-273, `drop_component` 372-383)

**Interfaces:**
- Consumes: rien de nouveau.
- Produces: `EditorCanvas.set_read_only(value: bool)` — en lecture seule, le canvas n'autorise plus aucune mutation (déplacement, connexion, création/suppression, dépose) ; seule la **sélection** d'un composant ou d'un nœud reste possible (pour choisir le mètre affiché en RUN).

- [ ] **Step 1 : Ajouter l'attribut et la méthode**

Dans `__init__`, après `self._state = "IDLE"` (ligne 46), ajouter :

```python
        self._read_only = False
```

Ajouter la méthode publique juste après `_bind_events` (après la ligne 66) :

```python
    def set_read_only(self, value: bool):
        """Active/désactive le mode lecture seule (sélection autorisée, mutations bloquées)."""
        self._read_only = value
```

- [ ] **Step 2 : Bloquer les mutations dans `_on_press`**

Au début de `_on_press`, juste après `self._drag_start = (event.x, event.y)` (ligne 117) et avant `if hit is None:`, insérer la branche lecture seule :

```python
        if self._read_only:
            if hit is None:
                self._deselect()
                return
            kind = hit[0]
            if kind in ("comp", "pin"):
                self._selected_comp = hit[1]
                self._selected_node = None
                self._selected_wire = None
            elif kind == "node":
                self._selected_comp = None
                self._selected_node = hit[1]
                self._selected_wire = None
            self._state = "SELECTED"
            self.redraw()
            self._notify_selection()
            return
```

(Note : `pin` sélectionne le composant porteur, car `hit[1]` est le `comp_id` pour `kind == "pin"`.)

- [ ] **Step 3 : Neutraliser les autres mutations**

Ajouter `if self._read_only: return` comme **première ligne** du corps de chacune des méthodes suivantes :
- `_on_motion` (après la signature, ligne 158)
- `_on_double_click` (ligne 220)
- `_on_delete` (ligne 233)
- `drop_component` (ligne 372)

Exemple pour `_on_motion` :

```python
    def _on_motion(self, event):
        if self._read_only:
            return
        if self._state == "SELECTED":
            ...
```

- [ ] **Step 4 : Vérifier l'absence de régression**

Run: `pytest tests/ -v`
Expected: PASS (les tests existants ne touchent pas le canvas ; rien ne doit casser).

- [ ] **Step 5 : Commit**

```bash
git add editor/editor_canvas.py
git commit -m "feat(editor): mode lecture seule du canvas (selection seule)"
```

---

### Task 6 : Couche d'overlay live sur le canvas

**Files:**
- Modify: `editor/editor_canvas.py` (imports en tête, ajout d'une méthode après `redraw` ligne 297-304)

**Interfaces:**
- Consumes: `editor.overlay.{voltage_color, state_indicator}` (Task 4) ; constantes `NODE_RADIUS`, `COMP_SIZE` (déjà dans le module).
- Produces: `EditorCanvas.draw_live_overlay(node_voltages: dict, comp_states: dict, comp_objects: dict)` — dessine, par-dessus le schéma, les étiquettes de tension, le code couleur des nœuds et les indicateurs d'état. Tous les items portent le tag `"overlay"`. `comp_objects` est `{comp_id: composant_simulateur}`.

- [ ] **Step 1 : Ajouter l'import**

En tête de `editor/editor_canvas.py`, après `from editor.circuit_model import ...` (ligne 5), ajouter :

```python
from editor.overlay import voltage_color, state_indicator
```

- [ ] **Step 2 : Ajouter la méthode `draw_live_overlay`**

Juste après la méthode `redraw` (après la ligne 304), insérer :

```python
    def draw_live_overlay(self, node_voltages: dict, comp_states: dict, comp_objects: dict):
        """Superpose tensions, code couleur des nœuds et indicateurs d'état.

        À appeler après redraw() en mode simulation. node_voltages : {nom: V}.
        comp_states : {id: {"voltage","current",...}}. comp_objects : {id: composant}.
        """
        self.canvas.delete("overlay")

        values = list(node_voltages.values())
        vmin = min(values) if values else 0.0
        vmax = max(values) if values else 0.0

        # Nœuds : remplissage coloré (sauf GND) + étiquette de tension
        for node in self.model.nodes:
            v = node_voltages.get(node.id)
            if v is None:
                continue
            if not node.is_gnd:
                color = voltage_color(v, vmin, vmax)
                self.canvas.create_oval(
                    node.x - NODE_RADIUS, node.y - NODE_RADIUS,
                    node.x + NODE_RADIUS, node.y + NODE_RADIUS,
                    fill=color, outline="#2255aa", tags=("overlay",))
            self.canvas.create_text(
                node.x, node.y + NODE_RADIUS + 9,
                text=f"{v:+.2f} V", font=("TkDefaultFont", 7, "bold"),
                fill="#003366", tags=("overlay",))

        # Composants : indicateur d'état (switch / BJT / diode)
        for comp in self.model.components:
            obj = comp_objects.get(comp.id)
            if obj is None:
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

- [ ] **Step 3 : Vérifier l'absence de régression**

Run: `pytest tests/ -v`
Expected: PASS (la nouvelle méthode n'est pas encore appelée ; rien ne casse). Vérifie aussi que `editor/editor_canvas.py` s'importe sans erreur :
Run: `python -c "import editor.editor_canvas"`
Expected: aucune sortie d'erreur.

- [ ] **Step 4 : Commit**

```bash
git add editor/editor_canvas.py
git commit -m "feat(editor): draw_live_overlay (tensions, couleurs noeuds, etats)"
```

---

### Task 7 : Activation/désactivation de la palette

**Files:**
- Modify: `editor/component_panel.py` (`__init__` ligne 14-32, `_on_list_press` ligne 34-45)

**Interfaces:**
- Produces: `ComponentPanel.set_enabled(value: bool)` — désactive la palette (drag-drop) en mode RUN.

- [ ] **Step 1 : Ajouter l'attribut d'état**

Dans `__init__`, après `self._drag_type: str | None = None` (ligne 18), ajouter :

```python
        self._enabled = True
```

- [ ] **Step 2 : Ajouter la méthode et le garde-fou**

Ajouter la méthode après `__init__` (après la ligne 32) :

```python
    def set_enabled(self, value: bool):
        """Active ou désactive la palette (drag-drop) — désactivée en simulation."""
        self._enabled = value
        self._listbox.config(state=tk.NORMAL if value else tk.DISABLED)
```

Au début de `_on_list_press` (ligne 35), ajouter :

```python
        if not self._enabled:
            return
```

- [ ] **Step 3 : Vérifier l'absence de régression**

Run: `python -c "import editor.component_panel"`
Expected: aucune erreur.
Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 4 : Commit**

```bash
git add editor/component_panel.py
git commit -m "feat(editor): ComponentPanel.set_enabled pour figer la palette en RUN"
```

---

### Task 8 : Orchestrateur `UnifiedApp`

**Files:**
- Create: `ui/unified_app.py`

**Interfaces:**
- Consumes: `circuit_loader.build_circuit` (T1), `editor.io.model_to_dict` (T2), `editor.validation.validate_for_simulation` (T3), `EditorCanvas.set_read_only`/`draw_live_overlay` (T5/T6), `ComponentPanel.set_enabled` (T7), `PropertiesPanel`, `DetailPanelWidget`, `SimulationEngine`, `SharedState`, `CircuitModel`.
- Produces: `UnifiedApp(tk.Tk)` — fenêtre unique avec machine à états EDIT ↔ RUN.

- [ ] **Step 1 : Écrire l'orchestrateur**

Créer `ui/unified_app.py` :

```python
# ui/unified_app.py
import tkinter as tk
from tkinter import filedialog, messagebox

from shared_state import SharedState
from circuit_loader import build_circuit
from simulator.engine import SimulationEngine
from editor.circuit_model import CircuitModel
from editor.editor_canvas import EditorCanvas
from editor.component_panel import ComponentPanel
from editor.properties_panel import PropertiesPanel
from editor.validation import validate_for_simulation
from editor import io
from ui.detail_panel import DetailPanelWidget


class UnifiedApp(tk.Tk):
    """Application unifiée : édition (mode EDIT) et simulation (mode RUN)
    sur un canvas unique."""

    REFRESH_MS = 200   # rafraîchissement UI à 5 Hz en mode RUN

    def __init__(self):
        super().__init__()
        self.geometry("1200x720")
        self.minsize(900, 500)

        self.model = CircuitModel()
        self._current_file = None
        self._mode = "EDIT"            # "EDIT" | "RUN"
        self._state = SharedState()
        self._engine = None
        self._circuit = None
        self._comp_objects = {}        # {id: composant simulateur}
        self._selected_run_id = None

        self._build_ui()
        self._schedule_refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Raccourcis fichier (mode EDIT)
        self.bind("<Control-n>", lambda e: self._new())
        self.bind("<Control-o>", lambda e: self._open())
        self.bind("<Control-s>", lambda e: self._save())

        self._update_title()

    # ── Construction de l'UI ────────────────────────────────────────────────
    def _build_ui(self):
        bar = tk.Frame(self, bd=1, relief=tk.RIDGE)
        bar.pack(fill=tk.X, side=tk.TOP)

        tk.Button(bar, text="📄 Nouveau", command=self._new).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="📂 Ouvrir", command=self._open).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="💾 Enregistrer", command=self._save).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="💾+ Enr. sous", command=self._save_as).pack(side=tk.LEFT, padx=3, pady=4)

        self._run_btn = tk.Button(bar, text="▶  Démarrer", command=self._toggle_simulation)
        self._run_btn.pack(side=tk.RIGHT, padx=5, pady=4)
        self._status_label = tk.Label(bar, text="", fg="red")
        self._status_label.pack(side=tk.RIGHT, padx=10)

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        self.canvas = EditorCanvas(body, self.model)

        self.comp_panel = ComponentPanel(body, self.canvas, self)
        self.comp_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Panneau droit : propriétés (EDIT) ou graphe (RUN) — swap par pack/pack_forget
        self._right = tk.Frame(body)
        self._right.pack(side=tk.RIGHT, fill=tk.Y)
        self._props = PropertiesPanel(self._right, self.model, self.canvas)
        self._detail = DetailPanelWidget(self._right)
        self._props.pack(fill=tk.BOTH, expand=True)

        self.canvas.set_on_selection_change(self._on_selection)
        self.canvas.set_on_model_change(self._on_model_change)

    def _show_props_panel(self):
        self._detail.pack_forget()
        self._props.pack(fill=tk.BOTH, expand=True)

    def _show_detail_panel(self):
        self._props.pack_forget()
        self._detail.pack(fill=tk.BOTH, expand=True)

    # ── Titre ────────────────────────────────────────────────────────────────
    def _update_title(self):
        prefix = "* " if self.model.is_dirty else ""
        name = self.model.name or "Nouveau circuit"
        suffix = " — Simulation" if self._mode == "RUN" else ""
        self.title(f"{prefix}{name} — Éditeur/Simulateur{suffix}")

    def _on_model_change(self):
        self._update_title()

    # ── Sélection ──────────────────────────────────────────────────────────
    def _on_selection(self, comp_id, node_id):
        if self._mode == "RUN":
            if comp_id and comp_id in self._comp_objects:
                self._selected_run_id = comp_id
                self._detail.show_component(self._comp_objects[comp_id])
            return
        if comp_id:
            self._props.show_component(comp_id)
        elif node_id:
            self._props.show_node(node_id)
        else:
            self._props.show_empty()

    # ── Machine à états EDIT ↔ RUN ───────────────────────────────────────────
    def _toggle_simulation(self):
        if self._mode == "RUN":
            self._stop_to_edit()
        else:
            self._start_run()

    def _start_run(self):
        errors = validate_for_simulation(self.model)
        if errors:
            messagebox.showerror("Circuit invalide", "\n".join(errors))
            return
        try:
            self._circuit = build_circuit(io.model_to_dict(self.model))
        except Exception as e:
            messagebox.showerror("Erreur de construction", str(e))
            return

        self._comp_objects = {c.id: c for c in self._circuit.components}
        self._state = SharedState()
        for cid, hist_size in self._circuit.histories.items():
            self._state.init_histories([cid], hist_size)

        self._engine = SimulationEngine(self._circuit, self._state)
        self._engine.start()

        self._mode = "RUN"
        self._selected_run_id = None
        self.canvas.set_read_only(True)
        self.comp_panel.set_enabled(False)
        self._show_detail_panel()
        self._run_btn.config(text="⏹  Arrêter")
        self._status_label.config(text="")
        self._update_title()

    def _stop_to_edit(self):
        if self._engine:
            self._engine.stop()
            self._engine = None
        self._mode = "EDIT"
        self._comp_objects = {}
        self._selected_run_id = None
        self.canvas.set_read_only(False)
        self.comp_panel.set_enabled(True)
        self.canvas.redraw()       # efface l'overlay (delete("all"))
        self._show_props_panel()
        self._props.show_empty()
        self._run_btn.config(text="▶  Démarrer")
        self._update_title()

    # ── Rafraîchissement RUN ─────────────────────────────────────────────────
    def _schedule_refresh(self):
        self._refresh()
        self.after(self.REFRESH_MS, self._schedule_refresh)

    def _refresh(self):
        if self._mode != "RUN":
            return
        data = self._state.read()
        if data["error"]:
            self._status_label.config(text=f"Erreur : {data['error']}")
            self._stop_to_edit()
            return
        self.canvas.redraw()
        self.canvas.draw_live_overlay(
            data["node_voltages"], data["comp_states"], self._comp_objects)
        if self._selected_run_id:
            cs = data["comp_states"].get(self._selected_run_id, {})
            history = data["histories"].get(self._selected_run_id, [])
            self._detail.update(cs, history, self._circuit.dt)

    # ── Opérations fichier (mode EDIT) ───────────────────────────────────────
    def _confirm_unsaved(self) -> bool:
        if not self.model.is_dirty:
            return True
        return messagebox.askyesno(
            "Modifications non sauvegardées",
            "Des modifications non sauvegardées seront perdues. Continuer ?")

    def _ensure_edit_mode(self):
        if self._mode == "RUN":
            self._stop_to_edit()

    def _new(self):
        self._ensure_edit_mode()
        if not self._confirm_unsaved():
            return
        self.model = CircuitModel()
        self._current_file = None
        self.canvas.model = self.model
        self._props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self._props.show_empty()
        self._update_title()

    def _open(self):
        self._ensure_edit_mode()
        if not self._confirm_unsaved():
            return
        path = filedialog.askopenfilename(
            title="Ouvrir un circuit",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")],
            initialdir="circuits")
        if not path:
            return
        try:
            self.model = io.load_circuit(path)
        except Exception as e:
            messagebox.showerror("Erreur de chargement", str(e))
            return
        self._current_file = path
        self.canvas.model = self.model
        self._props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self._props.show_empty()
        self._update_title()

    def _save(self):
        self._ensure_edit_mode()
        if self._current_file is None:
            self._save_as()
            return
        try:
            io.save_circuit(self.model, self._current_file)
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", str(e))
            return
        self._update_title()

    def _save_as(self):
        self._ensure_edit_mode()
        path = filedialog.asksaveasfilename(
            title="Enregistrer sous", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialdir="circuits")
        if not path:
            return
        self._current_file = path
        self._save()

    def _on_close(self):
        if self._mode == "RUN":
            self._stop_to_edit()
        if self._confirm_unsaved():
            self.destroy()
```

- [ ] **Step 2 : Vérifier l'import**

Run: `python -c "import ui.unified_app"`
Expected: aucune erreur d'import.

- [ ] **Step 3 : Vérification manuelle (lancement temporaire)**

Run: `python -c "from ui.unified_app import UnifiedApp; UnifiedApp().mainloop()"`

Vérifier visuellement :
1. La fenêtre s'ouvre : palette à gauche, canvas au centre, panneau Propriétés à droite.
2. Glisser un `voltage_source`, un `resistor`, deux nœuds + un `GND` ; relier les pattes ; cliquer « ▶ Démarrer ».
3. En RUN : la palette est grisée, le schéma est figé, des étiquettes `« x.xx V »` apparaissent près des nœuds, les nœuds se colorent, le bouton affiche « ⏹ Arrêter ».
4. Ajouter un `switch` relié et observer l'étiquette « ouvert »/« fermé » (cliquer le switch → bouton Basculer dans le panneau droit).
5. Cliquer « ⏹ Arrêter » : retour en édition, palette réactivée, overlay effacé, panneau Propriétés réaffiché.
6. Démarrer sans GND → message « Circuit invalide ».

Fermer la fenêtre.

- [ ] **Step 4 : Commit**

```bash
git add ui/unified_app.py
git commit -m "feat(ui): UnifiedApp orchestrateur edition+simulation (modes EDIT/RUN)"
```

---

### Task 9 : Point d'entrée et nettoyage

**Files:**
- Modify: `main.py`
- Delete: `ui/app.py`, `editor/main.py`, `ui/component_list.py`
- Modify: `README.md`, `editor/README.md`

**Interfaces:**
- Consumes: `ui.unified_app.UnifiedApp` (T8).

- [ ] **Step 1 : Rediriger le point d'entrée**

Remplacer le contenu de `main.py` par :

```python
# main.py — Point d'entrée de l'application unifiée (édition + simulation)
from ui.unified_app import UnifiedApp

if __name__ == "__main__":
    app = UnifiedApp()
    app.mainloop()
```

- [ ] **Step 2 : Confirmer l'absence de consommateurs avant suppression**

Run: `grep -rn "ui.app\|ui\.component_list\|editor.main\|from ui.app\|import component_list" --include=*.py .`
Expected: aucune occurrence en dehors des fichiers à supprimer eux-mêmes. (Si une occurrence inattendue apparaît, l'adapter avant de poursuivre.)

- [ ] **Step 3 : Supprimer les fichiers redondants**

```bash
git rm ui/app.py editor/main.py ui/component_list.py
```

- [ ] **Step 4 : Vérifier le lancement et les tests**

Run: `python -c "import main"`
Expected: aucune erreur d'import.
Run: `pytest tests/ -v`
Expected: PASS (tous les tests, y compris ceux ajoutés en T1–T4).

- [ ] **Step 5 : Mettre à jour la documentation**

Dans `README.md` :
- Section « Lancement » : conserver `python main.py` mais préciser qu'il lance désormais l'application unifiée (édition + simulation dans une fenêtre unique).
- Section « Utilisation » : remplacer le flux « Ouvrir circuit → Démarrer » par : dessiner/ouvrir un circuit dans le canvas, puis « ▶ Démarrer » pour simuler (le schéma se fige et affiche tensions, couleurs et états en live) ; « ⏹ Arrêter » pour revenir à l'édition.
- Section « Structure du projet » : remplacer le bloc `ui/` par :
  ```
  ui/
  ├── unified_app.py        ← fenêtre unique édition + simulation
  ├── detail_panel.py       ← panneau détail + graphe matplotlib (mode RUN)
  └── trigger.py            ← fenêtre de déclenchement oscilloscope
  editor/
  ├── editor_canvas.py      ← canvas 2D (édition + overlay live)
  ├── component_panel.py    ← palette gauche (drag-drop)
  ├── properties_panel.py   ← panneau propriétés (mode EDIT)
  ├── circuit_model.py      ← modèle du circuit (nœuds, composants, positions)
  ├── validation.py         ← validation pré-simulation
  ├── overlay.py            ← helpers couleur tension + indicateur d'état
  └── io.py                 ← lecture/écriture JSON + model_to_dict
  ```

Dans `editor/README.md` :
- Remplacer la section « Lancement » : l'éditeur n'a plus de point d'entrée autonome ; il est intégré à l'application principale (`python main.py`). Les modules `editor/` restent les widgets d'édition réutilisés par `ui/unified_app.py`.
- Supprimer la référence à `editor/main.py` dans la section « Structure du module ».

- [ ] **Step 6 : Commit**

```bash
git add main.py README.md editor/README.md
git commit -m "feat(app): main.py lance UnifiedApp; supprime les lanceurs redondants"
```

---

## Self-Review

**Spec coverage :**
- Vue unique / deux modes EDIT↔RUN → T5 (read-only), T8 (machine à états). ✓
- Pont de données sans disque → T1 (`build_circuit`), T2 (`model_to_dict`), utilisés en T8. ✓
- Overlay : tensions aux nœuds + code couleur + indicateurs d'état → T4 (helpers), T6 (rendu), T8 (appel). ✓
- Panneau graphe conservé → T8 réutilise `DetailPanelWidget`, swap de panneau. ✓
- Gel palette → T7. ✓
- Validation pré-run + erreurs claires → T3, affichées en T8. ✓
- Crash moteur remonté → T8 `_refresh` lit `data["error"]` et repasse en EDIT. ✓
- `is_dirty`/confirmation conservée → T8 `_confirm_unsaved` sur Nouveau/Ouvrir/fermeture. ✓
- Point d'entrée unique + suppression `ui/app.py`, `editor/main.py`, `ui/component_list.py` + READMEs → T9. ✓
- Tests : `build_circuit`, `model_to_dict`, validation, mapping état → T1–T4 (TDD). ✓

**Placeholder scan :** aucun « TBD/TODO », aucune ligne morte, chaque étape de code contient le code complet.

**Type consistency :**
- `build_circuit(data: dict) -> Circuit` (T1) ↔ appelé avec `io.model_to_dict(...)` (T8). ✓
- `model_to_dict(model) -> dict` (T2) ↔ consommé par `build_circuit` (T8). ✓
- `validate_for_simulation(model) -> list[str]` (T3) ↔ `if errors:` (T8). ✓
- `voltage_color` / `state_indicator` (T4) ↔ importés et appelés dans `draw_live_overlay` (T6). ✓
- `set_read_only(bool)` (T5), `draw_live_overlay(node_voltages, comp_states, comp_objects)` (T6), `set_enabled(bool)` (T7) ↔ appelés avec ces signatures exactes en T8. ✓
- `comp_objects = {id: composant}` (T8) ↔ 3ᵉ paramètre de `draw_live_overlay` et source de `state_indicator(obj, ...)`. ✓
