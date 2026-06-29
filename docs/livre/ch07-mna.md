# Chapitre 7 — Quand la nodale ne suffit pas : la MNA

> *Où la source de tension met en échec notre belle méthode, et où la solution — agrandir le système d'une inconnue de courant — fait enfin apparaître le « M » de MNA.*

## 7.1 Le composant qui casse l'analyse nodale

Au chapitre 5, notre méthode reposait sur un principe : chaque composant nous donne *son courant en fonction des tensions* (`I = G·U`), que l'on injecte dans la loi des nœuds. Cela marche pour la résistance, le condensateur, la source de courant… mais pas pour la **source de tension**.

Une source de tension (une pile de 9 V, par exemple) ne dit pas *« je laisse passer tel courant »*. Elle dit l'inverse :

> *« Entre mes deux bornes, la différence de potentiel **vaut** 9 V — et je fournirai **quel que soit** le courant nécessaire pour maintenir cette tension. »*

Le courant à travers la source est donc **inconnu** : il dépend du reste du circuit. Et la loi d'Ohm ne nous aide pas, car une source idéale n'a pas de résistance : on ne peut pas écrire `I = G·U`. Pire, tenter `G = 1/R` avec `R = 0` mènerait à une division par zéro (chapitre 3). L'analyse nodale pure est **bloquée**.

## 7.2 L'idée de la MNA : ajouter le courant comme inconnue

La solution est d'une élégance redoutable. Puisque le courant de la source est inconnu, faisons-en… **une inconnue de plus**.

C'est tout le principe de la **MNA** — *Modified Nodal Analysis*, l'analyse nodale **modifiée**. Le « modifiée » désigne exactement cet ajout : à côté des tensions de nœud, on introduit des **courants de branche** inconnus, un par composant qui impose une tension. C'est la **branche** entrevue au chapitre 4 (`needs_branch()`, `branch_map`).

Ajouter une inconnue exige d'ajouter une équation, sinon le système est sous-déterminé. Heureusement, la source nous en fournit une, gratuitement : *sa* loi, celle qui définit la tension imposée. Le compte est bon :

| On ajoute…              | …et on ajoute en échange              |
|-------------------------|---------------------------------------|
| une inconnue : `I_source` (courant de branche) | une équation : `V_pos − V_neg = tension` |

## 7.3 Les deux rôles de la branche

Concrètement, la nouvelle inconnue `I_source` joue dans la matrice **deux rôles** symétriques. Comprendre cette symétrie, c'est comprendre toute la MNA.

