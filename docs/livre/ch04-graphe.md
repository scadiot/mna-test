# Chapitre 4 — Modéliser un circuit comme un graphe

> *Où l'on cesse de voir un schéma électronique comme un dessin, pour le voir comme ce qu'il est vraiment aux yeux du simulateur : une liste de nœuds numérotés et de composants qui les relient.*

## 4.1 Du schéma au graphe

Un humain lit un circuit comme un dessin : des symboles, des fils qui serpentent, une disposition spatiale. Le simulateur, lui, se moque complètement de la géométrie. Pour lui, un circuit n'est qu'une structure abstraite : un **graphe**.

Un graphe, c'est deux choses :

- des **nœuds** : les points de connexion (là où des fils se rejoignent) ;
- des **composants** : les éléments (résistances, sources…) qui relient ces nœuds entre eux.

Tout ce que le dessin contient en plus — la position des symboles, la longueur des fils, les couleurs — est sans aucune importance électrique. Seule compte la **topologie** : *qui est connecté à qui*. Deux schémas qui paraissent très différents mais relient les mêmes composants aux mêmes nœuds sont, pour le simulateur, strictement identiques.

> Un fil, dans cette vision, n'est pas un composant : c'est simplement *l'absence de séparation*. Deux bornes reliées par un fil ne forment qu'**un seul et même nœud**.

C'est un changement de regard essentiel. Dans la suite du livre, oubliez le joli dessin : pensez « nœuds et connexions ».

## 4.2 Nommer les nœuds

Dans notre simulateur, chaque nœud porte un **nom** (une chaîne de caractères) : `"n1"`, `"out"`, `"vcc"`, etc. Et l'un de ces noms est réservé : `"GND"`, la masse, dont nous savons depuis le chapitre 1 qu'elle vaut toujours 0 V.

Chaque composant déclare la liste des nœuds qu'il touche, via sa méthode `get_nodes()`. Une résistance en touche deux, un transistor trois, et ainsi de suite. Le simulateur n'a donc pas besoin d'un « plan » du circuit : il lui suffit de demander à chaque composant *« quels nœuds relies-tu ? »* et de recoller les morceaux. Si deux composants mentionnent le nœud `"out"`, c'est qu'ils y sont connectés ensemble — voilà tout le secret de la topologie.

## 4.3 Des noms aux indices : la table des nœuds

Les noms sont commodes pour l'humain, mais une matrice ne connaît que des **indices** : ligne 0, ligne 1, ligne 2… Il faut donc traduire chaque nom de nœud en un numéro de ligne (et de colonne) dans la matrice `G`. Cette traduction, c'est la **table des nœuds** : le dictionnaire `node_map` qui associe `{nom: indice}`.

Sa construction obéit à deux règles que nous avons préparées dans les chapitres précédents :

1. **La masse est exclue.** Puisque `GND` vaut 0 V, sa tension n'est pas une inconnue ; elle n'a donc ni ligne ni colonne. On ne lui attribue aucun indice.
2. **L'ordre est déterministe.** Les noms sont triés alphabétiquement avant de recevoir leur indice. Ce détail garantit que, pour un même circuit, la matrice est toujours construite à l'identique — ce qui rend les résultats reproductibles et le débogage possible.

Voici la traduction en code, dans [simulator/engine.py](../../simulator/engine.py#L30-L40) :

```python
def _build_maps(self):
    """Attribue un indice à chaque nœud non-GND et à chaque branche de tension."""
    node_set = set()
    for comp in self._components:
        for node in comp.get_nodes():
            if node != "GND":              # règle 1 : la masse est exclue
                node_set.add(node)

    # Tri alphabétique pour un ordre déterministe (règle 2)
    for i, name in enumerate(sorted(node_set)):
        self._node_map[name] = i
```

Le mécanisme est limpide : on parcourt tous les composants, on récolte tous les noms de nœuds (sauf `GND`) dans un ensemble (qui élimine au passage les doublons), on les trie, puis on les numérote `0, 1, 2…`. Si un circuit comporte trois nœuds nommés `"a"`, `"b"`, `"out"` plus la masse, on obtiendra `node_map = {"a": 0, "b": 1, "out": 2}`. La matrice `G` fera donc 3×3 (avant l'ajout des branches, voir §4.4).

## 4.4 Au-delà des nœuds : les branches

La table des nœuds suffirait si tous les composants se contentaient de dire *« je laisse passer tel courant en fonction de la tension »* (le cas de la résistance). Mais certains composants imposent autre chose : une source de tension dit *« entre mes bornes, la tension **vaut** 6 V »*, sans qu'on connaisse d'avance le courant qui la traverse.

Pour gérer ces composants, le simulateur doit ajouter une **inconnue supplémentaire** : le courant inconnu qui circule dans le composant. On appelle cela une **branche**, et chaque composant qui en a besoin le signale par sa méthode `needs_branch()`. Une seconde table, le `branch_map`, attribue à ces composants un indice *après* ceux des nœuds :

```python
branch_idx = len(self._node_map)          # les branches commencent après les nœuds
for comp in self._components:
    if comp.needs_branch():
        self._branch_map[comp.id] = branch_idx
        branch_idx += 1
```

La taille finale de la matrice est donc :

$$
\text{taille} = \underbrace{\text{nombre de nœuds (hors GND)}}_{\text{tensions inconnues}} + \underbrace{\text{nombre de branches}}_{\text{courants inconnus}}
$$

ce que le moteur calcule en une ligne au début de chaque pas :

```python
size = len(self._node_map) + len(self._branch_map)
```

Ne vous inquiétez pas si le rôle exact des branches reste flou : c'est tout le sujet du chapitre 7, où nous découvrirons *pourquoi* et *comment* une branche s'inscrit dans la matrice. Pour l'instant, retenez seulement que la matrice a **deux régions** : une pour les tensions de nœud, une pour les courants de branche.

## 4.5 La carte mémoire complète

Faisons la synthèse visuelle. Pour un circuit à trois nœuds (`a`, `b`, `out`) plus la masse, et une source de tension (qui réclame une branche), le vecteur des inconnues `x` ressemble à ceci :

```
indice :     0       1       2          3
            V_a     V_b    V_out    I_source
           └──────── tensions ───────┘ └ courant ┘
              (depuis node_map)        (depuis branch_map)
```

La matrice `G` est carrée de cette taille (4×4 ici). Sa partie « haut-gauche » concentre les conductances entre nœuds (le stamping du chapitre 6) ; ses dernières lignes/colonnes encodent les branches (chapitre 7). `GND` n'apparaît nulle part — fidèle à son statut de référence muette.

## 4.6 À retenir

- Le simulateur ne voit pas un dessin mais un **graphe** : des **nœuds** reliés par des **composants**. Seule compte la **topologie** (qui est connecté à qui), pas la géométrie.
- Un **fil** n'est pas un composant : deux bornes reliées par un fil forment **un seul nœud**.
- La **table des nœuds** (`node_map`) traduit chaque nom de nœud en un indice de matrice. La masse en est **exclue** ; les noms sont **triés** pour un ordre déterministe.
- Certains composants ajoutent une inconnue de **courant** : une **branche** (`needs_branch()`, `branch_map`), numérotée *après* les nœuds.
- Taille de la matrice = nombre de nœuds (hors GND) + nombre de branches.

**Dans le prochain chapitre**, nous allons enfin remplir cette structure : à partir d'un petit circuit, nous écrirons les équations `G·x = b` *à la main*, en appliquant la loi des nœuds du chapitre 2. Vous y reconnaîtrez, en creux, la méthode de stamping déjà rencontrée au chapitre 6.
