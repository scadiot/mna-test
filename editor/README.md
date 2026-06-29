# Éditeur de circuit électronique

Application Python/Tkinter pour créer et éditer visuellement les fichiers JSON de circuits du répertoire `circuits/`.

## Lancement

```bash
python -m editor.main
```

## Interface

```
┌──────────────────────────────────────────────────────────────┐
│  📄 Nouveau   📂 Ouvrir   💾 Enregistrer   💾+ Enr. sous     │
├────────────────┬─────────────────────────┬───────────────────┤
│  Composants    │                         │  Propriétés       │
│                │      Vue 2D             │                   │
│  resistor      │      (canvas)           │  ID, type,        │
│  capacitor     │                         │  rotation,        │
│  ...           │                         │  paramètres,      │
│  ─────         │                         │  connexions       │
│  GND           │                         │                   │
└────────────────┴─────────────────────────┴───────────────────┘
```

## Utilisation

### Ajouter un composant
Glisser-déposer un type depuis le panneau gauche vers le canvas.

### Ajouter un nœud
Double-cliquer sur une zone vide du canvas.

### Ajouter un nœud GND
Glisser `GND` depuis le panneau gauche vers le canvas.

### Relier une patte à un nœud
Presser le bouton gauche sur une patte (cercle rouge), maintenir et relâcher sur un nœud.

### Déplacer un élément
Cliquer pour sélectionner, puis glisser.

### Tourner un composant
Sélectionner le composant → bouton « ↻ Tourner 90° » dans le panneau droit.

### Supprimer
Sélectionner un composant, nœud ou liaison → touche `Suppr`.

### Éditer les propriétés
Sélectionner un composant → modifier l'ID, les paramètres ou la rotation dans le panneau droit.

## Format JSON produit

L'éditeur génère un format étendu compatible avec le simulateur existant :

```json
{
  "name": "Mon circuit",
  "dt": 1e-5,
  "nodes": [
    { "id": "N1", "x": 200, "y": 150 },
    { "id": "GND", "x": 300, "y": 300 }
  ],
  "components": [
    {
      "id": "R1",
      "type": "resistor",
      "x": 250, "y": 150,
      "rotation": 0,
      "node_a": "N1",
      "node_b": "GND",
      "params": { "resistance": 1000.0 }
    }
  ]
}
```

Les champs `x`, `y`, `rotation` et la clé `nodes` sont ignorés par le simulateur — la compatibilité est préservée.

## Composants disponibles

| Type | Pattes | Paramètres |
|------|--------|------------|
| `resistor` | node_a, node_b | resistance (Ω) |
| `capacitor` | node_a, node_b | capacitance (F) |
| `inductor` | node_a, node_b | inductance (H) |
| `switch` | node_a, node_b | closed (bool) |
| `voltage_source` | node_pos, node_neg | waveform, amplitude |
| `current_source` | node_a, node_b | waveform, amplitude |
| `voltmeter` | node_a, node_b | history_size |
| `ammeter` | node_a, node_b | history_size |
| `transistor_bjt` | node_base, node_collector, node_emitter | beta, vce_sat |
| `opamp` | node_plus, node_minus, node_out | — |
| `diode` | node_anode, node_cathode | vf (V) |

## Structure du module

```
editor/
├── main.py              # Point d'entrée, fenêtre principale
├── circuit_model.py     # Dataclasses CircuitModel, ComponentData, NodeData
├── editor_canvas.py     # Canvas 2D, COMPONENT_TEMPLATES, machine à états
├── component_panel.py   # Panneau gauche avec drag-and-drop
├── properties_panel.py  # Panneau droit, édition des propriétés
├── toolbar.py           # Barre d'outils 4 boutons
└── io.py                # Lecture/écriture JSON
```
