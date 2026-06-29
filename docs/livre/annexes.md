# Annexes

Rappels et aide-mémoire, à consulter au fil de la lecture.

---

## Annexe A — Rappel d'algèbre linéaire

Le minimum nécessaire pour comprendre `G·x = b`.

**Vecteur.** Une liste ordonnée de nombres : `x = (V₁, V₂, …)`. Dans le livre, `x` contient les tensions de nœud et les courants de branche (chapitre 4).

**Matrice.** Un tableau rectangulaire de nombres. `G` est **carrée** (autant de lignes que de colonnes) : sa taille est le nombre d'inconnues (chapitre 8).

**Produit matrice-vecteur.** `G·x` produit un vecteur dont la ligne `i` vaut `Σⱼ G[i,j]·xⱼ`. Chaque ligne est donc une **combinaison linéaire** des inconnues — et, dans notre cas, une équation de la loi des nœuds (chapitre 2).

**Système linéaire.** `G·x = b` est un jeu d'équations à résoudre pour trouver `x`. « Résoudre » = trouver le vecteur `x` qui satisfait toutes les lignes simultanément (chapitre 8).

**Élimination de Gauss.** L'algorithme standard de résolution : combiner les lignes pour éliminer les inconnues une à une. C'est ce que fait `np.linalg.solve` (chapitre 5).

**Matrice singulière.** Une matrice pour laquelle le système n'a pas de solution unique (aucune, ou une infinité). La résolution échoue (`LinAlgError`). Cause physique : nœud flottant ou contraintes contradictoires (chapitre 8).

**Conditionnement.** Mesure de la sensibilité de la solution aux erreurs d'arrondi. Une matrice mêlant des valeurs très grandes et très petites est **mal conditionnée** : la précision en souffre (chapitre 8).

---

## Annexe B — Unités et préfixes

### Grandeurs fondamentales

| Grandeur     | Symbole | Unité    | Symbole unité |
|--------------|:-------:|----------|:-------------:|
| Tension      | `U`, `V`| volt     | V             |
| Courant      | `I`     | ampère   | A             |
| Résistance   | `R`     | ohm      | Ω             |
| Conductance  | `G`     | siemens  | S             |
| Capacité     | `C`     | farad    | F             |
| Inductance   | `L`     | henry    | H             |
| Puissance    | `P`     | watt     | W             |
| Fréquence    | `f`     | hertz    | Hz            |
| Temps        | `t`     | seconde  | s             |
| Charge       | `Q`     | coulomb  | C             |

### Préfixes

| Préfixe | Symbole | Facteur  | | Préfixe | Symbole | Facteur  |
|---------|:-------:|----------|-|---------|:-------:|----------|
| giga    | G       | 10⁹      | | milli   | m       | 10⁻³     |
| méga    | M       | 10⁶      | | micro   | µ       | 10⁻⁶     |
| kilo    | k       | 10³      | | nano    | n       | 10⁻⁹     |
|         |         |          | | pico    | p       | 10⁻¹²    |

### Relations clés

- Loi d'Ohm : `U = R·I` ⇔ `I = G·U`, avec `G = 1/R`
- Puissance : `P = U·I = R·I² = U²/R`
- Condensateur : `Q = C·U` ; `i = C·dv/dt`
- Bobine : `v = L·di/dt`
- Pulsation : `ω = 2πf` ; période : `T = 1/f`

---

## Annexe C — Formulaire de stamping

Le « stamping » de chaque composant, en un coup d'œil. Notations : `g = 1/R` (conductance) ; `g_eq` (conductance compagnon) ; `idx = -1` pour GND (marque ignorée). Les deux primitives :

- `_stamp_conductance(G, a, b, g)` : `G[a,a]+=g`, `G[b,b]+=g`, `G[a,b]-=g`, `G[b,a]-=g`
- `_stamp_current(b, a, b_, i)` : `b[a]+=i`, `b[b_]-=i`

