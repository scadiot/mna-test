# Chapitre 2 — Les lois de Kirchhoff

> *Où l'on découvre les deux règles, presque évidentes, qui suffisent à décrire n'importe quel circuit — et où l'on apprend laquelle des deux est le moteur secret du simulateur.*

## 2.1 Deux principes de bon sens

Au XIXᵉ siècle, Gustav Kirchhoff a énoncé deux lois qui, ensemble, gouvernent tous les circuits électriques, du plus simple au plus complexe. Leur force tient à leur généralité : elles ne dépendent ni du type de composant, ni de la forme du circuit. Elles découlent de deux principes de conservation que vous connaissez intuitivement.

- **La loi des nœuds** traduit la *conservation de la charge* : rien ne s'accumule, ce qui entre doit ressortir.
- **La loi des mailles** traduit la *conservation de l'énergie* : on revient toujours à son point de départ avec le même « niveau ».

Étudions-les l'une après l'autre.

## 2.2 La loi des nœuds (KCL) : tout ce qui entre doit sortir

Un **nœud** est un point de connexion où se rejoignent plusieurs fils. La **loi des nœuds** (en anglais *Kirchhoff's Current Law*, KCL) affirme :

> **En tout nœud, la somme des courants qui entrent est égale à la somme des courants qui sortent.**

Reprenons l'analogie de l'eau du chapitre 1. À un raccord en T où trois tuyaux se rejoignent, toute l'eau qui arrive doit repartir : elle ne peut ni s'accumuler ni disparaître au raccord. Le débit total entrant égale le débit total sortant. La charge électrique obéit à la même règle : un nœud ne stocke rien.

On l'écrit souvent sous une forme compacte, en comptant *positivement* les courants entrants et *négativement* les sortants :

$$
\sum_{k} I_k = 0 \quad \text{(en un nœud donné)}
$$

### Un exemple chiffré

Soit un nœud où arrivent deux courants, `I₁ = 3 A` et `I₂ = 2 A`, et d'où repart un courant `I₃`. La loi des nœuds impose :

$$
I_1 + I_2 = I_3 \quad\Rightarrow\quad I_3 = 5\ \text{A}.
$$

Pas de mystère : les 5 ampères entrants ressortent intégralement. Cette banalité apparente est, nous allons le voir, d'une puissance redoutable.

## 2.3 Pourquoi la KCL est le cœur du simulateur

Voici le lien central de tout le livre, que je vous demande de mémoriser :

> **Le simulateur écrit une équation « loi des nœuds » pour chaque nœud du circuit. Ces équations, mises ensemble, *sont* la matrice `G`.**

Chaque ligne de la matrice `G` que construira le simulateur n'est rien d'autre qu'une loi des nœuds en un point. Quand un composant viendra y déposer sa contribution — on dira qu'il la « tamponne » —, il ne fera qu'ajouter sa part de courant dans les équations KCL des nœuds qu'il touche.

C'est pourquoi la masse est exclue de la matrice (chapitre 1) : on n'écrit pas d'équation des nœuds pour elle. Elle absorbe ou fournit librement le courant nécessaire pour que tous les *autres* nœuds soient équilibrés — elle est le « puits » qui referme le bilan.

Nous construirons ces équations pas à pas au chapitre 5. Pour l'instant, retenez simplement la correspondance :

```
une ligne de la matrice  ⟷  la loi des nœuds en un point
```

## 2.4 La loi des mailles (KVL) : on revient toujours à son point de départ

La seconde loi concerne non plus les nœuds, mais les **mailles** : les boucles fermées que l'on peut tracer dans un circuit. La **loi des mailles** (en anglais *Kirchhoff's Voltage Law*, KVL) affirme :

> **Le long de toute boucle fermée, la somme des tensions est nulle.**

$$
\sum_{k} U_k = 0 \quad \text{(le long d'une maille)}
$$

L'image juste est celle d'une randonnée en montagne : si vous partez d'un point, parcourez un sentier en boucle et revenez exactement à votre point de départ, la somme de toutes vos montées et descentes est forcément nulle — vous êtes revenu à la même altitude. Les potentiels électriques se comportent comme des altitudes : une boucle fermée ramène au même potentiel, donc le bilan des différences de tension le long de la boucle est zéro.

### Un exemple chiffré

Une pile de `9 V` alimente deux résistances en série. La pile « monte » le potentiel de 9 V ; les deux résistances doivent ensemble « redescendre » ces mêmes 9 V. Si la première dissipe `U₁ = 6 V`, alors la KVL impose pour la seconde :

$$
9 = U_1 + U_2 \quad\Rightarrow\quad U_2 = 3\ \text{V}.
$$

C'est le principe du **diviseur de tension**, que nous retrouverons en pratique au chapitre 5.

## 2.5 Deux lois, deux stratégies de simulation

Les deux lois sont vraies en même temps, mais un simulateur doit *choisir* laquelle placer au centre de ses calculs. Le nôtre est bâti sur la **loi des nœuds** : ses inconnues principales sont les *tensions de nœud*, et ses équations sont des bilans de courant. C'est l'**analyse nodale**, le sujet du chapitre 5.

La loi des mailles n'est pas oubliée pour autant. Elle réapparaît dès qu'un composant impose directement une tension — typiquement une source de tension, qui dit « entre mes deux bornes, la différence *vaut* telle valeur ». Cette contrainte de type « tension imposée » est exactement ce qui obligera, au chapitre 7, à enrichir la méthode nodale pour donner la **MNA** (analyse nodale modifiée). On y verra le code écrire littéralement la ligne :

$$
V_{\text{pos}} - V_{\text{neg}} = \text{tension de la source}
$$

qui n'est rien d'autre qu'une loi des mailles élémentaire imposée au solveur.

## 2.6 À retenir

- La **loi des nœuds (KCL)** : en tout nœud, somme des courants entrants = somme des courants sortants (`Σ I = 0`). Elle exprime la conservation de la charge.
- La **loi des mailles (KVL)** : le long de toute boucle fermée, la somme des tensions est nulle (`Σ U = 0`). Elle exprime la conservation de l'énergie.
- Notre simulateur est bâti sur la **KCL** : **chaque ligne de la matrice `G` est la loi des nœuds en un point**. C'est le concept à ne jamais perdre de vue.
- La masse est exclue de la matrice parce qu'on n'écrit pas d'équation des nœuds pour elle : elle referme le bilan de courant des autres nœuds.
- La **KVL** ressurgira au chapitre 7 pour gérer les composants qui *imposent* une tension (les sources), donnant naissance à la MNA.

**Dans le prochain chapitre**, nous comblerons le chaînon manquant entre tension et courant : la **loi d'Ohm**. Nous découvrirons pourquoi le simulateur ne raisonne presque jamais en résistances, mais en **conductances** — et pourquoi ce simple renversement rend toute la méthode possible.
