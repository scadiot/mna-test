# Simulateur de circuit électrique — Spécification de design
Date : 2026-06-28

## Objectif

Projet Python pédagogique minimaliste simulant des circuits électroniques en analyse temporelle (transitoire). Le code est simple et très commenté en français. Les nommages (fonctions, classes, variables) sont en anglais.

L'utilisateur charge un fichier JSON décrivant un circuit, lance la simulation, et observe en temps réel les tensions, courants et historiques de chaque composant via une interface Tkinter.

---

## Architecture globale

Deux boucles indépendantes tournent en parallèle via `threading.Thread` :

- **Thread simulateur** : tourne à ~1000 Hz, résout la MNA à chaque pas de temps, écrit les résultats dans un `SharedState`
- **Thread principal Tkinter** : tourne à 5 Hz via `after(200)`, lit le `SharedState` et rafraîchit l'UI

Le `SharedState` est un objet Python partagé contenant :
- les tensions à chaque nœud du circuit
- les courants dans chaque composant
- les historiques (deque de N points) des appareils de mesure
- un flag `running` pour démarrer/arrêter proprement la simulation

La synchronisation entre les deux threads se fait via un unique `threading.Lock`, acquis brièvement lors de chaque écriture (simulateur) et lecture (UI).

```
┌─────────────────────────────────────────────────────────┐
│  Thread simulateur (1000 Hz)                            │
│  engine.py : lit le circuit, résout MNA, écrit état     │
└────────────────────┬────────────────────────────────────┘
                     │ SharedState (dict + Lock)
┌────────────────────▼────────────────────────────────────┐
│  Thread principal Tkinter (5 Hz via after(200))         │
│  app.py : liste composants, panneau détail, historique  │
└─────────────────────────────────────────────────────────┘
```

---

## Moteur mathématique — Modified Nodal Analysis (MNA)

### Principe

À chaque pas de temps `dt`, le simulateur résout le système linéaire :

```
G · x = b
```

où :
- `x` = vecteur des inconnues : tensions aux nœuds + courants dans les sources de tension
- `G` = matrice des conductances et contraintes (construite depuis les composants)
- `b` = vecteur des termes sources (tensions et courants imposés)

Le nœud `GND` est le nœud de référence (tension = 0V). Le moteur attribue automatiquement un indice numérique à chaque nœud nommé dans le JSON.

La résolution est faite avec `numpy.linalg.solve(G, b)`.

### Traitement des composants réactifs (Euler implicite)

Les condensateurs et bobines sont remplacés à chaque pas par des **modèles compagnons** (résistance + source), une technique standard de SPICE :

**Condensateur C :**
```
i(t) = C · dv/dt  →  G_eq = C/dt  (conductance compagnon)
                      I_eq = -G_eq · v(t-1)  (source compagnon)
```

**Bobine L :**
```
v(t) = L · di/dt  →  R_eq = dt/L  (résistance compagnon, en série)
                      V_eq = i(t-1) · L/dt  (source compagnon)
```

### Boucle du simulateur

```
pour chaque pas de temps:
    1. calculer la valeur de chaque source selon t (DC / sinus / impulsion / créneau)
    2. mettre à jour les modèles compagnons de L et C
    3. construire G et b depuis les composants
    4. résoudre x = numpy.linalg.solve(G, b)
    5. extraire tensions et courants
    6. acquérir le Lock, écrire dans SharedState, libérer le Lock
    7. attendre jusqu'au prochain tick : sleep(dt)
```

---

## Modèles des composants

Chaque composant est une classe Python héritant d'une classe de base `Component` avec deux méthodes :

```python
class Component:
    def stamp(self, G, b, state):
        # Ajoute la contribution du composant à la matrice MNA
        ...
    def get_state(self, x):
        # Extrait tension aux bornes et courant traversant depuis le vecteur solution
        ...
```

### Table des modèles

| Composant | Type JSON | Modèle MNA |
|---|---|---|
| Résistance | `resistor` | Conductance `1/R` entre deux nœuds |
| Condensateur | `capacitor` | Conductance `C/dt` + source de courant (Euler implicite) |
| Bobine | `inductor` | Source de tension `L·i(t-1)/dt` + résistance série `L/dt` |
| Interrupteur | `switch` | Résistance `1e9 Ω` (ouvert) ou `1e-6 Ω` (fermé) |
| Source de tension | `voltage_source` | Ligne supplémentaire imposant `V_nœud = f(t)` |
| Source de courant | `current_source` | Injection directe dans `b` |
| Transistor BJT idéal | `transistor_bjt` | Bloqué : résistance infinie / Saturé : source `Vce_sat` / Actif : source de courant `β·Ib` |
| Ampli-op idéal | `opamp` | Contrainte `V+ = V−` + sortie comme source de tension commandée |
| Voltmètre | `voltmeter` | Résistance `1e9 Ω` (invisible pour le circuit) |
| Ampèremètre | `ammeter` | Source de tension 0V (mesure le courant par la ligne MNA) |

### Sources — formes d'onde disponibles

| Waveform | Description | Paramètres |
|---|---|---|
| `dc` | Tension/courant constant | `amplitude` |
| `sine` | Sinusoïde | `amplitude`, `frequency`, `phase` (optionnel) |
| `pulse` | Impulsion unique | `amplitude`, `t_start`, `t_end` |
| `square` | Signal créneau | `amplitude`, `frequency`, `duty_cycle` (optionnel, défaut 0.5) |

---

## Format JSON des circuits

