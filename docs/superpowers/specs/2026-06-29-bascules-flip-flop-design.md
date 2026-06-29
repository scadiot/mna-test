# Bascules (flip-flops) — circuits JSON

Date : 2026-06-29
Statut : design validé

## Objectif

Ajouter trois nouveaux circuits JSON de type *bascule* (flip-flop) dans
`circuits/`, exploitables par le simulateur existant et visualisables dans
l'éditeur (`python -m editor.main`).

## Contraintes du moteur (établies par lecture du code)

- Le moteur résout par **MNA + modèles compagnons** (`simulator/components.py`).
  Les composants non-linéaires (`BJT`, `Diode`) décident de leur état d'après
  l'**état du pas précédent** (`prev_state`), avec un retard d'un pas. C'est ce
  retard qui permet à une **rétroaction croisée** (cœur d'une bascule) de se
  stabiliser ou d'osciller d'un pas à l'autre.
- L'**AOp est idéal avec contrainte `V+ = V-`** (`OpAmp`), donc adapté
  uniquement à la contre-réaction négative. Une bascule à comparateur / Schmitt
  (réaction positive) ne fonctionnerait pas → **toutes les bascules sont à
  transistors NPN** (`transistor_bjt`).
- Types de composants disponibles (`circuit_loader.py`) : `resistor`,
  `capacitor`, `inductor`, `switch`, `voltage_source`, `current_source`,
  `transistor_bjt`, `opamp`, `diode`, `voltmeter`, `ammeter`, `potentiometer`.
- Chaque circuit doit contenir au moins un nœud `GND`.
- Format JSON : `{ "name", "dt", "components": [ { "id", "type", "node_*",
  "params" } ] }`.

## Conventions communes aux trois circuits

- Alimentation `VCC` = 5 V DC (`voltage_source`, waveform `dc`).
- Masse `GND`.
- Transistors `transistor_bjt` : `beta=100`, `vbe_threshold=0.6`,
  `vce_sat=0.2` (mêmes valeurs que `circuits/transistor_switch.json`).
- `dt = 1e-3` s (les bascules sont lentes ; inutile de descendre à la µs).
- Un voltmètre par sortie de collecteur pour visualiser les états.

## Circuit 1 — `flip_flop_astable.json`

Multivibrateur astable (clignotant) : deux transistors croisés Q1/Q2.

- Collecteurs `N_c1`, `N_c2` reliés à VCC par `Rc1`, `Rc2` = 1 kΩ.
- Émetteurs à `GND`.
- Couplage croisé capacitif :
  - `Ccpl1` : `N_c1` → base `N_b2`.
  - `Ccpl2` : `N_c2` → base `N_b1`.
- Polarisation des bases : `Rb1` (VCC → `N_b1`), `Rb2` (VCC → `N_b2`) = 47 kΩ.
- Demi-période ≈ 0,69·Rb·C ≈ 0,32 s → clignotement ≈ 1,5 Hz.
- **Démarrage garanti** par dissymétrie : `Ccpl1 = 10 µF` (1e-5),
  `Ccpl2 = 12 µF` (1.2e-5). Sans dissymétrie, l'équilibre symétrique parfait
  de la simulation pourrait rester figé.
- Voltmètres `VM_C1` (`N_c1`/GND), `VM_C2` (`N_c2`/GND), `history_size = 5000`
  (fenêtre ≈ 5 s, plusieurs cycles).

## Circuit 2 — `flip_flop_bistable_rs.json`

Bascule bistable RS à couplage résistif : deux états stables, mémorisés.

- Collecteurs `N_c1`, `N_c2` reliés à VCC par `Rc1`, `Rc2` = 1 kΩ.
- Émetteurs à `GND`.
- Couplage croisé **résistif** :
  - `Rcpl1` : `N_c1` → base `N_b2` = 10 kΩ.
  - `Rcpl2` : `N_c2` → base `N_b1` = 10 kΩ.
- Bases tirées vers `GND` par `Rb1`, `Rb2` = 47 kΩ (maintien de l'état bas).
- Commande manuelle par interrupteurs (pilotables dans l'UI) :
  - `S_set` : relie VCC à `N_b1` via `R_set` (≈ 4,7 kΩ) → force Q1 ON, Q2 OFF.
  - `S_reset` : relie VCC à `N_b2` via `R_reset` (≈ 4,7 kΩ) → état inverse.
  - Les deux interrupteurs `closed: false` au repos.
- L'état **reste mémorisé** après réouverture de l'interrupteur grâce à la
  rétroaction croisée (gérée par `prev_state`).
- Voltmètres `VM_C1`, `VM_C2`, `history_size = 2000`.

## Circuit 3 — `flip_flop_monostable.json`

Monostable : un seul état stable au repos ; un déclenchement génère une
impulsion calibrée puis retour au repos.

- Collecteurs `N_c1`, `N_c2` reliés à VCC par `Rc1`, `Rc2` = 1 kΩ.
- Émetteurs à `GND`.
- Au repos : Q2 **passant** (base `N_b2` tirée à VCC par `Rb2` = 47 kΩ),
  Q1 **bloqué**.
- Couplage temporisateur : condensateur `Ctmg` (`N_c1` → `N_b2`) fixe la durée
  d'impulsion τ ≈ 0,69·Rb2·Ctmg ≈ 0,3 s (Ctmg ≈ 10 µF).
- Couplage de maintien : `Rcpl` (`N_c2` → `N_b1`) = 47 kΩ pour stabiliser
  l'état de repos.
- Déclenchement : `S_trig` relie VCC à `N_b1` via `R_trig` (≈ 4,7 kΩ).
  `closed: false` au repos ; une fermeture brève déclenche l'impulsion.
- Voltmètres `VM_C1`, `VM_C2`, `history_size = 3000`.

## Validation (étape d'implémentation)

Les comportements dynamiques exacts ne sont pas garantis par construction et
**doivent être vérifiés en exécutant le simulateur** :

- Astable : oscillation effective et symétrie/dissymétrie du rapport cyclique.
- Bistable : verrouillage et mémorisation après réouverture des interrupteurs.
- Monostable : durée d'impulsion et retour à l'état de repos.

Les valeurs (R, C, dissymétrie de démarrage) seront ajustées si la simulation
ne donne pas le comportement attendu. Chaque circuit doit au minimum se charger
sans erreur via `load_circuit`.

## Hors périmètre (YAGNI)

- Pas de bascule à AOp / comparateur (incompatible avec l'AOp idéal).
- Pas d'ampèremètres (non demandés ; les voltmètres suffisent à la lecture).
- Pas de modification du moteur ni de nouveaux types de composants.
