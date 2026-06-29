# Chapitre 24 — Limites et extensions

> *Où l'on dresse le bilan honnête de ce que le simulateur fait et ne fait pas, où l'on apprend à y ajouter son propre composant — et où le lecteur, devenu capable de lire et d'étendre le code, referme le livre.*

## 24.1 Ce que le simulateur fait bien

Au terme de ce livre, mesurons le chemin parcouru. Notre simulateur, en quelques centaines de lignes, accomplit des choses remarquables :

- il résout n'importe quel circuit linéaire par la **MNA** (parties II) ;
- il gère le **temps** et les composants réactifs par les modèles compagnons (partie IV) ;
- il approche des composants **non-linéaires** — diode, transistor — par linéarisation par morceaux (partie V) ;
- il tourne en **temps réel**, dans un thread, avec une interaction concurrente sûre (parties VI).

Surtout, il est **lisible**. Chaque composant tient en quelques lignes, le moteur en une centaine. C'était son but : non pas rivaliser avec les outils professionnels, mais **rendre la simulation compréhensible**. À cet égard, il réussit là où SPICE, puissant mais opaque, reste une boîte noire pour le néophyte.

## 24.2 Ce qu'il ne fait pas (et pourquoi)

L'honnêteté, fil rouge de ce livre, impose de nommer les sacrifices. Notre simulateur n'est **pas** un outil de conception professionnelle, pour des raisons assumées :

- **Pas d'itération de Newton-Raphson** (chapitre 17). Les composants non-linéaires sont décidés d'après le pas précédent, ce qui introduit un retard d'un pas et un risque d'oscillation. Un vrai simulateur itère jusqu'à convergence à *chaque* pas.

- **Intégration du premier ordre seulement** (chapitre 15). L'Euler implicite est stable mais peu précis ; les outils sérieux emploient des méthodes d'ordre supérieur (trapèze, Gear) pour une fidélité accrue à pas égal.

