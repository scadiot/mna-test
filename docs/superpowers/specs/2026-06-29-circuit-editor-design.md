# Éditeur de circuit électronique — Spécification de design
Date : 2026-06-29

## Objectif

Créer une petite application Python dans le sous-répertoire `editor/` permettant de créer et éditer visuellement les fichiers JSON de circuits électroniques du répertoire `circuits/`. L'éditeur produit un format JSON étendu (avec positions) compatible avec le simulateur existant, qui ignore les champs inconnus.

---

## Architecture globale

Architecture plate (Option A) : peu de fichiers, logique regroupée dans le canvas, sans sur-abstraction. Cohérent avec le style pédagogique/minimaliste du projet.

```
mna-test/
└── editor/
    ├── __init__.py
    ├── main.py              ← point d'entrée, crée la fenêtre Tk principale
    ├── circuit_model.py     ← données du circuit (composants, nœuds, liaisons)
    ├── editor_canvas.py     ← vue 2D, machine à états, tout le canvas Tkinter
    ├── component_panel.py   ← panneau gauche : liste des types draggables
    ├── properties_panel.py  ← panneau droit : propriétés du composant sélectionné
    ├── toolbar.py           ← barre d'outils (nouveau, ouvrir, enregistrer, enr. sous)
    └── io.py                ← lecture/écriture JSON (format étendu)
```

Le module `editor/` est indépendant du simulateur — il ne lit ni n'importe rien depuis `simulator/` ou `ui/`.

### Disposition de la fenêtre

```
┌─────────────────────────────────────────────────────────────┐
│  [📄 Nouveau]  [📂 Ouvrir]  [💾 Enregistrer]  [💾+ Enr.sous]│  toolbar.py
├────────────────┬────────────────────────────┬───────────────┤
│  Composants    │                            │  Propriétés   │
│                │                            │               │
│  resistor      │      Canvas 2D             │  ID: R1       │
│  capacitor     │      (EditorCanvas)        │  Type: resist │
│  inductor      │                            │  Rotation: 0° │
│  switch        │                            │  resistance:  │
│  voltage_src   │                            │  [1000.0    ] │
│  current_src   │                            │               │
│  voltmeter     │                            │  Pattes:      │
│  ammeter       │                            │  node_a → N1  │
│  transistor    │                            │  node_b → N2  │
│  opamp         │                            │               │
│  diode         │                            │               │
│  ─────         │                            │               │
│  GND           │                            │               │
└────────────────┴────────────────────────────┴───────────────┘
```

---

## Format JSON étendu

Les fichiers produits par l'éditeur ajoutent une clé `"nodes"` au niveau racine, et les champs `"x"`, `"y"`, `"rotation"` dans chaque composant. Le simulateur ignore ces champs inconnus — la compatibilité est préservée.

```json
{
  "name": "Filtre RC passe-bas",
  "dt": 1e-5,
  "nodes": [
    { "id": "N1", "x": 200, "y": 150 },
    { "id": "N2", "x": 400, "y": 150 },
    { "id": "GND", "x": 300, "y": 300 }
  ],
  "components": [
    {
      "id": "R1",
      "type": "resistor",
      "x": 300,
      "y": 150,
      "rotation": 0,
      "node_a": "N1",
      "node_b": "N2",
      "params": { "resistance": 1000.0 }
    }
  ]
}
```

**Règles :**
- Les nœuds GND multiples ont des IDs `GND`, `GND_1`, `GND_2`… mais tous correspondent à la masse
- Les anciens fichiers sans positions sont chargés avec les composants disposés automatiquement en grille
- `rotation` vaut 0, 90, 180 ou 270

---

## Modèle de données (`circuit_model.py`)

```python
@dataclass
class Pin:
    name: str       # "node_a", "node_pos", "node_base"…
    label: str      # "+", "−", "A", "K" (affiché sur le canvas)
    offset: tuple   # (dx, dy) relatif au centre, avant rotation

@dataclass
class ComponentData:
    id: str             # "R1", "C1"…
    type: str           # "resistor", "capacitor"…
    x: float            # position centre sur le canvas
    y: float
    rotation: int       # 0, 90, 180, 270
    params: dict        # {"resistance": 1000.0}
    pin_connections: dict  # {"node_a": "N1", "node_b": "GND"}

@dataclass
class NodeData:
    id: str       # "N1", "GND"…
    x: float
    y: float
    is_gnd: bool  # True si nœud de masse

class CircuitModel:
    name: str
    dt: float
    components: list[ComponentData]
    nodes: list[NodeData]
    # méthodes : add_component, remove_component, add_node, remove_node,
    #            connect_pin, disconnect_pin, next_id(type)
```

