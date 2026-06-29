# « Du courant à la matrice » — Comprendre un simulateur de circuits par la pratique

Un livre qui explique, à un lecteur connaissant Python mais néophyte en électronique,
comment fonctionne le simulateur de ce dépôt (`simulator/`).

**Approche :** *physique d'abord* — on comprend d'abord la loi physique, puis on
découvre sa traduction dans le code. Chaque composant suit le même triptyque :
**physique → équation → code (`stamp` / `get_state`)**.

**Hors périmètre :** interface graphique et éditeur. On suppose le lecteur à l'aise
avec la programmation et le langage Python.

---

## Plan

### Préface
- À qui s'adresse ce livre — La promesse — La philosophie : *un simulateur ne « comprend »
  pas l'électronique, il résout un système d'équations*.

### Partie I — Les fondamentaux de l'électricité
- **Ch. 1** — Les grandeurs de base (tension, courant, masse comme référence 0 V) ✅ [rédigé](ch01-grandeurs.md)
- **Ch. 2** — Les lois de Kirchhoff (nœuds / mailles) ✅ [rédigé](ch02-kirchhoff.md)
- **Ch. 3** — La loi d'Ohm et la conductance (`I = G·U`) ✅ [rédigé](ch03-ohm-conductance.md)

### Partie II — Du circuit au système d'équations
- **Ch. 4** — Modéliser un circuit comme un graphe (`node_map`, exclusion de GND) ✅ [rédigé](ch04-graphe.md)
- **Ch. 5** — L'analyse nodale (`G·x = b`) ✅ [rédigé](ch05-analyse-nodale.md)
- **Ch. 6** — Le « stamping » : assembler la matrice composant par composant ✅ [rédigé](ch06-stamping.md)
- **Ch. 7** — Quand la nodale ne suffit pas : la MNA (sources de tension, `branch_map`) ✅ [rédigé](ch07-mna.md)
- **Ch. 8** — Résoudre le système (`numpy.linalg.solve`, matrice singulière) ✅ [rédigé](ch08-resolution.md)

### Partie III — Le catalogue des composants
- **Ch. 9** — La résistance (`Resistor`) ✅ [rédigé](ch09-resistance.md)
- **Ch. 10** — Les sources : DC, sinus, impulsion, créneau (`sources.py`) ✅ [rédigé](ch10-sources-formes.md)
- **Ch. 11** — Sources de tension vs sources de courant (`VoltageSource`, `CurrentSource`) ✅ [rédigé](ch11-tension-vs-courant.md)
- **Ch. 12** — Les instruments (`Voltmeter`, `Ammeter`, historique) ✅ [rédigé](ch12-instruments.md)
- **Ch. 13** — L'interrupteur (`Switch`) ✅ [rédigé](ch13-interrupteur.md)

### Partie IV — Le temps : composants réactifs
- **Ch. 14** — Pourquoi le temps change tout (`i = C·dv/dt`, `v = L·di/dt`) ✅ [rédigé](ch14-temps.md)
- **Ch. 15** — La discrétisation du temps (pas `dt`, Euler implicite) ✅ [rédigé](ch15-discretisation.md)
- **Ch. 16** — Les modèles compagnons (`Capacitor`, `Inductor`, `prev_state`) ✅ [rédigé](ch16-modeles-compagnons.md)

### Partie V — Les composants non-linéaires
- **Ch. 17** — Le défi de la non-linéarité (linéarisation par morceaux) ✅ [rédigé](ch17-non-linearite.md)
- **Ch. 18** — La diode (`Diode`, offset de courant) ✅ [rédigé](ch18-diode.md)
- **Ch. 19** — Le transistor bipolaire NPN (`BJT`, 3 régimes) ✅ [rédigé](ch19-transistor.md)
- **Ch. 20** — L'amplificateur opérationnel idéal (`OpAmp`) ✅ [rédigé](ch20-ampli-op.md)

### Partie VI — L'architecture du moteur
- **Ch. 21** — La boucle de simulation (`_step`, synchro temps réel, thread) ✅ [rédigé](ch21-boucle-simulation.md)
- **Ch. 22** — Du fichier au circuit (`circuit_loader`, JSON) ✅ [rédigé](ch22-chargement.md)
- **Ch. 23** — Concurrence et état partagé (`shared_state`, verrou) ✅ [rédigé](ch23-concurrence.md)
- **Ch. 24** — Limites et extensions (ajouter son propre composant) ✅ [rédigé](ch24-limites-extensions.md)

### Annexes ✅ [rédigées](annexes.md)
- **A.** Rappel d'algèbre linéaire
- **B.** Aide-mémoire des unités et préfixes
- **C.** Toutes les formules de « stamping » sur une page
- **D.** Glossaire

---

## État de rédaction

**Livre complet : 24 chapitres + 4 annexes rédigés. ✅**

| Chapitre | Statut |
|----------|--------|
| Ch. 1 — Les grandeurs de base | ✅ rédigé |
| Ch. 2 — Les lois de Kirchhoff | ✅ rédigé |
| Ch. 3 — La loi d'Ohm et la conductance | ✅ rédigé |
| Ch. 4 — Modéliser un circuit comme un graphe | ✅ rédigé |
| Ch. 5 — L'analyse nodale | ✅ rédigé |
| Ch. 6 — Le stamping | ✅ rédigé (chapitre témoin) |
| Ch. 7 — La MNA | ✅ rédigé |
| Ch. 8 — Résoudre le système | ✅ rédigé |
| Ch. 9 — La résistance | ✅ rédigé |
| Ch. 10 — Les sources et formes d'onde | ✅ rédigé |
| Ch. 11 — Tension vs courant | ✅ rédigé |
| Ch. 12 — Les instruments | ✅ rédigé |
| Ch. 13 — L'interrupteur | ✅ rédigé |
| Ch. 14 — Pourquoi le temps change tout | ✅ rédigé |
| Ch. 15 — La discrétisation du temps | ✅ rédigé |
| Ch. 16 — Les modèles compagnons | ✅ rédigé |
| Ch. 17 — Le défi de la non-linéarité | ✅ rédigé |
| Ch. 18 — La diode | ✅ rédigé |
| Ch. 19 — Le transistor bipolaire NPN | ✅ rédigé |
| Ch. 20 — L'amplificateur opérationnel idéal | ✅ rédigé |
| Ch. 21 — La boucle de simulation | ✅ rédigé |
| Ch. 22 — Du fichier au circuit | ✅ rédigé |
| Ch. 23 — Concurrence et état partagé | ✅ rédigé |
| Ch. 24 — Limites et extensions | ✅ rédigé |
| Annexes A–D | ✅ rédigées |
