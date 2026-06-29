# Chapitre 6 — Le « stamping » : assembler la matrice, composant par composant

> *Où l'on découvre que le simulateur ne « lit » jamais le circuit dans son ensemble — il laisse chaque composant écrire lui-même sa petite contribution dans une grande grille de nombres.*

## 6.1 Le problème que l'on cherche à résoudre

Dans le chapitre précédent, nous avons appris à écrire, à la main, les équations d'un circuit grâce à la **loi des nœuds** (KCL) : *en tout nœud, la somme des courants qui entrent égale la somme des courants qui sortent.*

Cela fonctionne très bien sur le papier pour trois résistances. Mais imaginez un circuit de cinquante composants. Personne ne veut écrire cinquante équations à la main — et surtout, un programme ne sait pas « raisonner » sur un schéma comme un humain.

Il nous faut donc une méthode **mécanique** et **locale** : une recette où l'on prend les composants un par un, *sans jamais regarder le reste du circuit*, et où chacun dépose sa contribution au bon endroit. Quand tous les composants ont déposé la leur, le système d'équations est, comme par magie, entièrement construit.

Cette recette porte un nom imagé en anglais : le **stamping** (« tamponner »). Chaque composant est comme un tampon encreur qui laisse sa marque sur une grille. C'est l'idée la plus importante de tout le simulateur, et c'est celle de ce chapitre.

## 6.2 La grille : la matrice de conductance `G`

Rappelons ce que nous voulons construire (chapitre 5) : un système de la forme

$$
G \cdot x = b
$$

- `x` est le vecteur des **inconnues** : les tensions de chaque nœud (sauf la masse, toujours à 0 V).
- `b` est le vecteur des **courants injectés** dans chaque nœud.
- `G` est une matrice carrée : c'est elle que le stamping va remplir.

Le point essentiel — et ce qui rend la méthode possible — est le suivant :

> **Chaque case `G[i, j]` de la matrice a une signification physique précise.**
> La ligne `i` est l'équation KCL du nœud `i`. La colonne `j` dit *« comment la tension du nœud j influence le courant au nœud i »*.

Une fois cette correspondance comprise, le stamping devient évident.

## 6.3 La physique : ce qu'une résistance « dit » à ses deux nœuds

Prenons une résistance `R` branchée entre deux nœuds, `A` et `B`. Sa conductance est `g = 1/R`.