Les liaisons patte→nœud sont stockées dans `pin_connections` de chaque `ComponentData` — pas de structure séparée. Cela mappe directement sur le format JSON existant.

---

## Vue 2D et interactions (`editor_canvas.py`)

### Tags Tkinter

Chaque entité visuelle est identifiée par des tags uniques :
- `comp_{id}` — tous les items canvas d'un composant (carré + texte + pattes)
- `node_{id}` — le cercle d'un nœud
- `wire_{comp_id}_{pin_name}` — la ligne reliant une patte à son nœud

### Machine à états (4 états)

```
IDLE
 ├─ clic sur composant          → SELECTED (composant sélectionné)
 ├─ clic sur nœud               → SELECTED (nœud sélectionné)
 ├─ clic sur liaison            → SELECTED (liaison sélectionnée)
 ├─ double-clic canvas vide     → crée un nœud → IDLE
 └─ bouton pressé sur patte     → CONNECTING

SELECTED
 ├─ début drag sur composant    → DRAGGING
 ├─ début drag sur nœud        → DRAGGING
 ├─ touche Suppr                → supprime l'entité → IDLE
 └─ clic ailleurs               → IDLE

DRAGGING
 └─ relâche bouton              → IDLE (modèle mis à jour)

CONNECTING
 ├─ relâche sur un nœud         → crée liaison patte→nœud → IDLE
 └─ relâche ailleurs            → annule → IDLE
```

### Rendu des composants