| Composant | Branche ? | Contribution | Référence |
|-----------|:---------:|--------------|:---------:|
| **Résistance** | non | conductance `g = 1/R` | Ch. 9 |
| **Source de courant** | non | courant `I(t)` dans `b` (`_stamp_current`) | Ch. 11 |
| **Condensateur** | non | conductance `g_eq = C/dt` **+** source `g_eq·v_prev` | Ch. 16 |
| **Bobine** | non | conductance `g_eq = dt/L` **+** source `i_prev` | Ch. 16 |
| **Interrupteur** | non | conductance `1/R_CLOSED` (fermé) ou `1/R_OPEN` (ouvert) | Ch. 13 |
| **Voltmètre** | non | conductance `1e-9` (quasi nulle) | Ch. 12 |
| **Diode (passante)** | non | conductance `1/R_ON` **+** source `vf/R_ON` | Ch. 18 |
| **Diode (bloquée)** | non | conductance `1/R_OFF` | Ch. 18 |
| **Transistor (bloqué)** | non | conductance `1e-9` entre C-E | Ch. 19 |
| **Transistor (actif)** | non | source de courant `β·I_B` (C→E) | Ch. 19 |
| **Transistor (saturé)** | non | conductance `1e6` entre C-E | Ch. 19 |
| **Source de tension** | **oui** | ligne `V_pos − V_neg = V(t)` + colonne courant | Ch. 7 |
| **Ampèremètre** | **oui** | ligne `V_a − V_b = 0` + colonne courant | Ch. 12 |
| **Ampli-op** | **oui** | ligne `V_+ − V_− = 0` + courant injecté sur sortie | Ch. 20 |

**Structure d'une branche** (source de tension, ampèremètre, ampli-op) :
- Ligne de branche : `G[br, pos] += 1`, `G[br, neg] -= 1`, `b[br] = valeur`
- Colonne de branche : `G[pos, br] += 1`, `G[neg, br] -= 1` (sortie pour l'ampli-op)

**Décision d'état** (composants non-linéaires) : fondée sur `prev_state` (le pas précédent), pas sur l'instant courant (Ch. 17).

---

## Annexe D — Glossaire

**Ampèremètre** — instrument mesurant le courant ; modélisé par une source de tension de 0 V, branché en série. (Ch. 12)

**Branche** — inconnue de courant ajoutée à la MNA pour les composants imposant une tension. (Ch. 7)

**Conductance** (`G`) — facilité de passage du courant ; inverse de la résistance, `G = 1/R`. (Ch. 3)

**Condition de course** (*race condition*) — bug survenant quand deux threads accèdent aux mêmes données sans synchronisation. (Ch. 23)

**Euler implicite** (*backward Euler*) — méthode d'intégration évaluant la loi à l'instant courant ; inconditionnellement stable. (Ch. 15)

**Différences finies** — approximation d'une dérivée par une différence : `dv/dt ≈ (v(t) − v(t−dt))/dt`. (Ch. 15)

**KCL** (loi des nœuds) — en tout nœud, la somme des courants est nulle. Fondement de la matrice `G`. (Ch. 2)

**KVL** (loi des mailles) — le long de toute boucle, la somme des tensions est nulle. (Ch. 2)

**Linéarisation par morceaux** — approcher une courbe non-linéaire par des segments de droite ; le segment est choisi d'après le pas précédent. (Ch. 17)

**Masse** (`GND`) — nœud de référence à 0 V ; exclu de la matrice. (Ch. 1)

**MNA** (*Modified Nodal Analysis*) — analyse nodale enrichie de courants de branche pour gérer les sources de tension. (Ch. 7)

**Modèle compagnon** — équivalent temporaire (conductance + source de courant) d'un composant réactif, valable pour un pas. (Ch. 16)

**Nœud** — point de connexion entre composants ; porte une tension inconnue. (Ch. 4)

**Pas de temps** (`dt`) — intervalle entre deux évaluations du circuit. (Ch. 15)

**`prev_state`** — état d'un composant au pas précédent ; mémoire du simulateur. (Ch. 14)

**Stamping** — méthode locale d'assemblage de la matrice, composant par composant. (Ch. 6)

**Verrou** (*lock*) — mécanisme garantissant qu'un seul thread accède à une ressource à la fois. (Ch. 23)

**Voltmètre** — instrument mesurant la tension ; résistance quasi infinie, branché en parallèle. (Ch. 12)
