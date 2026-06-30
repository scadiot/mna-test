# Chapitre 5 — L'analyse nodale : écrire le système à la main

> *Où l'on résout un vrai circuit avec un crayon, en transformant la loi des nœuds en un système d'équations — et où l'on rencontre, pour la première fois en chair et en os, le fameux `G·x = b`.*

## 5.1 Le plan de bataille

Nous avons maintenant tous les ingrédients :

- les **grandeurs** (chapitre 1) : tensions de nœud, courants ;
- la **loi des nœuds** (chapitre 2) : en chaque nœud, la somme des courants est nulle ;
- la **conductance** (chapitre 3) : `I = G·U`, la forme « courant en fonction des tensions » ;
- la **vision en graphe** (chapitre 4) : des nœuds numérotés.

L'**analyse nodale** consiste à combiner tout cela en une recette mécanique :

> Pour chaque nœud (sauf la masse), on écrit la loi des nœuds, en exprimant chaque courant à l'aide de la loi d'Ohm. On obtient autant d'équations que d'inconnues — et donc un système résoluble.

Les **inconnues** sont les tensions de nœud. Faisons-le entièrement sur un exemple.

## 5.2 Le circuit d'étude

Prenons un circuit simple mais non trivial. Deux nœuds, `n1` et `n2`, la masse `GND`, et quatre composants :

- une **source de courant** qui injecte `I = 3 A` dans le nœud `n1` (depuis la masse) ;
- `R1 = 1 Ω` entre `n1` et `n2` (conductance `g₁ = 1 S`) ;
- `R3 = 1 Ω` entre `n1` et `GND` (conductance `g₃ = 1 S`) ;
- `R2 = 1 Ω` entre `n2` et `GND` (conductance `g₂ = 1 S`).

```
        I = 3A
         │
         ▼
        n1 ───[ R1 = 1Ω ]─── n2
         │                    │
      [ R3 = 1Ω ]          [ R2 = 1Ω ]
         │                    │
        GND ────────────────── GND
```

> *Pourquoi une source de courant et non une source de tension ?* Parce qu'une source de courant se contente d'**injecter un courant connu** : elle s'intègre directement dans la loi des nœuds, sans inconnue supplémentaire. La source de tension, plus subtile, attendra le chapitre 7. On commence par le cas pur.

Indices (chapitre 4) : `n1 → 0`, `n2 → 1`. Deux inconnues : `V₁` et `V₂`. On vise donc un système 2×2.

## 5.3 Équation du nœud n1

Appliquons la loi des nœuds en `n1` : *la somme des courants entrants égale la somme des sortants*. Comptons positivement ce qui entre dans `n1`.

- La source **injecte** `+3 A`.
- `R3` relie `n1` à la masse (0 V). Le courant qui **sort** de `n1` vers la masse vaut `g₃·(V₁ − 0) = g₃ V₁`.
- `R1` relie `n1` à `n2`. Le courant qui **sort** de `n1` vers `n2` vaut `g₁·(V₁ − V₂)`.

Le bilan « entrant = sortant » donne :

$$
3 = g_3 V_1 + g_1 (V_1 - V_2)
$$

En regroupant par inconnue :

$$
(g_1 + g_3)\,V_1 - g_1\,V_2 = 3
$$

Avec nos valeurs (`g₁ = g₃ = 1`) :

$$
2\,V_1 - 1\,V_2 = 3 \qquad \text{(équation du nœud n1)}
$$

## 5.4 Équation du nœud n2

Même démarche en `n2`. Aucune source n'y injecte de courant ; le bilan ne fait intervenir que `R1` et `R2`.

- `R1` amène depuis `n1` un courant entrant `g₁·(V₁ − V₂)`.
- `R2` évacue vers la masse un courant sortant `g₂·(V₂ − 0) = g₂ V₂`.

Bilan :

$$
g_1 (V_1 - V_2) = g_2 V_2
\quad\Rightarrow\quad
-g_1\,V_1 + (g_1 + g_2)\,V_2 = 0
$$

Avec les valeurs (`g₁ = g₂ = 1`) :

$$
-1\,V_1 + 2\,V_2 = 0 \qquad \text{(équation du nœud n2)}
$$

## 5.5 Le système sous forme matricielle

Rassemblons nos deux équations :

$$
\begin{cases}
2\,V_1 - 1\,V_2 = 3 \\
-1\,V_1 + 2\,V_2 = 0
\end{cases}
$$

Ce système s'écrit exactement sous la forme `G·x = b` :

$$
\underbrace{\begin{pmatrix} 2 & -1 \\ -1 & 2 \end{pmatrix}}_{G}
\underbrace{\begin{pmatrix} V_1 \\ V_2 \end{pmatrix}}_{x}
=
\underbrace{\begin{pmatrix} 3 \\ 0 \end{pmatrix}}_{b}
$$

