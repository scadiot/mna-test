# Chapitre 15 — La discrétisation du temps

> *Où l'on remplace une dérivée — objet du calcul infinitésimal — par une simple soustraction, et où l'on découvre que le choix du « quand » mesurer la pente n'est pas un détail, mais une question de survie numérique.*

## 15.1 Le temps en petits pas

Le monde physique est **continu** : le temps s'écoule sans à-coups, et la tension d'un condensateur varie de façon lisse. Un ordinateur, lui, ne sait procéder que par **étapes discrètes**. Notre simulateur n'évalue donc pas le circuit « à tout instant », mais à une suite d'instants régulièrement espacés :

$$
t_0 = 0, \quad t_1 = dt, \quad t_2 = 2\,dt, \quad \dots
$$

Le paramètre `dt` (lu dans `circuit.dt`) est le **pas de temps** : l'intervalle entre deux évaluations. C'est la « cadence » du simulateur. Plus `dt` est petit, plus la simulation est fidèle au continu — mais plus il faut de pas pour couvrir la même durée. C'est un compromis entre précision et coût de calcul, thème récurrent de la simulation numérique.

## 15.2 Approcher une dérivée par une différence

Reprenons le problème du chapitre 14 : la loi du condensateur contient `dv/dt`, une dérivée. Que *signifie* cette dérivée ? C'est la **pente** de la courbe de tension : à quelle vitesse `v` change à un instant donné.

L'idée de la discrétisation est de remplacer cette pente *instantanée* par une pente *moyenne* mesurée sur un petit intervalle `dt`. Géométriquement, on remplace la tangente à la courbe par la corde entre deux points proches :

$$
\frac{dv}{dt} \;\approx\; \frac{v(t) - v(t - dt)}{dt}
$$

