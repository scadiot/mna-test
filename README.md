# Simulateur de circuit électrique — MNA

Simulateur pédagogique de circuits électroniques en analyse temporelle. Les circuits sont décrits dans des fichiers JSON et simulés en temps réel via la méthode **Modified Nodal Analysis (MNA)** avec intégration par Euler implicite.

- Thread simulateur : ~1 000 Hz
- Thread interface : ~5 Hz (Tkinter)
- Composants : R, L, C, interrupteur, source de tension/courant, BJT, ampli-op, voltmètre, ampèremètre

---

## Installation

**Prérequis :** Python 3.10+

```bash
pip install -r requirements.txt
```

**Dépendances :** `numpy`, `matplotlib` (Tkinter est inclus avec Python)

---

## Lancement

```bash
python main.py
```

---

## Utilisation

1. Cliquer sur **"Ouvrir circuit..."** et choisir un fichier `.json` (dossier `circuits/`)
2. Cliquer sur **"▶ Démarrer"** pour lancer la simulation
3. Cliquer sur un composant dans la liste pour voir ses paramètres et son état en temps réel
4. Les voltmètres et ampèremètres affichent un graphique d'historique
5. Un interrupteur (`switch`) affiche un bouton **Toggle** pour l'ouvrir/fermer pendant la simulation
6. Cliquer sur **"⏹ Arrêter"** pour stopper

---

## Circuits d'exemple

### `circuits/rc_filter.json` — Filtre RC passe-bas

Filtre RC de fréquence de coupure **fc = 100 Hz** alimenté par une source sinusoïdale 5 V.

```
V1 (sinus 100 Hz, 5V) → N1 → R1 (1 kΩ) → N2 → C1 (1,59 µF) → GND
                                                  VM_in (N1)   VM_out (N2)
```

**Ce qu'on observe :** cliquer sur `VM_out` — le signal est atténué par rapport à `VM_in`. À 100 Hz (fréquence de coupure), l'amplitude est réduite de moitié (−3 dB).

---

### `circuits/rl_transient.json` — Réponse RL à l'échelon

Source DC 12 V avec interrupteur SW1 (ouvert par défaut). Constante de temps **τ = L/R = 0,1 ms**.

```
V1 (DC 12V) → N1 → SW1 (interrupteur) → N2 → R1 (100 Ω) → N3 → L1 (10 mH) → GND
                                                                   VM1 (N3)
```

**Ce qu'on observe :** démarrer la simulation → cliquer sur `SW1` → bouton Toggle → basculer. La tension sur `VM1` monte exponentiellement vers 12 V avec τ ≈ 0,1 ms.

---

### `circuits/transistor_switch.json` — Commutation BJT NPN

Transistor NPN (β = 100) piloté par un signal créneau 10 Hz sur la base.

```
V_base (carré 10 Hz, 5V) → R_base (10 kΩ) → N_base → Q1 (BJT NPN) → GND
V_cc (DC 12V) → R_collector (1 kΩ) → N_collector → Q1 collecteur
                                       VM_col (N_collector)
```

**Ce qu'on observe :** cliquer sur `VM_col` — le signal collecteur est l'inverse du signal base : 12 V quand la base est basse (transistor bloqué), 0,2 V quand la base est haute (transistor saturé).

---

## Format des fichiers JSON

```json
{
  "name": "Nom du circuit",
  "dt": 1e-5,
  "components": [
    {
      "id": "V1",
      "type": "voltage_source",
      "node_pos": "N1",
      "node_neg": "GND",
      "params": { "waveform": "sine", "amplitude": 5.0, "frequency": 100.0 }
    },
    {
      "id": "R1",
      "type": "resistor",
      "node_a": "N1",
      "node_b": "N2",
      "params": { "resistance": 1000.0 }
    }
  ]
}
```

**Règles :**
- `"GND"` est toujours la masse (tension = 0 V imposée)
- Les nœuds sont des chaînes libres (`"N1"`, `"N_base"`, etc.)
- `dt` est le pas de temps en secondes (`1e-5` = 10 µs)
- Chaque composant a un `id` unique

### Types de composants

| Type JSON        | Paramètres requis                                      | Nœuds                              |
|------------------|--------------------------------------------------------|------------------------------------|
| `resistor`       | `resistance` (Ω)                                       | `node_a`, `node_b`                 |
| `capacitor`      | `capacitance` (F)                                      | `node_a`, `node_b`                 |
| `inductor`       | `inductance` (H)                                       | `node_a`, `node_b`                 |
| `switch`         | `closed` (true/false)                                  | `node_a`, `node_b`                 |
| `voltage_source` | `waveform`, + params de la forme d'onde                | `node_pos`, `node_neg`             |
| `current_source` | `waveform`, + params de la forme d'onde                | `node_a`, `node_b`                 |
| `transistor_bjt` | `beta`, `vce_sat`, `vbe_threshold`                     | `node_base`, `node_collector`, `node_emitter` |
| `opamp`          | _(aucun)_                                              | `node_plus`, `node_minus`, `node_out` |
| `voltmeter`      | `history_size` (nombre de points, ex. 500)             | `node_a`, `node_b`                 |
| `ammeter`        | `history_size`                                         | `node_a`, `node_b`                 |

> L'ampèremètre doit être placé **en série** : couper le fil entre deux nœuds et insérer l'ampèremètre entre eux.

### Formes d'onde disponibles (`waveform`)

| Valeur    | Description         | Paramètres supplémentaires                        |
|-----------|---------------------|---------------------------------------------------|
| `"dc"`    | Tension constante   | `amplitude`                                       |
| `"sine"`  | Sinusoïde           | `amplitude`, `frequency`, `phase` _(optionnel)_   |
| `"pulse"` | Impulsion unique    | `amplitude`, `t_start`, `t_end`                   |
| `"square"`| Signal créneau      | `amplitude`, `frequency`, `duty_cycle` _(optionnel, défaut 0.5)_ |

---

## Structure du projet

```
mna-test/
├── main.py                   ← point d'entrée
├── shared_state.py           ← données partagées thread-safe (Lock)
├── circuit_loader.py         ← lecture et validation du JSON
├── requirements.txt
├── simulator/
│   ├── engine.py             ← boucle MNA ~1000 Hz
│   ├── components.py         ← R, L, C, Switch, BJT, OpAmp, Voltmeter, Ammeter
│   └── sources.py            ← DC, Sine, Pulse, Square
├── ui/
│   ├── app.py                ← fenêtre principale Tkinter
│   ├── component_list.py     ← liste des composants cliquable
│   └── detail_panel.py       ← panneau détail + graphique matplotlib
├── circuits/
│   ├── rc_filter.json
│   ├── rl_transient.json
│   └── transistor_switch.json
└── tests/
    ├── test_shared_state.py
    ├── test_sources.py
    ├── test_components.py
    └── test_engine.py
```

---

## Tests

```bash
pytest tests/ -v
```

44 tests couvrent les composants, le moteur MNA et le SharedState.

---

## Principe de fonctionnement (résumé)

À chaque pas de temps `dt`, le simulateur résout le système linéaire **G·x = b** :

- **G** : matrice des conductances (construite depuis les composants)
- **x** : vecteur des inconnues (tensions aux nœuds + courants dans les sources)
- **b** : vecteur des termes sources

Les condensateurs et bobines sont remplacés à chaque pas par des **modèles compagnons** (Euler implicite), une technique standard utilisée par SPICE.

Le résultat est écrit dans un `SharedState` protégé par un `threading.Lock`, que l'interface Tkinter lit toutes les 200 ms.