**Rôle n°1 — la nouvelle ligne (l'équation de contrainte).**
On ajoute une ligne au système, qui dit simplement :

$$
V_{\text{pos}} - V_{\text{neg}} = \text{tension imposée}
$$

C'est une **loi des mailles** (chapitre 2) écrite noir sur blanc. Le second membre `b` de cette ligne reçoit la valeur de la tension.

**Rôle n°2 — la nouvelle colonne (le courant dans la loi des nœuds).**
Le courant `I_source` traverse les nœuds `pos` et `neg`. Il doit donc apparaître dans *leurs* équations de la loi des nœuds : il entre dans l'un, sort de l'autre. On ajoute donc `±1` dans les lignes des nœuds, à la colonne de la branche.

Ces deux rôles se reflètent dans la matrice de façon **symétrique** (`+1` en ligne de branche ↔ `+1` en colonne de branche), ce qui préserve une belle propriété de la matrice. Voyons-les dans le code.

## 7.4 Le stamping d'une source de tension

Voici la méthode `stamp` de la source de tension ([simulator/components.py](../../simulator/components.py#L330-L342)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_pos = node_map.get(self.node_pos, -1)
    idx_neg = node_map.get(self.node_neg, -1)
    branch = branch_map[self.id]
    voltage = self.source.voltage(t)
    # Ligne de branche : impose V_pos - V_neg = voltage
    if idx_pos >= 0:
        G[branch, idx_pos] += 1.0      # rôle 1 : ligne de contrainte
        G[idx_pos, branch] += 1.0      # rôle 2 : courant dans la KCL de pos
    if idx_neg >= 0:
        G[branch, idx_neg] -= 1.0      # rôle 1 : ...- V_neg
        G[idx_neg, branch] -= 1.0      # rôle 2 : courant dans la KCL de neg
    b[branch] = voltage                # le second membre = tension imposée
```

Lisez-la en gardant les deux rôles en tête :

- `G[branch, idx_pos] += 1` et `G[branch, idx_neg] -= 1` remplissent la **ligne de branche** : c'est l'équation `V_pos − V_neg = voltage` (rôle 1).
- `G[idx_pos, branch] += 1` et `G[idx_neg, branch] -= 1` remplissent la **colonne de branche** : le courant `I_source` s'invite dans la loi des nœuds des deux bornes (rôle 2).
- `b[branch] = voltage` pose la valeur imposée. Notez que `voltage = self.source.voltage(t)` **dépend du temps** : une source sinusoïdale recalcule cette valeur à chaque pas (ce sera le sujet du chapitre 10).

## 7.5 Un exemple complet : le diviseur de tension

Mettons tout en œuvre. Circuit : une source de **6 V** entre le nœud `a` et la masse, puis deux résistances en série, `R1 = 1 Ω` (entre `a` et `b`) et `R2 = 1 Ω` (entre `b` et la masse).

Indices : `a → 0`, `b → 1`, et la branche de la source → `2`. Trois inconnues : `V_a`, `V_b`, `I_source`. La matrice est 3×3.

Assemblons-la par stamping :

- `R1` (conductance 1, entre `a` et `b`) : `G[0,0]+=1`, `G[1,1]+=1`, `G[0,1]-=1`, `G[1,0]-=1`.
- `R2` (conductance 1, entre `b` et la masse) : une seule marque, `G[1,1]+=1`.
- Source (branche 2, `pos=a`, `neg=GND`) : `G[2,0]+=1`, `G[0,2]+=1`, et `b[2]=6`.

Ce qui donne :

$$
\begin{pmatrix} 1 & -1 & 1 \\ -1 & 2 & 0 \\ 1 & 0 & 0 \end{pmatrix}
\begin{pmatrix} V_a \\ V_b \\ I_{\text{source}} \end{pmatrix}
=
\begin{pmatrix} 0 \\ 0 \\ 6 \end{pmatrix}
$$

Résolvons ligne par ligne :

- **Ligne 3** (la contrainte de la source) : `V_a = 6 V`. La source impose bien sa tension.
- **Ligne 2** (KCL en `b`) : `−V_a + 2 V_b = 0 ⇒ V_b = 3 V`. C'est le **diviseur de tension** : deux résistances égales partagent la tension en deux.
- **Ligne 1** (KCL en `a`) : `V_a − V_b + I_source = 0 ⇒ 6 − 3 + I_source = 0 ⇒ I_source = −3 A`.

Le courant de branche vaut `−3 A`. Le signe est une affaire de convention : le code le retourne pour adopter la convention « générateur » dans `get_state` ([simulator/components.py](../../simulator/components.py#L344-L349)), où l'on lit `current = -x[branch]`, soit **3 A fournis** par la source. Vérification : ce courant traverse `R1` puis `R2` (`6 V / 2 Ω = 3 A`) ✓.

## 7.6 La même mécanique pour d'autres composants

La beauté de la MNA est que la **branche** n'est pas réservée aux piles. Tout composant qui impose une relation faisant intervenir un courant inconnu réutilise exactement le même mécanisme. Dans notre simulateur, trois autres composants déclarent `needs_branch()` :

- **L'ampèremètre** ([components.py](../../simulator/components.py#L289-L300)) : il se comporte comme une source de tension de **0 V** (un court-circuit idéal). Sa ligne de contrainte impose `V_a − V_b = 0`, et son inconnue de branche **est** précisément le courant qu'on cherche à mesurer. Mesurer un courant, en MNA, c'est donc gratuit : il suffit de lire `x[branch]`.

- **L'amplificateur opérationnel idéal** ([components.py](../../simulator/components.py#L506-L519)) : sa contrainte impose `V(+) = V(−)` (les deux entrées au même potentiel), et son courant de branche est injecté sur la sortie. Nous y reviendrons au chapitre 20.

- **La source de tension** elle-même, déjà étudiée, sous toutes ses formes d'onde (chapitre 10).

Une même idée — *ajouter une inconnue de courant et son équation de contrainte* — résout ainsi trois problèmes en apparence très différents. C'est la marque d'une bonne abstraction.

## 7.7 À retenir

- Une **source de tension** impose une tension et laisse son **courant libre** : l'analyse nodale pure, qui exige `I = G·U`, ne sait pas la traiter.
- La **MNA** (analyse nodale *modifiée*) ajoute, pour chaque tel composant, une **inconnue de courant de branche** *et* l'équation de contrainte correspondante. Le système reste carré.
- Cette branche joue **deux rôles symétriques** : une **ligne** (`V_pos − V_neg = valeur`, une loi des mailles) et une **colonne** (le courant entre dans la loi des nœuds des deux bornes).
- Le même mécanisme sert à la source de tension, à l'**ampèremètre** (source 0 V dont la branche *est* le courant mesuré) et à l'**ampli-op** (contrainte `V+ = V−`).

**Dans le prochain chapitre**, le système `G·x = b` est enfin complet — nœuds *et* branches. Reste à le **résoudre** : nous verrons comment `numpy` s'y prend, ce que signifie une **matrice singulière**, et pourquoi un nœud « flottant » ou un montage impossible fait échouer la simulation.