```json
{
  "name": "Filtre RC passe-bas",
  "dt": 1e-5,
  "components": [
    {
      "id": "V1",
      "type": "voltage_source",
      "node_pos": "N1",
      "node_neg": "GND",
      "params": {
        "waveform": "sine",
        "amplitude": 5.0,
        "frequency": 100.0
      }
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
      "params": { "capacitance": 1e-6 }
    },
    {
      "id": "VM1",
      "type": "voltmeter",
      "node_a": "N2",
      "node_b": "GND",
      "params": { "history_size": 500 }
    }
  ]
}
```

**Règles du format :**
- `"GND"` est toujours la masse (tension = 0V, imposée par la MNA)
- Les nœuds sont des chaînes de caractères libres — le moteur leur attribue un indice automatiquement
- `dt` est le pas de temps en secondes (ex: `1e-5` = 10 µs)
- L'interrupteur accepte un paramètre `"closed": true/false`, modifiable pendant la simulation
- Le transistor BJT utilise les clés `"node_base"`, `"node_collector"`, `"node_emitter"` et accepte `"beta"` et `"vce_sat"` dans `params`
- L'ampli-op utilise les clés `"node_plus"`, `"node_minus"`, `"node_out"` (3 terminaux, la masse est implicitement GND pour les rails d'alimentation)
- L'ampèremètre doit être placé **en série** dans le circuit : il faut couper le fil entre deux nœuds et insérer l'ampèremètre entre eux (ex: `node_a: "N1"`, `node_b: "N1b"`, avec R1 connecté sur `"N1b"`)

---

## Interface utilisateur (Tkinter)

### Disposition

```
┌──────────────────────────────────────────────────────────┐
│  [Ouvrir circuit...]   circuits/rc_filter.json   [▶ Run] │
├──────────────────────┬───────────────────────────────────┤
│  Liste composants    │  Détail du composant sélectionné  │
│                      │                                   │
│  ▶ V1  voltage_src   │  ID : C1  (capacitor)            │
│    R1  resistor      │  Capacitance : 1.0e-6 F           │
│    C1  capacitor  ◀  │  Tension aux bornes : 2.31 V      │
│    VM1 voltmeter     │  Courant : 0.000231 A             │
│                      │  ┌───────────────────────────┐   │
│                      │  │  Historique (matplotlib)  │   │
│                      │  │                           │   │
│                      │  └───────────────────────────┘   │
└──────────────────────┴───────────────────────────────────┘
```

### Comportement

- **Barre supérieure** : bouton d'ouverture de fichier JSON (`filedialog`), nom du circuit chargé, bouton Run/Stop
- **Liste composants** : affiche `id` et `type` de chaque composant, cliquable
- **Panneau détail** : affiche les paramètres statiques (valeurs du JSON) + l'état dynamique (tension, courant) lu dans le `SharedState`. Se rafraîchit à 5 Hz.
- **Graphique historique** : affiché uniquement pour les voltmètres et ampèremètres. Courbe matplotlib embarquée (`FigureCanvasTkAgg`), mise à jour à 5 Hz.
- Un interrupteur dans la liste affiche un bouton toggle pour ouvrir/fermer le circuit en temps réel.

---

## Structure des fichiers du projet

```
mna-test/
├── main.py                        ← point d'entrée : crée et lance l'UI
├── shared_state.py                ← SharedState : données partagées + Lock
├── circuit_loader.py              ← lecture, parsing et validation du JSON
├── simulator/
│   ├── __init__.py
│   ├── engine.py                  ← boucle 1000 Hz, résolution MNA
│   ├── components.py              ← classes R, L, C, Switch, BJT, OpAmp, Voltmeter, Ammeter
│   └── sources.py                 ← DC, sine, pulse, square
├── ui/
│   ├── __init__.py
│   ├── app.py                     ← fenêtre principale Tkinter
│   ├── component_list.py          ← widget liste cliquable
│   └── detail_panel.py            ← widget paramètres + graphique matplotlib
└── circuits/
    ├── rc_filter.json             ← filtre RC passe-bas (source sinus)
    ├── rl_transient.json          ← transitoire RL (source DC + interrupteur)
    └── transistor_switch.json     ← transistor BJT en commutation (source créneau)
```

**Dépendances Python :**
- `numpy` — résolution du système linéaire MNA
- `matplotlib` — graphique historique embarqué dans Tkinter
- `tkinter` — natif Python, aucune installation requise

---

## Gestion des erreurs

- **JSON invalide** : l'UI affiche un message d'erreur dans la barre supérieure, la simulation ne démarre pas
- **Nœud GND absent** : erreur détectée au chargement, message explicite à l'utilisateur
- **Matrice MNA singulière** (circuit mal formé, ex: nœud flottant) : le thread simulateur attrape l'exception `numpy.linalg.LinAlgError`, passe `running = False` et écrit un message d'erreur dans le `SharedState`; l'UI l'affiche au prochain rafraîchissement
- **Composant de type inconnu** : erreur au chargement avec le nom du type non reconnu

---

## Ce qui est hors périmètre (pour rester minimaliste)

- Pas d'éditeur graphique de circuit (le circuit est défini dans le JSON)
- Pas d'analyse fréquentielle (Bode) ni AC complexe — uniquement temporel
- Pas de sauvegarde de l'état de simulation
- Pas de modèles MOSFET ni de composants numériques complexes
- Pas d'interface pour modifier les paramètres de composants depuis l'UI (sauf l'interrupteur)