Le courant qui la traverse, de `A` vers `B`, vaut (loi d'Ohm renversée, chapitre 3) :

$$
I_{A \to B} = g \cdot (V_A - V_B)
$$

Réfléchissons à ce que cela signifie pour la **loi des nœuds** à chacune de ses extrémités :

- Au nœud `A`, cette résistance **fait sortir** un courant `g·(V_A − V_B)`.
- Au nœud `B`, cette même résistance **fait entrer** ce courant, donc elle en fait sortir `g·(V_B − V_A)`.

Développons la contribution de la résistance à l'équation du nœud `A`. Le courant sortant est :

$$
g \cdot V_A - g \cdot V_B
$$

Autrement dit, cette résistance ajoute :
- un terme `+g` qui multiplie `V_A` ,
- un terme `−g` qui multiplie `V_B`.

Et par symétrie, sa contribution à l'équation du nœud `B` est :

$$
g \cdot V_B - g \cdot V_A \quad\Rightarrow\quad +g \text{ sur } V_B,\ -g \text{ sur } V_A.
$$

## 6.4 Du calcul au tampon : les quatre marques

Reportons ces quatre termes dans la grille `G`, en se souvenant que *« ligne = équation du nœud, colonne = tension qui multiplie »* :

|              | colonne `A` | colonne `B` |
|--------------|:-----------:|:-----------:|
| **ligne `A`** |   `+g`      |    `−g`     |
| **ligne `B`** |   `−g`      |    `+g`     |

Voilà l'empreinte d'une résistance. Toujours la même, pour *n'importe quelle* résistance, *n'importe où* dans le circuit. Quatre cases :

- `+g` sur les deux cases **diagonales** (`A,A` et `B,B`),
- `−g` sur les deux cases **croisées** (`A,B` et `B,A`).

C'est cette empreinte de quatre marques que le code appelle « tamponner une conductance ». Et c'est exactement ce que fait cette fonction, le cœur battant de [simulator/components.py](../../simulator/components.py#L6-L17) :

```python
def _stamp_conductance(G, idx_a, idx_b, g):
    """
    Ajoute une conductance g entre les nœuds idx_a et idx_b.
    idx = -1 signifie GND (pas de ligne dans la matrice).
    """
    if idx_a >= 0:
        G[idx_a, idx_a] += g          # case diagonale A
    if idx_b >= 0:
        G[idx_b, idx_b] += g          # case diagonale B
    if idx_a >= 0 and idx_b >= 0:
        G[idx_a, idx_b] -= g          # case croisée A,B
        G[idx_b, idx_a] -= g          # case croisée B,A
```

Lisez-la maintenant à la lumière du tableau précédent : ce sont **les quatre marques, ni plus ni moins**.

### Le détail qui compte : la masse (`idx = -1`)

Pourquoi tous ces `if ... >= 0` ? Parce que le nœud de masse (`GND`) est notre **référence à 0 V**. Sa tension n'est pas une inconnue : on la connaît déjà. Elle n'a donc *aucune ligne ni colonne* dans la matrice. Le code signale « ce nœud est la masse » par l'indice spécial `-1`.

Conséquence élégante : une résistance branchée entre `A` et la masse ne dépose qu'**une seule marque**, `+g` sur la case `A,A`. Les trois autres marques concernent une ligne ou une colonne qui n'existe pas — le code les saute simplement. C'est cohérent avec la physique : la masse absorbe ce courant sans qu'on ait besoin de lui écrire une équation.

## 6.5 La magie de l'addition : un exemple complet

Le mot que je vous demande de retenir dans `_stamp_conductance`, c'est `+=` (et non `=`). Chaque composant **ajoute** ses marques à ce qui est déjà là. C'est ce qui permet à des contributions indépendantes de se cumuler dans les mêmes cases.

Prenons un petit circuit concret. Deux nœuds, `n1` et `n2`, et trois résistances :

- `R1 = 1 Ω` (donc `g1 = 1 S`) entre `n1` et `n2`,
- `R2 = 2 Ω` (donc `g2 = 0,5 S`) entre `n2` et la masse,
- `R3 = 4 Ω` (donc `g3 = 0,25 S`) entre `n1` et la masse.

Le simulateur attribue les indices `n1 → 0`, `n2 → 1` (la masse n'a pas d'indice). La matrice `G` fait donc 2×2. Tamponnons les trois résistances, l'une après l'autre :

**Après R1** (entre les indices 0 et 1, quatre marques) :

```
        n1      n2
n1 [   1.0    -1.0  ]
n2 [  -1.0     1.0  ]
```

**Après R2** (entre n2 et la masse : une seule marque, `+0,5` sur la case `1,1`) :

```
        n1      n2
n1 [   1.0    -1.0  ]
n2 [  -1.0     1.5  ]
```

**Après R3** (entre n1 et la masse : une seule marque, `+0,25` sur la case `0,0`) :

```
        n1      n2
n1 [   1.25   -1.0  ]
n2 [  -1.0     1.5  ]
```

Et c'est terminé. Aucun des trois composants n'a eu besoin de connaître l'existence des deux autres. Pourtant, si vous reprenez la loi des nœuds « à la main » pour ce circuit, vous retrouverez exactement cette matrice. Vérifions la première ligne, l'équation KCL du nœud `n1` :

$$
\underbrace{g_1 (V_{n1} - V_{n2})}_{R_1} + \underbrace{g_3 \cdot V_{n1}}_{R_3} = 0
\;\Rightarrow\;
(g_1 + g_3)\,V_{n1} - g_1\,V_{n2} = 0
\;\Rightarrow\;
1{,}25\,V_{n1} - 1{,}0\,V_{n2} = 0.
$$

Les coefficients `1,25` et `−1,0` sont précisément la première ligne de notre matrice. Le stamping n'est donc pas une astuce informatique obscure : c'est *la loi des nœuds, réorganisée pour qu'une machine puisse l'assembler dans n'importe quel ordre.*

## 6.6 Où cela se passe-t-il dans le moteur ?

Le moteur n'a aucune connaissance des résistances, des condensateurs ou des diodes. Il connaît seulement un **contrat** : tout composant sait se tamponner lui-même. Voici le passage de [simulator/engine.py](../../simulator/engine.py#L50-L57) qui orchestre tout, à chaque pas de temps :

```python
size = len(self._node_map) + len(self._branch_map)
G = np.zeros((size, size))      # une grille vide
b = np.zeros(size)

# Chaque composant ajoute sa contribution à G et b
for comp in self._components:
    prev = self._prev_states[comp.id]
    comp.stamp(G, b, self._node_map, self._branch_map, self._dt, t, prev)
```

Trois lignes de logique, et tout le circuit est assemblé. On part d'une grille de zéros (`np.zeros`), puis on demande poliment à chaque composant : *« dépose ta marque »*. La résistance, elle, répond en appelant la fonction que nous venons de disséquer, comme on le voit dans sa méthode `stamp` ([simulator/components.py](../../simulator/components.py#L100-L103)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)   # -1 si le nœud est la masse
    idx_b = node_map.get(self.node_b, -1)
    _stamp_conductance(G, idx_a, idx_b, 1.0 / self.resistance)
```

C'est ici que se concrétise la traduction des noms de nœuds (`"n1"`, `"GND"`…) en indices de matrice, via `node_map.get(..., -1)` — le `-1` étant notre signal « c'est la masse ».

## 6.7 Le chemin du retour : `get_state`

Le stamping construit les équations. Une fois que le moteur a résolu `G·x = b` (le sujet du chapitre 8), le vecteur `x` contient les tensions de tous les nœuds. Mais l'utilisateur, lui, veut souvent savoir : *« quel courant traverse ma résistance ? »*

C'est le rôle, symétrique du stamping, de la méthode `get_state` ([simulator/components.py](../../simulator/components.py#L105-L109)) :

```python
def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    voltage = va - vb
    return {"voltage": voltage, "current": voltage / self.resistance}
```

On relit les deux tensions de nœud dans la solution `x`, on en déduit la tension aux bornes (`V_A − V_B`), et on applique une dernière fois la loi d'Ohm pour le courant. La boucle est bouclée :

> **`stamp`** traduit *la physique du composant → vers* la matrice.
> **`get_state`** traduit *la solution de la matrice → vers* la physique observable.

Tous les composants du livre, du plus simple (la résistance) au plus subtil (le transistor du chapitre 19), suivront ce même aller-retour. Seul le contenu de leur tampon changera.

## 6.8 À retenir

- La **loi des nœuds** (KCL) est le seul principe physique derrière la matrice `G`. Chaque ligne *est* une équation KCL.
- Le **stamping** est une méthode locale : chaque composant ajoute sa contribution sans rien savoir du reste du circuit. Le `+=` est ce qui permet aux contributions de s'additionner.
- L'empreinte d'une **conductance** est universelle : `+g` sur les deux diagonales, `−g` sur les deux croisées.
- La **masse** (indice `-1`) n'a ni ligne ni colonne : ses marques sont simplement ignorées, ce qui correspond exactement à son statut de référence 0 V.
- `stamp` va de la physique vers la matrice ; `get_state` fait le chemin inverse.

**Dans le prochain chapitre**, nous rencontrerons un composant que cette belle mécanique ne sait pas encore gérer : la source de tension. Elle nous forcera à *agrandir* la matrice au-delà des seuls nœuds — et ce sera la naissance du « M » de MNA.