- **Modèles de composants idéalisés**. La diode est un interrupteur à seuil (pas l'équation exponentielle de Shockley) ; le transistor ignore la tension d'Early, la température, les courbes réelles ; l'ampli-op est parfait (gain infini, pas de saturation).

- **Pas d'analyse fréquentielle ni de point de fonctionnement**. On ne fait que de la simulation **temporelle** pas-à-pas. Pas d'analyse AC (réponse en fréquence), pas de calcul du régime continu établi (*operating point*) par résolution directe.

- **Pas d'optimisation numérique**. La matrice est **dense** (`np.zeros`), reconstruite et résolue entièrement à chaque pas. Pour de gros circuits, on utiliserait des matrices **creuses** (*sparse*) et une factorisation réutilisée entre les pas.

Aucune de ces limites n'est un défaut : ce sont des **choix** au service de la clarté et du temps réel. Les connaître, c'est savoir *quand* ce simulateur suffit et *quand* il faut un autre outil.

## 24.3 Exercice de synthèse : ajouter un composant

La meilleure preuve que vous avez compris l'architecture est de l'**étendre**. Ajouter un composant ne demande de toucher qu'à **deux endroits**, et illustre toute la puissance des abstractions du livre.

**Étape 1 — écrire la classe du composant** (dans `simulator/components.py`). Il suffit d'hériter de `Component` et d'implémenter le contrat que nous connaissons par cœur :

- `get_nodes()` : quels nœuds je relie ?
- `needs_branch()` : ai-je besoin d'une inconnue de courant ? (chapitre 7)
- `stamp(...)` : ma contribution à `G` et `b` (chapitre 6) ;
- `get_state(...)` : comment lire ma tension et mon courant après résolution.

**Étape 2 — l'enregistrer dans la fabrique** (dans `circuit_loader.py`) : ajouter un `elif comp_type == "mon_composant"` qui appelle le constructeur (chapitre 22).

Et c'est tout. Le moteur, l'état partagé, la boucle temps réel : **rien d'autre ne change**. Votre composant sera tamponné, résolu, mémorisé et publié comme les autres, gratuitement. C'est la marque d'une architecture bien pensée — *ouverte à l'extension, fermée à la modification*.

## 24.4 Une idée concrète : le potentiomètre

Pour rendre l'exercice tangible, prenons un cas réel — d'autant que le dépôt en contient justement les prémices (une spécification de *potentiomètre*). Un potentiomètre est une **résistance variable** : une résistance dont la valeur se règle, typiquement par un curseur entre 0 et une valeur maximale.

Sa conception découle directement de ce que vous savez :

- C'est, au fond, une **résistance** (chapitre 9) — donc `stamp` tamponne une simple conductance `1/R`.
- Sa valeur `R` dépend d'un paramètre réglable (la position du curseur), modifiable **en temps réel** — exactement comme l'interrupteur expose `toggle()` (chapitre 13). On ajouterait une méthode `set_position(x)` qui met à jour `R`, et le pas suivant tamponnerait la nouvelle valeur, sans aucun autre changement.

Vous voyez comme deux composants déjà étudiés — la résistance pour le *quoi*, l'interrupteur pour le *réglage en temps réel* — se combinent pour en former un troisième. C'est ainsi que se construit, par recomposition, tout un catalogue. Le potentiomètre câblé en **diviseur** (chapitre 9) donnerait même une tension de sortie réglable : un volume, une luminosité, une consigne.

## 24.5 Pour aller plus loin

Si ce livre vous a donné le goût d'approfondir, voici des directions naturelles, chacune prolongeant un chapitre :

- **Améliorer les non-linéarités** : implémenter une vraie boucle de Newton-Raphson (chapitre 17) et comparer la précision aux transitions.
- **Monter en ordre d'intégration** : remplacer Euler implicite par la méthode du trapèze (chapitre 15) et observer le gain de fidélité.
- **Enrichir les modèles** : diode de Shockley, transistor avec effet d'Early (chapitres 18-19).
- **Optimiser** : passer aux matrices creuses pour simuler de grands circuits (chapitre 8).
- **Ajouter des analyses** : un mode « point de fonctionnement » (résolution directe en continu) ou une analyse fréquentielle.

Chacune est un projet en soi — et, grâce à l'architecture modulaire, chacune peut être tentée **isolément**, sans réécrire le reste.

## 24.6 Le mot de la fin

Vous avez ouvert ce livre en néophyte de l'électronique. Vous le refermez capable de **lire**, de **comprendre** et d'**étendre** un simulateur de circuits complet. Vous savez ce qu'est une tension, comment Kirchhoff gouverne un circuit, pourquoi une matrice résout un réseau, comment le temps se discrétise, et comment une diode ou un transistor se ramène à des briques élémentaires.

Mais surtout, vous avez vu une idée se déployer du début à la fin : *un simulateur ne comprend pas l'électronique — il la traduit en équations qu'une machine sait résoudre.* De la loi des nœuds (chapitre 2) au stamping (chapitre 6), des modèles compagnons (chapitre 16) à la boucle temps réel (chapitre 21), c'est toujours la même démarche : **réduire la physique à de l'algèbre, pas à pas**.

Cette démarche dépasse de loin les circuits. C'est l'essence de toute simulation — et, peut-être, de toute compréhension : décomposer le complexe en éléments simples, dont l'assemblage reconstitue le tout. Le circuit n'était qu'un prétexte. La vraie leçon est cette manière de penser.

## 24.7 À retenir

- Le simulateur excelle par sa **lisibilité** et son fonctionnement **temps réel** ; il n'est pas un outil de conception **professionnel**.
- Ses **limites assumées** : pas d'itération Newton-Raphson, intégration du 1er ordre, modèles idéalisés, pas d'analyse AC/point de fonctionnement, matrice dense non optimisée.
- **Étendre** le simulateur ne touche que **deux endroits** : la classe du composant (`stamp`, `get_state`, `get_nodes`, `needs_branch`) et la fabrique du chargeur. Le reste fonctionne **gratuitement** — architecture *ouverte à l'extension, fermée à la modification*.
- Exemple concret : le **potentiomètre** = une résistance (chapitre 9) + un réglage temps réel (chapitre 13).
- La leçon centrale du livre : *un simulateur traduit la physique en algèbre*. Cette démarche de décomposition dépasse l'électronique.

**Fin.** Les annexes qui suivent rassemblent les rappels mathématiques, les unités, le formulaire de stamping et le glossaire — vos compagnons de relecture.