Le numérateur est une simple **soustraction** : la valeur maintenant moins la valeur au pas précédent. Le dénominateur est notre pas `dt`. Voilà la magie : une dérivée, objet abstrait du calcul, devient une opération arithmétique élémentaire — *à condition de connaître la valeur précédente* (d'où la mémoire du chapitre 14).

Cette technique porte un nom : les **différences finies**. Plus `dt` est petit, meilleure est l'approximation, car la corde épouse mieux la tangente.

## 15.3 Un choix lourd de conséquences : où mesure-t-on la pente ?

Voici une subtilité que les débutants sous-estiment, et qui sépare les simulateurs robustes des simulateurs instables.

Notre approximation `(v(t) − v(t−dt))/dt` est la pente *entre* deux instants. Mais à *quel* instant cette pente correspond-elle, dans la loi du composant ? On a le choix, et ce choix définit la **méthode d'intégration** :

- **Euler explicite** : on évalue la loi du composant à l'instant **précédent** `t − dt`. La nouvelle valeur se calcule alors *uniquement* à partir du passé connu. C'est simple… mais réputé **instable** : avec un `dt` un peu trop grand, les erreurs s'amplifient à chaque pas et la simulation **explose** en oscillations divergentes.

- **Euler implicite** (ou *backward Euler*) : on évalue la loi à l'instant **courant** `t`. La nouvelle valeur apparaît alors des **deux côtés** de l'équation — d'où le nom « implicite » : elle est définie *implicitement*, et il faut résoudre une équation pour l'isoler. C'est un peu plus de travail, mais cette méthode est **inconditionnellement stable** : elle ne diverge jamais, quel que soit `dt`.

Notre simulateur choisit, sans hésiter, **Euler implicite**. Pour un simulateur en temps réel qui doit rester robuste quoi qu'il arrive, la stabilité prime sur la simplicité. Mieux vaut une légère erreur d'amplitude qu'une explosion numérique.

## 15.4 Pourquoi l'implicite est-il stable ? (intuition)

Sans formalisme, voici l'intuition. Euler **explicite** calcule le prochain pas en extrapolant la pente *actuelle* vers l'avant — comme conduire en ne regardant que dans le rétroviseur. Si la situation change vite, on sur-corrige, puis on sur-corrige dans l'autre sens, et l'oscillation enfle.

Euler **implicite** exige que la pente utilisée soit cohérente avec la valeur *d'arrivée* — comme si l'on demandait : *« quelle valeur future serait cohérente avec sa propre pente ? »*. Cette auto-cohérence agit comme un frein : le système est forcé de converger vers un état stable au lieu de s'emballer. C'est ce frein intrinsèque qui empêche la divergence.

> Le prix à payer — la valeur inconnue des deux côtés de l'équation — n'en est pas vraiment un pour nous. Car notre moteur **résout déjà un système** `G·x = b` à chaque pas (chapitre 8) ! Glisser une inconnue de plus dans ce système est exactement ce qu'il sait faire. L'implicite s'intègre donc *gratuitement* dans la MNA.

## 15.5 Application au condensateur

Appliquons Euler implicite à la loi du condensateur, `i = C·dv/dt`. On remplace la dérivée par la différence finie, en évaluant à l'instant courant `t` :

$$
i(t) = C \cdot \frac{v(t) - v(t - dt)}{dt}
$$

Développons :

$$
i(t) = \frac{C}{dt}\,v(t) \;-\; \frac{C}{dt}\,v(t - dt)
$$

Posons `g_eq = C/dt`. La loi devient :

$$
\boxed{\,i(t) = g_{eq}\, v(t) \;-\; g_{eq}\, v_{\text{prev}}\,}
$$

Regardez ce résultat de près, car il est extraordinaire. La loi du condensateur — qui était une *équation différentielle* — est devenue une **équation algébrique linéaire** reliant le courant `i(t)` à la tension `v(t)` ! Le terme `g_eq·v(t)` ressemble exactement à une loi d'Ohm `I = G·U` (une conductance). Et le terme `g_eq·v_prev`, qui ne dépend que du passé *connu*, est une simple constante : une source de courant.

## 15.6 Application à la bobine

Même recette pour la bobine, `v = L·di/dt` :

$$
v(t) = L \cdot \frac{i(t) - i(t - dt)}{dt}
$$

En isolant cette fois le **courant** (car c'est lui l'inconnue utile pour la loi des nœuds) :

$$
\boxed{\,i(t) = \frac{dt}{L}\, v(t) \;+\; i_{\text{prev}}\,}
$$

Avec `g_eq = dt/L`. Même structure : une conductance (`g_eq·v(t)`) plus un terme issu du passé (`i_prev`). Notez la dualité parfaite avec le condensateur : pour le condensateur, `g_eq = C/dt` et le terme mémoire est une *tension* précédente ; pour la bobine, `g_eq = dt/L` et le terme mémoire est un *courant* précédent.

## 15.7 À retenir

- Le simulateur évalue le circuit à des instants discrets espacés de `dt`, le **pas de temps**. Petit `dt` = plus précis mais plus coûteux.
- Une **dérivée** se remplace par une **différence finie** : `dv/dt ≈ (v(t) − v(t−dt))/dt`. C'est une soustraction — d'où le besoin de mémoriser le pas précédent.
- Le choix de l'instant où l'on évalue la loi définit la **méthode** : l'**Euler explicite** (passé seul) est instable ; l'**Euler implicite** (instant courant) est **inconditionnellement stable**. Notre moteur choisit l'**implicite**.
- L'implicite met l'inconnue des deux côtés — mais comme le moteur résout déjà un système, cela s'intègre **gratuitement**.
- Résultat capital : la loi différentielle devient **algébrique** :
  - condensateur : `i(t) = g_eq·v(t) − g_eq·v_prev`, avec `g_eq = C/dt` ;
  - bobine : `i(t) = g_eq·v(t) + i_prev`, avec `g_eq = dt/L`.

**Dans le prochain chapitre**, nous franchirons la dernière marche : reconnaître, dans ces deux équations, **une conductance en parallèle avec une source de courant**. C'est le **modèle compagnon** — et il nous permettra de tamponner condensateur et bobine avec des outils que nous possédons déjà depuis le chapitre 6.
