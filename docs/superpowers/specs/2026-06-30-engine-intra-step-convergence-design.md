# Convergence intra-pas du moteur (point fixe sur états discrets)

Date : 2026-06-30
Statut : design validé

## Objectif

Faire converger les composants non-linéaires (BJT, diode) **à l'intérieur de
chaque pas de temps** au lieu de décider de leur état d'après le seul pas
précédent. But concret : réduire les artefacts numériques du solve unique
(excursions de tension absurdes aux commutations) et alléger les bricolages
introduits dans les trois bascules flip-flop.

## Contexte et cause racine (établis par lecture du code)

- [`engine.py`](../../../simulator/engine.py) `_step()` fait **un seul**
  `np.linalg.solve` par pas. Les composants non-linéaires décident de leur état
  d'après `prev_state` (état du pas **précédent**) :
  [`BJT.stamp`](../../../simulator/components.py) lit
  `prev_state["vbe"|"vce"|"current"|"saturated"|"ic"]` ;
  [`Diode.stamp`](../../../simulator/components.py) lit `prev_state["voltage"]`.
- Conséquence : quand un transistor passe brutalement actif, la source de
  courant contrôlée `β·ib` calculée sur l'ib du pas précédent surinjecte → le
  collecteur part à plusieurs centaines de volts négatifs en un pas → l'état
  rebascule au pas suivant → **cycle limite numérique** aux commutations.

## Résultats du prototype (mesurés, validant le design)

Un prototype jetable de la boucle de point fixe (hors dépôt) a mesuré, sur
l'astable :

- Astable `Rb=100k` (asymétrie de couplage 10/12 µF), **sans** condensateurs de
  découplage : le pic minimal de collecteur passe de **−394 V (solve unique) à
  −36 V (avec convergence)** et l'oscillation est préservée (8 transitions sur
  4000 pas).
- Astable `Rb=47k` : **n'oscille pas** même avec convergence (verrouillage en
  double-saturation). C'est un **vrai point d'équilibre** du circuit symétrique
  dans ce modèle (en saturation le BJT piecewise-linéaire n'a aucun gain
  régénératif). `Rb=100k` reste donc nécessaire.
- Aux instants de commutation, la boucle de point fixe **thrashe** (atteint le
  plafond d'itérations sans converger sur ~3 pas/4000) ; le dernier itéré
  best-effort est le résidu de −36 V.

Ces mesures fixent les **critères de succès réalistes** ci-dessous : la
convergence améliore nettement mais n'élimine pas totalement les pics, et ne
supprime pas le besoin de `Rb=100k`.

## Approche retenue

**Itération de point fixe sur les états discrets** des composants
piecewise-linéaires. Chaque état (bloqué/actif/saturé ; passant/bloqué) définit
un stamp **linéaire** ; on boucle « stamp → solve → re-décide les états →
re-stamp » jusqu'à stabilité des états discrets. Aucun jacobien.

Alternatives écartées : Newton-Raphson avec modèles lisses + jacobiens (réécrit
tous les composants — hors de proportion) ; limitation/amortissement de tension
par pas avec solve unique (bricolage, ne traite pas la cause).

## Conception détaillée

### Insight : aucun changement de signature de `stamp`

Réactifs et non-linéaires lisent déjà tout ce qu'il leur faut dans `prev_state`.
Seul le **moteur** change : il contrôle *ce qu'il place* dans cet état entre
itérations. Les ~20 tests de
[`test_components.py`](../../../tests/test_components.py) qui appellent
`stamp(..., prev_state=...)` restent **intacts**.

### 1. `simulator/components.py` (additif)

Ajouter une propriété `is_nonlinear` sur `Component` (défaut `False`),
surchargée à `True` sur `BJT` et `Diode`. Le moteur s'en sert pour savoir quels
composants ré-itérer. Additif : aucun test cassé.

### 2. `simulator/engine.py` — réécriture de `_step`

```
hist        = snapshot figé de _prev_states         # historique temporel C/L — FIGÉ
iter_states = copie de hist
x_prev = None
pour k de 0 à MAX_ITER-1 :
    G,b ← pour chaque comp : comp.stamp(..., prev_state=iter_states[comp.id])
    x   ← solve(G,b)                                 # singulière → set_error, abandon (inchangé)
    comp_states ← { comp.id: comp.get_state(x) }     # état issu de CE solve
    si x_prev existe et ‖x − x_prev‖∞ < TOL : convergé, sortir   # comp_states est à jour
    x_prev = x
    pour chaque comp où comp.is_nonlinear : iter_states[comp.id] = comp_states[comp.id]
    # les réactifs et linéaires NE sont PAS mis à jour → hist reste figé
# en sortie (convergé OU MAX_ITER atteint), comp_states = état du dernier solve
recalcul des courants C/L depuis hist (bloc existant, inchangé)
_prev_states = comp_states
```

- **Critère de convergence** : `‖x − x_prev‖∞ < TOL` avec `TOL = 1e-9`. Pour du
  piecewise-linéaire, dès que les états discrets se stabilisent les tensions
  sont identiques (Δ ≈ 0), donc ce seuil très serré détecte la convergence sans
  réglage fin.
- **`MAX_ITER`** : constante module (valeur initiale **100**). À l'atteindre
  sans convergence → comportement best-effort.
- **Non-convergence (best-effort)** : on garde le dernier `comp_states` et on
  avance le temps. Aucune interruption, aucun compteur exposé dans
  `SharedState` (choix utilisateur : « continuer »).
- **Matrice singulière** : comportement actuel conservé (`set_error`, arrêt
  propre) — peut survenir à n'importe quelle itération.
- Le bloc de recalcul des courants réactifs et le throttle CPU
  ([`engine.py` `_compute_sleep`](../../../simulator/engine.py)) restent
  inchangés.

### 3. Interaction avec le heuristique de saturation du BJT (risque connu)

[`BJT.stamp`](../../../simulator/components.py) contient une logique de
maintien en saturation à retard d'un pas
(`if sat_prev: self._sat = i_c_drive >= ic_prev`). Pendant l'itération
intra-pas, `sat_prev`/`ic_prev` proviennent de l'itéré (mis à jour à chaque
tour), ce qui peut **entretenir le thrashing** observé aux commutations.