Voici enfin nos trois objets en pleine lumière :

- **`G`**, la **matrice de conductance** : sur sa diagonale, la somme des conductances touchant chaque nœud ; hors diagonale, l'opposé des conductances reliant deux nœuds.
- **`x`**, le vecteur des **tensions inconnues**.
- **`b`**, le vecteur des **courants injectés** : seul `n1` reçoit la source (`3`), `n2` ne reçoit rien (`0`).

## 5.6 La révélation : ce système s'assemble tout seul

Regardez la matrice `G` ci-dessus. Sa structure n'est pas le fruit du hasard :

- Le `+2` en haut à gauche = `g₁ + g₃`, **somme** des conductances touchant `n1`.
- Le `−1` hors diagonale = `−g₁`, l'**opposé** de la conductance reliant `n1` et `n2`.

Ce sont *précisément* les « quatre marques » de la conductance : `+g` sur les diagonales, `−g` sur les croisées. La technique que le simulateur emploie — et que le chapitre 6 détaillera sous le nom de *stamping* — n'invente rien : elle **assemble automatiquement, composant par composant, exactement le système que nous venons d'écrire à la main.** La seule différence est qu'elle le fait dans n'importe quel ordre et sans jamais « comprendre » le circuit globalement.

De même, le vecteur `b` reçoit la contribution des sources de courant : la fonction `_stamp_current(b, idx_a, idx_b, current)`, que nous verrons au chapitre 6, déposera `+3` dans la ligne de `n1`. La boucle qui, dans le moteur, demande à chaque composant de se tamponner produit donc *ce* `G` et *ce* `b`, sans qu'aucun humain n'ait écrit la moindre équation.

## 5.7 Résoudre, et vérifier

Reste à trouver `V₁` et `V₂`. De la seconde équation : `V₁ = 2 V₂`. En substituant dans la première :

$$
2(2 V_2) - V_2 = 3 \;\Rightarrow\; 3 V_2 = 3 \;\Rightarrow\; V_2 = 1\ \text{V}, \quad V_1 = 2\ \text{V}.
$$

Vérifions par la physique (toujours !). Avec `V₁ = 2 V` et `V₂ = 1 V` :

- courant dans `R3` (de `n1` vers la masse) : `(2 − 0)/1 = 2 A` ;
- courant dans `R1` (de `n1` vers `n2`) : `(2 − 1)/1 = 1 A` ;
- somme sortant de `n1` : `2 + 1 = 3 A` ✓ — exactement le courant injecté par la source ;
- courant dans `R2` (de `n2` vers la masse) : `(1 − 0)/1 = 1 A`, qui est bien le courant arrivé par `R1` ✓.

Tout est équilibré. Les lois de Kirchhoff sont satisfaites en chaque nœud. Le système était correct.

## 5.8 Et la machine, comment résout-elle ?

À la main, nous avons procédé par substitution. Pour deux équations, c'est trivial ; pour cinquante, c'est inhumain. Le simulateur confie cette tâche à l'algèbre linéaire numérique, en une seule ligne ([simulator/engine.py](../../simulator/engine.py#L60-L61)) :

```python
x = np.linalg.solve(G, b)
```

C'est tout. `numpy` reçoit la matrice `G` et le vecteur `b`, et renvoie le vecteur `x` des tensions. Comment il s'y prend, et ce qui peut mal tourner (la redoutable « matrice singulière »), fera l'objet du chapitre 8.

## 5.9 À retenir

- L'**analyse nodale** : pour chaque nœud (sauf la masse), on écrit la **loi des nœuds**, en exprimant chaque courant par `I = G·U`. Les inconnues sont les **tensions de nœud**.
- On obtient un système `G·x = b` où :
  - la **diagonale** de `G` = somme des conductances touchant le nœud ;
  - le **hors-diagonale** = opposé de la conductance reliant deux nœuds ;
  - `b` = courants injectés (sources de courant).
- Ce système est **identiquement** celui que le simulateur assemble automatiquement, composant par composant, plutôt qu'à la main — la technique que formalisera le chapitre 6 (le *stamping*).
- On résout, puis on **vérifie** par les lois de Kirchhoff. Le moteur, lui, résout via `np.linalg.solve(G, b)`.

**Dans le prochain chapitre (Ch. 7)**, nous affronterons le composant que l'analyse nodale pure ne sait pas traiter : la **source de tension**. Elle nous forcera à agrandir le système avec une inconnue de courant — la **branche** entrevue au chapitre 4 — et donnera enfin son nom complet à notre méthode : la **MNA**.
