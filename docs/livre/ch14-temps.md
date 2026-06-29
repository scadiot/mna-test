# Chapitre 14 — Pourquoi le temps change tout

> *Où l'on rencontre deux composants qui ne réagissent pas à ce qui est, mais à ce qui change — et où l'on comprend que pour les simuler, il faudra leur donner une mémoire.*

## 14.1 Des composants qui ont une mémoire

Jusqu'à présent, tous nos composants étaient **sans mémoire**. Une résistance soumise à 3 V laisse passer le même courant, qu'on vienne de la brancher ou qu'elle soit là depuis une heure. Son présent ne dépend pas de son passé. C'est ce qui rendait chaque pas de simulation indépendant des autres (chapitre 8).

Le **condensateur** et la **bobine** brisent cette indépendance. Ce sont des composants **réactifs** : leur comportement à l'instant présent dépend de leur **histoire**. Ils stockent de l'énergie — l'un sous forme de champ électrique, l'autre sous forme de champ magnétique — et cette énergie accumulée influence ce qu'ils font ensuite. Pour les simuler, il faudra donc, pour la première fois, qu'un composant **se souvienne** du pas précédent.

C'est la rupture conceptuelle de tout le livre. Préparons-la en comprenant *physiquement* ces deux composants.

## 14.2 Le condensateur : un réservoir de charge

Un condensateur est, dans sa version la plus simple, deux plaques métalliques séparées par un isolant. On ne peut pas faire passer un courant continu « à travers » (l'isolant bloque), mais on peut **accumuler des charges** sur les plaques. Plus on accumule de charge `Q`, plus la tension `U` à ses bornes monte, proportionnellement :

$$
Q = C \cdot U
$$

`C` est la **capacité**, en **farads** (F). Elle mesure « combien de charge le condensateur stocke par volt ».

Ce qui nous intéresse, c'est le **courant**. Or le courant est un débit de charges (chapitre 1) : c'est la vitesse à laquelle `Q` change. En dérivant la relation `Q = C·U` par rapport au temps, on obtient la loi fondamentale du condensateur :

$$
\boxed{\,i(t) = C \cdot \frac{dv}{dt}\,}
$$

Lisez bien cette formule, car elle est déroutante : **le courant ne dépend pas de la tension, mais de sa *variation*.**

- Si la tension est constante (`dv/dt = 0`), le courant est **nul** : un condensateur chargé et stable bloque le courant continu.
- Si la tension change vite, le courant est grand.

C'est pour cela qu'un condensateur « lisse » les variations : il absorbe du courant quand la tension veut monter, en restitue quand elle veut descendre. Il s'oppose aux *changements* de tension.

## 14.3 La bobine : un réservoir de courant

La bobine (ou inductance) est un fil enroulé. Elle stocke de l'énergie dans le **champ magnétique** créé par le courant qui la traverse. Son comportement est le **dual** exact de celui du condensateur (vous commencez à reconnaître ces dualités, chapitre 11) :

$$
\boxed{\,v(t) = L \cdot \frac{di}{dt}\,}
$$

`L` est l'**inductance**, en **henrys** (H). Cette fois, c'est la **tension** qui dépend de la *variation* du **courant** :

- Si le courant est constant (`di/dt = 0`), la tension est **nulle** : une bobine parcourue par un courant stable se comporte comme un simple fil.
- Si l'on tente de changer brutalement le courant, la bobine génère une forte tension qui s'y oppose.

Là où le condensateur s'oppose aux changements de **tension**, la bobine s'oppose aux changements de **courant**. Deux gardiens de l'inertie, chacun dans son registre.

## 14.4 Le problème pour le simulateur : la dérivée

Voici la difficulté. Notre moteur sait résoudre `G·x = b`, un système **algébrique** : des multiplications et des additions de nombres. Mais les lois ci-dessus contiennent une **dérivée**, `dv/dt` ou `di/dt`. Une dérivée n'est pas une opération algébrique : c'est une notion de *calcul infinitésimal*, qui parle de variation instantanée.

On ne peut pas « tamponner une dérivée » dans une matrice de nombres. Il y a une incompatibilité fondamentale entre :

- la **physique** de ces composants, qui est **différentielle** (elle parle de taux de variation continus) ;
- la **machinerie** du simulateur, qui est **algébrique** (elle manipule des nombres figés à un instant donné).

Tout l'enjeu des deux prochains chapitres est de **construire un pont** entre ces deux mondes. Ce pont a deux piliers :

1. **La discrétisation du temps** (chapitre 15) : remplacer la dérivée continue par une différence entre deux instants proches. C'est ce qui transformera `dv/dt` en quelque chose de calculable.
2. **Le modèle compagnon** (chapitre 16) : une fois la dérivée discrétisée, déguiser le condensateur et la bobine en composants que l'on sait déjà tamponner — une conductance et une source de courant.

## 14.5 Pourquoi il faudra une mémoire

Anticipons la clé. Une dérivée `dv/dt` compare la valeur **maintenant** à la valeur **juste avant**. Pour la calculer, le simulateur devra donc connaître la tension (ou le courant) du **pas précédent**. C'est exactement le rôle du `prev_state` que vous avez croisé dans toutes les signatures de `stamp` depuis le chapitre 6 — un paramètre resté inutilisé jusqu'ici par les composants sans mémoire.

Le moteur conserve cet historique dans un dictionnaire, initialisé à zéro au démarrage ([simulator/engine.py](../../simulator/engine.py#L27-L28)) :

```python
# État précédent de chaque composant pour les modèles compagnons
self._prev_states = {c.id: {"voltage": 0.0, "current": 0.0} for c in self._components}
```

Ce simple dictionnaire est la **mémoire** du simulateur. Chaque condensateur y retrouvera, au pas suivant, la tension qu'il avait au pas d'avant ; chaque bobine, le courant qu'elle portait. C'est ce fil ténu entre deux instants qui va permettre à un système algébrique de simuler une physique différentielle.

## 14.6 À retenir

- Le **condensateur** et la **bobine** sont des composants **réactifs** : ils stockent de l'énergie et leur comportement dépend de leur **histoire**, pas seulement de l'instant présent.
- Condensateur : `i = C·dv/dt`. Le courant dépend de la **variation** de tension. Tension stable → courant nul. Il s'oppose aux changements de **tension**.
- Bobine : `v = L·di/dt` (le dual). La tension dépend de la **variation** de courant. Courant stable → tension nulle. Elle s'oppose aux changements de **courant**.
- Problème : ces lois sont **différentielles** (une dérivée), mais le simulateur est **algébrique**. Il faut un pont.
- Ce pont exigera une **mémoire** : le `prev_state` (et le dictionnaire `_prev_states` du moteur), enfin mis à profit.

**Dans le prochain chapitre**, nous bâtirons le premier pilier du pont : la **discrétisation du temps**. Nous verrons comment remplacer une dérivée continue par une simple soustraction entre deux pas — et pourquoi le choix de la méthode (Euler *implicite*) est crucial pour la stabilité.