Décision : **ne pas réécrire le modèle BJT dans ce périmètre.** On accepte le
thrashing résiduel (best-effort, ~3 pas/4000) qui produit le pic de −36 V. Une
refonte du heuristique de saturation (ou un voltage-limiting à la SPICE) est
notée comme **travail futur** distinct, hors de cette spec.

### 4. Tests

Dans [`tests/test_engine.py`](../../../tests/test_engine.py) :

- **Non-régression** : tous les tests existants du dépôt restent verts
  (RC, RLC, diodes, AOp, BJT amplificateur, bascules, etc.).
- **Suppression des excursions absurdes** : un astable `Rb=100k` **sans**
  condensateurs de découplage donne `min(collecteur) > −50 V` avec la
  convergence (vs ≈ −394 V sans), tout en oscillant (≥ 4 transitions). Le seuil
  −50 V encadre le résidu mesuré (−36 V) sans coller à la valeur exacte.
- **Convergence nominale** : sur un circuit BJT en régime actif stable
  (ex. l'amplificateur de `test_engine.py`), le pas converge en peu
  d'itérations (assertion : le moteur expose le nombre d'itérations du dernier
  pas via un attribut interne `_last_iterations`, et il est `< MAX_ITER` en
  régime établi).
- **Best-effort sur non-convergence** : vérifier qu'un pas qui atteint
  `MAX_ITER` n'interrompt pas la simulation (pas d'erreur, le temps avance).

`_last_iterations` (attribut interne du moteur, non exposé à `SharedState`) est
ajouté uniquement pour rendre la convergence testable.

### 5. Simplification des bascules (preuve tangible)

Une fois la convergence en place, re-tester chaque bascule et appliquer la
simplification que la simulation **autorise réellement** (validée par les tests
de [`test_flip_flop_circuits.py`](../../../tests/test_flip_flop_circuits.py)) :

- **Retrait/réduction des condensateurs de découplage `Cc`** : les pics étant
  réduits ~10×, retirer les `Cc` si le comportement reste propre, sinon les
  **réduire fortement** (la valeur de 200 µF de l'astable, plus grosse que les
  condensateurs de couplage, doit au minimum redescendre à un ordre de grandeur
  raisonnable). Critère : les tests de comportement (oscillation / mémorisation /
  impulsion) passent avec les seuils inchangés (bas < 1 V, haut > 3 V).
- **`Rb` de l'astable** : reste à **100 kΩ** (le prototype confirme que 47 kΩ
  ne réoscille pas). Documenté comme choix de conception, non comme bricolage.
- **Dissymétrie du bistable** : re-testée ; conservée si encore nécessaire pour
  un état de démarrage défini, sinon retirée.

Chaque valeur conservée est documentée comme choix de conception légitime.

## Critères de succès (réalistes, ancrés sur le prototype)

1. Tous les tests existants du dépôt restent verts.
2. Avec la convergence, l'astable `Rb=100k` **sans `Cc`** a `min(collecteur) >
   −50 V` (vs ≈ −394 V) et oscille — la convergence remplace l'essentiel du rôle
   des `Cc`.
3. Les `Cc` des trois bascules sont **retirés ou fortement réduits**, tests de
   comportement verts.
4. La simulation ne s'interrompt jamais sur non-convergence (best-effort).

Explicitement **hors** des critères : élimination totale des pics de
commutation et retour de `Rb` à 47 kΩ — le prototype montre que la seule
convergence ne les atteint pas.

## Hors périmètre (YAGNI)

- Pas de Newton-Raphson ni de modèles de composants lisses.
- Pas de réécriture du heuristique de saturation du BJT ni de voltage-limiting
  (travail futur séparé).
- Pas de modification de la signature de `stamp` ni des modèles réactifs.
- Pas d'exposition de métriques de convergence dans `SharedState`/l'UI.

## Risques

- **Thrashing résiduel** aux commutations (best-effort) : accepté, borné par
  `MAX_ITER`, résidu ≈ −36 V documenté.
- **Coût CPU** : quelques itérations par pas. Négligeable sur ces petits
  circuits ; le throttle existant borne déjà l'occupation CPU.
- **Non-régression** : le risque principal. La boucle commune change pour
  **tous** les circuits → la batterie de tests de non-régression est la garde-fou
  essentielle avant tout merge.
