# Chapitre 20 — L'amplificateur opérationnel idéal

> *Où le composant le plus puissant du catalogue se révèle aussi le plus simple à tamponner — une seule contrainte — mais où comprendre cette contrainte exige de saisir l'idée la plus subtile de l'électronique : la rétroaction.*

## 20.1 Un amplificateur à gain (presque) infini

L'amplificateur opérationnel (« ampli-op ») est une brique de base de l'électronique analogique. Il possède deux entrées — l'entrée **non-inverseuse** (`+`) et l'entrée **inverseuse** (`−`) — et une **sortie**. Son principe est d'amplifier *énormément* la différence de tension entre ses deux entrées :

$$
V_{\text{out}} = A \cdot (V_+ - V_-)
$$

avec un gain `A` colossal — des centaines de milliers, voire davantage. Dans le modèle **idéal**, on pousse cette idée à l'extrême : `A` est considéré comme **infini**.

Un gain infini peut sembler absurde — la moindre différence à l'entrée saturerait la sortie. La clé qui rend l'ampli-op utile est ce qu'on en fait autour : la **rétroaction**.

## 20.2 La rétroaction négative et le « court-circuit virtuel »

Presque tous les montages à ampli-op renvoient une partie de la sortie vers l'entrée inverseuse (`−`). C'est la **rétroaction négative** : la sortie « se corrige elle-même ». Voici le raisonnement, qui est le cœur intellectuel du chapitre.

Supposons que `V_+` soit légèrement supérieur à `V_−`. La sortie, amplifiant cette différence par un gain énorme, monte fortement. Comme elle est reliée à l'entrée `−`, cette montée fait *remonter* `V_−`… jusqu'à ce que `V_−` rattrape `V_+`. À ce moment, la différence s'annule, et le système se stabilise. Le gain infini a un effet contre-intuitif : il force les **deux entrées au même potentiel**.

$$
\boxed{\,V_+ = V_-\,}
$$

On appelle cela le **court-circuit virtuel** : les deux entrées sont au même potentiel comme si elles étaient reliées, *sans* l'être réellement (aucun courant ne circule entre elles). C'est une contrainte que l'ampli-op **impose** au circuit, en ajustant sa sortie pour qu'elle soit vraie.

> Remarquez le renversement : on ne calcule pas `V_out` à partir des entrées (la formule à gain `A`). On pose `V_+ = V_−` comme une **contrainte**, et c'est `V_out` qui devient l'inconnue, libre de prendre *la valeur qu'il faut* pour satisfaire cette contrainte. Exactement comme une source de tension imposait `V` et laissait son courant libre (chapitre 7) !

## 20.3 Une vieille connaissance : la branche MNA

Ce renversement vous dit quelque chose. Un composant qui **impose une relation de tension** et dont une grandeur de sortie est **libre** : c'est précisément le cas qui a donné naissance à la MNA et aux **branches** (chapitre 7). L'ampli-op idéal réutilise donc exactement ce mécanisme. Il déclare `needs_branch()`, et son inconnue de branche est le **courant de sortie** — ce courant que l'ampli débite pour maintenir la contrainte.

Son stamping est, de fait, l'un des plus courts du simulateur ([simulator/components.py](../../simulator/components.py#L506-L519)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_p = node_map.get(self.node_plus, -1)
    idx_n = node_map.get(self.node_minus, -1)
    idx_o = node_map.get(self.node_out, -1)
    branch = branch_map[self.id]
    # Ligne de branche : impose V(plus) - V(minus) = 0
    if idx_p >= 0:
        G[branch, idx_p] += 1.0
    if idx_n >= 0:
        G[branch, idx_n] -= 1.0
    # Colonne KCL : le courant de sortie est injecté sur node_out
    if idx_o >= 0:
        G[idx_o, branch] += 1.0
    b[branch] = 0.0
```

Décortiquons-le à la lumière du chapitre 7 :

- **La ligne de branche** (`G[branch, idx_p] += 1`, `G[branch, idx_n] -= 1`, `b[branch] = 0`) écrit la contrainte `V_+ − V_− = 0`. C'est le court-circuit virtuel, posé noir sur blanc.
- **La colonne de branche** (`G[idx_o, branch] += 1`) injecte le courant inconnu de la branche sur le nœud de **sortie**. C'est par là que l'ampli « agit » sur le circuit.

Notez l'asymétrie avec la source de tension : ici, la contrainte porte sur les entrées (`+`, `−`), mais le courant est injecté sur une *troisième* borne (la sortie). C'est ce découplage entrée/sortie qui fait de l'ampli-op un composant **actif** : il prélève un courant négligeable sur ses entrées (elles n'apparaissent pas dans la colonne) et fournit le courant nécessaire en sortie.

## 20.4 Linéaire, mais subtil

Un point d'honnêteté, dans l'esprit de la Partie V. À la différence de la diode et du transistor, l'ampli-op **idéal est en réalité linéaire** : sa contrainte `V_+ = V_−` est une équation linéaire, sans coude ni régime. Il n'utilise d'ailleurs pas `prev_state`. Pourquoi figure-t-il alors parmi les composants non-linéaires ?

Parce qu'il est le **point culminant** des composants actifs, et que sa difficulté n'est pas mathématique mais **conceptuelle** : il faut comprendre la rétroaction pour saisir pourquoi `V_+ = V_−`. Un ampli-op *réel* est, lui, bel et bien non-linéaire (sa sortie sature, son gain est fini). Notre modèle idéalisé fait l'impasse sur ces limites, mais capture l'essentiel — la contrainte du court-circuit virtuel — qui suffit à analyser l'immense majorité des montages.

## 20.5 Ce que l'ampli-op permet de construire

Avec ce simple « `V_+ = V_−` plus une sortie libre », on bâtit une étonnante variété de circuits : amplificateurs de gain réglable, additionneurs, soustracteurs, comparateurs, filtres actifs, intégrateurs… L'ampli-op est le couteau suisse de l'analogique. Tout son pouvoir tient dans cette contrainte que le simulateur exprime en quatre lignes — preuve qu'une bonne abstraction (la branche MNA) rend simple ce qui paraissait redoutable.

## 20.6 À retenir

- L'**ampli-op idéal** amplifie la différence `V_+ − V_−` avec un gain supposé **infini**.
- Combiné à la **rétroaction négative**, ce gain infini force le **court-circuit virtuel** : `V_+ = V_−`. La sortie `V_out` s'ajuste librement pour satisfaire cette contrainte.
- C'est le même schéma que la source de tension : il **impose une relation** et laisse un courant **libre** → il réutilise la **branche MNA** (`needs_branch`), son inconnue étant le **courant de sortie**.
- Stamping en deux temps : la **ligne** pose `V_+ − V_− = 0` ; la **colonne** injecte le courant de branche sur le nœud de **sortie** (découplage entrée/sortie = caractère actif).
- Le modèle idéal est en fait **linéaire** ; il est ici pour sa richesse **conceptuelle** (la rétroaction), non pour une non-linéarité mathématique.

**Ceci clôt la Partie V**, et avec elle le tour complet du catalogue : vous comprenez désormais **chacun des composants** du simulateur, du plus passif (la résistance) au plus actif (l'ampli-op).

**La Partie VI**, la dernière, prend de la hauteur : nous quitterons les composants pour observer la **machinerie d'ensemble** — la boucle de simulation en temps réel, le chargement des circuits, la concurrence entre threads, et enfin les limites et extensions possibles du moteur.
