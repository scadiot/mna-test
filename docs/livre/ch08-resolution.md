# Chapitre 8 — Résoudre le système

> *Où l'on confie la matrice à `numpy`, où l'on apprend ce que « résoudre » veut dire, et surtout où l'on découvre les circuits impossibles qui font apparaître l'erreur la plus redoutée du simulateur : la matrice singulière.*

## 8.1 Ce que « résoudre » signifie

À la fin du chapitre 7, nous avons un système complet :

$$
G \cdot x = b
$$

`G` et `b` sont **connus** (assemblés par le stamping). L'inconnue est `x`, le vecteur des tensions de nœud et des courants de branche. Résoudre, c'est trouver l'unique vecteur `x` qui satisfait *toutes* les équations à la fois — c'est-à-dire le seul jeu de tensions et de courants pour lequel les lois de Kirchhoff sont respectées partout dans le circuit, simultanément.

Géométriquement, chaque ligne du système est une contrainte. Avec `n` inconnues, on a `n` contraintes, et leur intersection est (en général) un point unique : la solution. Tout l'enjeu du chapitre tient dans ces deux mots — « en général ». Parfois, il n'y a pas de point unique. Nous y viendrons au §8.4.

## 8.2 La résolution en une ligne

Inverser une matrice à la main est pénible dès la taille 3, et impensable au-delà. Heureusement, l'algèbre linéaire numérique est un domaine mûr, et `numpy` offre une fonction dédiée. Tout le travail tient dans une ligne du moteur ([simulator/engine.py](../../simulator/engine.py#L60-L64)) :

```python
try:
    x = np.linalg.solve(G, b)
except np.linalg.LinAlgError as e:
    self._state.set_error(f"Matrice singulière à t={t:.6f}s : {e}")
    return False
```

`np.linalg.solve(G, b)` calcule `x`. En coulisses, il n'« inverse » pas réellement `G` (ce serait coûteux et imprécis) : il procède par **élimination de Gauss** — la version automatisée des substitutions que nous avons faites à la main au chapitre 5. Il combine les lignes pour faire disparaître les inconnues une à une, jusqu'à isoler chaque valeur.

Le `try / except` est essentiel : si le circuit décrit un système **insoluble**, `numpy` lève une `LinAlgError`. Le moteur ne plante pas : il enregistre un message d'erreur explicite (avec l'instant `t` fautif) et interrompt proprement la simulation. C'est un exemple de robustesse qu'on attend d'un simulateur — un circuit mal formé doit produire un *diagnostic*, pas un crash.

## 8.3 De la solution `x` aux grandeurs physiques