- Carré 100×100 px, fond gris clair (#e8e8e8), bordure gris foncé
- Texte centré : type du composant (`resistor`, `capacitor`…)
- Pattes : cercles de 8 px de diamètre sur la bordure
  - Rouge (#ff4444) : patte non connectée
  - Vert (#44bb44) : patte connectée à un nœud
- Nœuds : cercles de 12 px, fond bleu clair (#aad4ff), bordure bleue
- Nœuds GND : cercles de 12 px, fond noir, label "GND"
- Liaisons : lignes droites noires de 2 px entre patte et nœud
- Entité sélectionnée : bordure orange (#ff8800) de 3 px

### Drag depuis le panneau gauche

Le drag traverse deux widgets Tkinter (Listbox → Canvas). La technique : au `<ButtonPress-1>` sur la Listbox, on enregistre le type sélectionné et on bind `<B1-Motion>` + `<ButtonRelease-1>` sur la fenêtre racine (`root`) pour suivre le curseur globalement. Un rectangle fantôme semi-transparent est dessiné sur le canvas pendant le survol. Au `<ButtonRelease-1>`, si le curseur est sur le canvas, un `ComponentData` est créé ; sinon le drag est annulé.

Au relâchement sur le canvas, un `ComponentData` est créé avec :
- ID auto-incrémenté : `next_id(type)` cherche le prochain entier libre (`R1`, `R2`…)
- Paramètres par défaut issus de `COMPONENT_TEMPLATES`
- Position = point de relâchement

---

## Gabarits de composants (`COMPONENT_TEMPLATES`)

Dictionnaire centralisé dans `editor_canvas.py` définissant pattes et paramètres par défaut :

Chaque patte a aussi un `label` court affiché au survol sur le canvas (`+`, `−`, `A`, `K`, `B`, `C`, `E`, `IN+`, `IN−`, `OUT`).

| Type | Pattes (offset relatif au centre 100×100) | Params par défaut |
|---|---|---|
| `resistor` | `node_a` (−50, 0) gauche, `node_b` (+50, 0) droite | `resistance: 1000.0` |
| `capacitor` | `node_a` (−50, 0), `node_b` (+50, 0) | `capacitance: 1e-6` |
| `inductor` | `node_a` (−50, 0), `node_b` (+50, 0) | `inductance: 0.01` |
| `switch` | `node_a` (−50, 0), `node_b` (+50, 0) | `closed: false` |
| `voltage_source` | `node_pos` (0, −50) haut, `node_neg` (0, +50) bas | `waveform: dc, amplitude: 5.0` |
| `current_source` | `node_pos` (0, −50) haut, `node_neg` (0, +50) bas | `waveform: dc, amplitude: 0.001` |
| `voltmeter` | `node_a` (−50, 0), `node_b` (+50, 0) | `history_size: 500` |
| `ammeter` | `node_a` (−50, 0), `node_b` (+50, 0) | `history_size: 500` |
| `transistor_bjt` | `node_base` (−50, 0), `node_collector` (0, −50), `node_emitter` (0, +50) | `beta: 100, vce_sat: 0.2` |
| `opamp` | `node_plus` (−50, −25), `node_minus` (−50, +25), `node_out` (+50, 0) | _(aucun)_ |
| `diode` | `node_a` (−50, 0) anode, `node_k` (+50, 0) cathode | `is: 1e-12, n: 1.0` |

La rotation applique une transformation matricielle 2D : `(x', y') = (x·cos θ − y·sin θ, x·sin θ + y·cos θ)`.

---

## Panneau gauche (`component_panel.py`)

`Listbox` Tkinter listant tous les types disponibles dans l'ordre ci-dessus, avec `GND` séparé par un séparateur visuel en bas. Le drag est initié avec `<ButtonPress-1>` sur un item de la liste, et terminé par `<ButtonRelease-1>` sur le canvas.

---

## Panneau droit (`properties_panel.py`)

### Composant sélectionné

- **ID** — `Entry` éditable, validé à la perte de focus ; refusé si ID déjà utilisé (message inline en rouge)
- **Type** — `Label` non éditable
- **Rotation** — bouton « ↻ Tourner 90° » qui incrémente la rotation de 90° et redessine
- **Params** — un `Entry` par paramètre du gabarit, avec nom et unité en label
- **Pattes connectées** — liste en lecture seule : `node_a → N1`, `node_b → N2`…

### Nœud sélectionné

- **ID** — `Entry` éditable (avec propagation dans tous les `pin_connections` qui le référencent)
- **Coordonnées** — `x` et `y` en lecture seule

### Rien de sélectionné

Panneau vide avec texte d'invite « Sélectionnez un composant ou un nœud ».

---

## Barre d'outils (`toolbar.py`)

Boutons carrés (48×48 px) avec icône Unicode et tooltip affiché au survol (label flottant) :

| Bouton | Icône | Raccourci | Action |
|--------|-------|-----------|--------|
| Nouveau | 📄 | Ctrl+N | Réinitialise (confirmation si non sauvegardé) |
| Ouvrir | 📂 | Ctrl+O | `filedialog.askopenfilename` → charge JSON |
| Enregistrer | 💾 | Ctrl+S | Sauvegarde dans le fichier courant |
| Enregistrer sous | 💾+ | Ctrl+Shift+S | `filedialog.asksaveasfilename` |

Le titre de la fenêtre affiche `* Nom du circuit` si des modifications non sauvegardées sont présentes.

---

## Lecture/écriture JSON (`io.py`)

### Chargement

1. Lire et parser le JSON
2. Si `"nodes"` absent → disposer les composants en grille (5 par ligne, espacement 150 px), créer les nœuds à des positions par défaut
3. Si `"x"`/`"y"` absents d'un composant → position grille
4. Construire les `ComponentData` et `NodeData` et les injecter dans un `CircuitModel`

### Sauvegarde

1. Sérialiser tous les `ComponentData` (avec `x`, `y`, `rotation`)
2. Sérialiser tous les `NodeData` dans `"nodes"`
3. Écrire avec `json.dump` et indentation 2

---

## Gestion des erreurs et cas limites

- **Suppression d'un nœud connecté** : boîte de confirmation, les liaisons vers ce nœud sont supprimées si confirmé
- **ID dupliqué** : édition refusée, message inline en rouge sous le champ
- **JSON invalide à l'ouverture** : `messagebox.showerror` avec le message d'exception
- **Circuit non sauvegardé** : confirmation avant Nouveau, Ouvrir et fermeture de la fenêtre

---

## Ce qui est hors périmètre

- Zoom et pan du canvas
- Undo/redo
- Affichage d'icônes SVG réelles pour les composants (texte uniquement pour l'instant)
- Validation électrique (nœuds flottants, court-circuits)
- Lancement du simulateur depuis l'éditeur
