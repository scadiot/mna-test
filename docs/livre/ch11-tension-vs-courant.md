# Chapitre 11 — Sources de tension vs sources de courant

> *Où deux composants jumeaux révèlent une profonde dualité : l'un fixe la tension et subit le courant, l'autre fixe le courant et subit la tension. Deux faces d'une même pièce.*

## 11.1 Deux façons opposées d'imposer sa loi

Au chapitre 10, nous avons choisi une forme d'onde. Reste à décider *quelle grandeur* la source impose. Il y a deux possibilités, exactement opposées :

- une **source de tension** dit : *« je fixe la tension entre mes bornes ; le courant, je le fournirai, quel qu'il soit. »*
- une **source de courant** dit : *« je fixe le courant qui me traverse ; la tension à mes bornes, je la subirai, quelle qu'elle soit. »*

C'est une **dualité** parfaite. Ce que l'une fixe, l'autre le subit, et réciproquement. Cette symétrie se reflète jusque dans le code : leurs deux stampings sont radicalement différents, et c'est tout l'intérêt de ce chapitre.

| | Source de tension | Source de courant |
|---|---|---|
| **Impose** | la tension `V_pos − V_neg` | le courant injecté |
| **Subit (inconnu)** | son courant | sa tension |
| **Inconnue de branche ?** | **oui** (`needs_branch`) | **non** |
| **S'inscrit dans…** | une ligne/colonne de branche | le vecteur `b` |

## 11.2 La source de tension : un rappel

Nous l'avons longuement étudiée au chapitre 7, car c'est elle qui a justifié toute la MNA. Récapitulons l'essentiel : comme elle impose une tension mais laisse son courant libre, elle a besoin d'une **inconnue de branche** (`needs_branch()` renvoie `True`). Son stamping écrit deux choses : la ligne de contrainte `V_pos − V_neg = valeur`, et la colonne qui injecte le courant de branche dans la loi des nœuds des deux bornes.

Son `get_state` récupère ce courant subi ([simulator/components.py](../../simulator/components.py#L344-L349)) :

```python
def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_pos)
    vb = _node_voltage(x, node_map, self.node_neg)
    branch = branch_map[self.id]
    current = -x[branch]   # courant fourni par la source (convention générateur)
    return {"voltage": va - vb, "current": current}
```

Le courant n'est pas calculé : il est **lu** dans la solution, à l'indice de branche. C'est le reste du circuit qui l'a déterminé.

## 11.3 La source de courant : la simplicité retrouvée

La source de courant est, paradoxalement, *plus simple* que sa jumelle. Pourquoi ? Parce qu'elle injecte une grandeur **connue** — un courant — directement dans la loi des nœuds. Or la loi des nœuds est précisément un bilan de courants (chapitre 2) ! Un courant connu s'y inscrit sans détour, dans le vecteur `b`, **sans aucune inconnue supplémentaire**. Elle n'a donc **pas besoin de branche** ([components.py](../../simulator/components.py#L371-L379)) :

```python
def needs_branch(self):
    return False

def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    current = self.source.voltage(t)   # la valeur imposée (ici, un courant)
    # Injecte 'current' ampères entrant en idx_a, sortant de idx_b
    _stamp_current(b, idx_a, idx_b, current)
```

C'est exactement le `_stamp_current` du chapitre 6 — celui-là même qui injectait nos sources de courant dans l'exemple résolu à la main du chapitre 5. Rien de neuf : une source de courant ne touche **jamais** la matrice `G`, seulement le vecteur `b`.

Et son `get_state` ? Sa tension est inconnue *a priori*, mais une fois le système résolu, les tensions des nœuds `a` et `b` sont connues : il suffit de les lire et de les soustraire ([components.py](../../simulator/components.py#L381-L384)).

```python
def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    return {"voltage": va - vb, "current": 0.0}
```

La tension subie est `va − vb` ; le courant, lui, est fixé par la source (le champ est laissé à `0.0` ici car la valeur connue est déjà l'amplitude imposée).

## 11.4 Une question de signe : la convention générateur

Les signes méritent une halte, car ils déroutent souvent. Une source *fournit* de l'énergie au circuit : c'est un **générateur**. Pour un générateur, on adopte la convention où le courant *sort* par la borne `+`. C'est la raison du signe « moins » dans le `get_state` de la source de tension : `current = -x[branch]`. L'inconnue de branche `x[branch]` est comptée selon une convention interne ; on la retourne pour présenter à l'utilisateur le courant **réellement débité** par la source.

Au chapitre 7, notre diviseur donnait `x[branch] = −3 A`, donc un courant débité de `+3 A` — un nombre positif, conforme à l'intuition « la source fournit 3 A ». Les conventions de signe ne sont pas de la bureaucratie : elles garantissent que les valeurs affichées correspondent à ce qu'un physicien attend.

## 11.5 Quand utiliser l'une ou l'autre ?

En pratique :

- **Source de tension** : modélise une pile, une alimentation régulée, le secteur, la sortie d'un étage qui maintient une tension. C'est de loin la plus courante.
- **Source de courant** : modélise un composant qui *force un courant* indépendamment de la tension — par exemple le courant de polarisation d'un transistor, ou une source de référence en électronique intégrée. On la retrouvera, sous forme *contrôlée*, au cœur du modèle du transistor (chapitre 19), où le courant de collecteur `I_C = β·I_B` est précisément injecté par un `_stamp_current`.

## 11.6 À retenir

- **Dualité fondamentale** : la source de tension fixe `V` et subit `I` ; la source de courant fixe `I` et subit `V`.
- La **source de tension** a besoin d'une **branche** (MNA, chapitre 7) ; son courant est *lu* dans la solution.
- La **source de courant** est plus simple : un courant connu s'inscrit directement dans le vecteur `b` via `_stamp_current`, **sans branche**, sans toucher `G`.
- La **convention générateur** explique le signe « moins » sur le courant de la source de tension : on affiche le courant réellement débité.
- Tension → piles, alimentations. Courant → polarisations, sources de référence, et le modèle du transistor (chapitre 19).

**Dans le prochain chapitre**, nous brancherons des *instruments* sur le circuit : le **voltmètre** et l'**ampèremètre**. Nous verrons qu'ils sont, eux aussi, des cas particuliers de tout ce que nous savons déjà — l'un une résistance quasi infinie, l'autre une source de tension de 0 V.