Une fois `x` obtenu, il faut le retraduire en quantités lisibles. Le moteur sépare les tensions de nœud des autres résultats ([simulator/engine.py](../../simulator/engine.py#L66-L68)) :

```python
node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
node_voltages["GND"] = 0.0
```

On parcourt la table des nœuds pour récupérer chaque tension dans `x`, et l'on rajoute « à la main » la masse à 0 V — fidèle à son statut de référence (chapitre 1), absente de `x` mais bien présente dans les résultats.

Ensuite, chaque composant calcule ses propres grandeurs via `get_state` (la méthode-miroir du stamping, chapitre 6) : une résistance en déduit son courant, une source de tension lit son courant de branche, etc. C'est le **chemin du retour** : de la matrice vers la physique observable.

## 8.4 Le cauchemar du simulateur : la matrice singulière

Une matrice est dite **singulière** lorsque le système n'a *pas* de solution unique — soit aucune solution, soit une infinité. Dans les deux cas, `np.linalg.solve` échoue. Physiquement, une matrice singulière signale presque toujours un circuit **mal défini**. Voici les deux coupables les plus fréquents.

### Cause n°1 : le nœud flottant

Imaginez un nœud relié au reste du circuit par… rien. Ou seulement par des composants qui n'imposent aucune relation exploitable. Sa tension est alors **indéterminée** : rien dans le circuit ne la fixe. Le solveur, sommé de trouver une valeur unique, n'en trouve aucune — il y en a une infinité de possibles.

Le cas d'école : un sous-circuit **sans aucun chemin vers la masse**. Souvenez-vous que tout se mesure par rapport à `GND` (chapitre 1). Si une partie du circuit n'a aucune connexion (même indirecte) à la masse, ses potentiels « flottent » sans ancrage. C'est l'erreur la plus courante du débutant : *oublier de relier son montage à la masse.*

C'est aussi pourquoi certains composants du simulateur, qui devraient être de parfaits isolants, sont en réalité dotés d'une conductance **minuscule mais non nulle**. Le voltmètre en est l'exemple ([components.py](../../simulator/components.py#L247-L251)) :

```python
# 1e9 Ω → conductance 1e-9 S, pratiquement invisible pour le circuit
_stamp_conductance(G, idx_a, idx_b, 1e-9)
```

Cette conductance de `1e-9 S` est électriquement négligeable (elle ne perturbe pas les mesures), mais elle **ancre** le nœud : elle lui donne un chemin, si ténu soit-il, et empêche la matrice de devenir singulière. C'est une astuce numérique classique : préférer un « presque infini » à un véritable infini (chapitre 3), précisément pour rester du bon côté de la solubilité.

### Cause n°2 : la contradiction

L'inverse du nœud flottant : un circuit qui impose deux contraintes **incompatibles**. Par exemple, deux sources de tension idéales, branchées en parallèle sur les mêmes nœuds, mais réglées à des valeurs différentes : l'une dit « 5 V », l'autre « 3 V ». Aucune solution ne peut satisfaire les deux à la fois. La matrice est, là encore, singulière — non par manque de contrainte, mais par excès contradictoire. (Un court-circuit pur sur une source de tension idéale relève de la même pathologie.)

## 8.5 Un mot sur la précision : le conditionnement

Même quand une matrice n'est pas tout à fait singulière, elle peut en être *dangereusement proche*. C'est typiquement ce qui arrive quand on fait cohabiter des valeurs extrêmes — par exemple la conductance de `1e6 S` d'un interrupteur fermé à côté du `1e-9 S` d'un voltmètre. On parle alors de matrice **mal conditionnée** : la résolution reste possible, mais l'arithmétique en virgule flottante de l'ordinateur y perd en précision, et de petites erreurs d'arrondi peuvent s'amplifier.

Notre simulateur reste dans des plages raisonnables et n'a, en pratique, pas à s'en soucier. Mais c'est une bonne chose à garder en tête : les nombres « extrêmes » que nous utilisons pour approcher les idéaux (chapitre 3) ont un coût caché. Trop extrêmes, ils dégraderaient les résultats ; le choix de `1e9` et `1e-6` plutôt que `1e30` et `1e-30` est un compromis délibéré entre fidélité au modèle idéal et stabilité numérique.

## 8.6 Le cycle complet d'un pas de simulation

Nous pouvons à présent résumer ce qu'accomplit un **pas** de simulation — la fonction `_step` que nous décortiquerons en détail au chapitre 21 :

1. **Créer** une matrice `G` et un vecteur `b` remplis de zéros (taille = nœuds + branches).
2. **Tamponner** : chaque composant ajoute sa contribution (chapitres 6 et 7).
3. **Résoudre** `G·x = b` avec `np.linalg.solve` (ce chapitre).
4. **Extraire** les tensions de nœud, puis l'état de chaque composant via `get_state`.
5. **Publier** les résultats et passer au pas de temps suivant.

À ce stade du livre, vous comprenez entièrement les étapes 1 à 4 pour un circuit **purement résistif**. Il manque encore une dimension capitale : le **temps**. Comment un condensateur « se souvient-il » de son état d'un pas à l'autre ? C'est tout l'objet de la Partie IV.

## 8.7 À retenir

- **Résoudre** `G·x = b`, c'est trouver l'unique jeu de tensions et de courants satisfaisant toutes les lois de Kirchhoff simultanément.
- Le moteur le fait via `np.linalg.solve(G, b)`, qui procède par **élimination de Gauss** (la version automatique du chapitre 5).
- Une **matrice singulière** (système sans solution unique) lève une `LinAlgError`, soigneusement rattrapée pour produire un **diagnostic** plutôt qu'un crash.
- Causes classiques : le **nœud flottant** (souvent : pas de chemin vers la masse) et la **contradiction** (sources incompatibles). Les conductances minuscules (`1e-9 S` du voltmètre) servent à **ancrer** les nœuds et éviter la singularité.
- Des valeurs trop extrêmes dégradent le **conditionnement** (la précision) : `1e9 / 1e-6` est un compromis volontaire.

**Ceci clôt la Partie II.** Vous maîtrisez désormais toute la chaîne « du circuit aux tensions résolues » pour les composants linéaires et statiques. **La Partie III** ouvre le catalogue des composants un à un — en commençant, au chapitre 9, par la résistance, vue cette fois sous l'angle du composant réel et de ses usages.
