# Chapitre 1 — Les grandeurs de base : tension, courant, masse

> *Où l'on apprend que l'électricité ne se mesure jamais en un point, mais toujours entre deux, et où l'on rencontre le personnage le plus important — et le plus discret — de tout le simulateur : la masse.*

## 1.1 Une analogie pour démarrer : l'eau dans les tuyaux

Avant toute formule, installons une image mentale. Elle est imparfaite, mais elle vous accompagnera tout au long du livre.

Imaginez un réseau de tuyaux remplis d'eau.

- La **pression** de l'eau en un point, c'est la **tension** électrique (notée `V`, en **volts**). Une pression élevée « pousse » fort.
- Le **débit** d'eau qui passe dans un tuyau, c'est le **courant** électrique (noté `I`, en **ampères**). Beaucoup d'eau qui circule = courant élevé.
- Un tuyau étroit qui freine le débit, c'est une **résistance** (notée `R`, en **ohms**, symbole `Ω`). Nous y reviendrons au chapitre 3.

Cette analogie capture déjà l'essentiel : ce qui *pousse* (la tension) n'est pas la même chose que ce qui *circule* (le courant). Confondre les deux est l'erreur n°1 du débutant. Gardons-les bien distincts.

## 1.2 Le courant : un débit de charges

L'électricité, c'est le déplacement de **charges électriques** (en pratique, des électrons dans un fil de cuivre). Le **courant** mesure ce débit : combien de charges passent par seconde à travers une section du fil.

- Unité : l'**ampère** (`A`).
- Un courant a un **sens** : on choisit par convention le sens dans lequel circuleraient des charges positives. Un courant peut donc être positif ou négatif selon le sens où il va réellement.

Ce signe n'est pas un détail : tout le simulateur repose sur des conventions de signe rigoureuses. Quand vous lirez, au chapitre 11, qu'une source de courant « injecte `current` ampères du nœud `b` vers le nœud `a` », c'est précisément ce sens conventionnel qui est en jeu.

## 1.3 La tension : une différence, jamais une valeur absolue

Voici le point le plus important du chapitre, et celui que les débutants saisissent le plus mal.

> **Une tension n'existe pas en un seul point. Elle se définit toujours *entre deux points*.**

Reprenons l'eau : cela n'a aucun sens de demander « quelle est la différence de pression *ici* ? ». Une différence se mesure forcément entre deux endroits. La pression « absolue » en un point n'a de sens que par rapport à une référence (souvent : la pression atmosphérique).

En électricité, c'est identique. On parle de la tension **entre** un nœud `A` et un nœud `B`, et on la note :

$$
U_{AB} = V_A - V_B
$$

C'est une **différence de potentiel** (d'où le `U`). Le mot « potentiel » (`V_A`, `V_B`) désigne une sorte de « niveau » attribué à chaque point ; seule leur *différence* a une réalité physique mesurable.

Cette idée est inscrite partout dans le code du simulateur. Chaque composant à deux bornes connaît deux nœuds, `node_a` et `node_b`, et calcule systématiquement sa tension comme une différence. Par exemple, pour la résistance :

```python
va = _node_voltage(x, node_map, self.node_a)
vb = _node_voltage(x, node_map, self.node_b)
voltage = va - vb        # jamais une valeur seule : toujours une différence
```

Retenez ce réflexe : dès qu'on parle de tension dans ce livre, demandez-vous *« entre quels deux points ? »*.

## 1.4 La masse : la référence à zéro volt

Si toute tension est une différence, une question se pose : par rapport à **quoi** mesure-t-on les potentiels `V_A`, `V_B`, etc. ?

La réponse est une convention universelle en électronique : on choisit **un** nœud du circuit que l'on décrète être à **0 volt**, et tous les autres potentiels se mesurent par rapport à lui. Ce nœud de référence s'appelle la **masse** (en anglais *ground*), et dans notre simulateur il porte toujours le nom `GND`.

> La masse, c'est le « niveau de la mer » de votre circuit. Toutes les altitudes (les tensions) se comptent à partir d'elle.

Ce choix n'enlève rien à la généralité : seules les différences comptent, donc fixer un point à 0 V ne change aucune mesure réelle entre deux autres points. En revanche, il rend les calculs possibles, car il donne un ancrage. Sans masse, le simulateur n'aurait aucun point d'appui — et, comme nous le verrons au chapitre 8, sa matrice deviendrait **singulière** (insoluble).

Dans le moteur, ce statut spécial de `GND` se traduit très concrètement. La masse n'a pas d'équation à elle : on connaît déjà sa tension. Le code la réinjecte « à la main » après chaque résolution ([simulator/engine.py](../../simulator/engine.py#L67-L68)) :

```python
node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
node_voltages["GND"] = 0.0        # la masse : toujours 0 V, par définition
```

Nous reverrons ce personnage discret dans presque tous les chapitres. Au chapitre 6, vous avez peut-être déjà croisé son indice spécial `-1` dans la fonction de stamping : c'est la même idée — la masse n'a ni ligne ni colonne dans la matrice, car sa tension n'est pas une inconnue.

## 1.5 La puissance : quand tension et courant se rencontrent

Une dernière grandeur, pour compléter le tableau. Lorsqu'un courant `I` traverse un composant aux bornes duquel règne une tension `U`, ce composant échange une **puissance** :

$$
P = U \cdot I
$$

- Unité : le **watt** (`W`).
- C'est le rythme auquel l'énergie est fournie (par une source) ou dissipée (par exemple en chaleur dans une résistance).

La puissance ne joue pas de rôle direct dans la résolution MNA du simulateur, mais c'est elle qui explique pourquoi une résistance chauffe, pourquoi une pile se vide, et pourquoi les unités « ampère » et « volt » comptent tant en pratique. Nous la croiserons à nouveau au chapitre 9.

## 1.6 Ordres de grandeur et préfixes

L'électronique manie des nombres minuscules autant qu'énormes. Quelques préfixes reviendront sans cesse (un aide-mémoire complet figure en annexe B) :

| Préfixe | Symbole | Facteur      | Exemple courant            |
|---------|:-------:|--------------|----------------------------|
| méga    | `M`     | × 1 000 000  | `1 MΩ` (résistance élevée)  |
| kilo    | `k`     | × 1 000      | `10 kΩ`                     |
| milli   | `m`     | × 0,001      | `5 mA` (courant typique)    |
| micro   | `µ`     | × 0,000 001  | `100 µF` (condensateur)     |
| nano    | `n`     | × 10⁻⁹       | `10 nF`                     |

Vous verrez ces ordres de grandeur dans les valeurs « extrêmes » utilisées par le simulateur pour modéliser certains composants : une résistance de `1e9 Ω` (1 GΩ) pour un interrupteur ouvert, de `1e-6 Ω` (1 µΩ) pour un interrupteur fermé. Ces nombres n'ont rien d'arbitraire : ce sont des grandeurs physiques plausibles, choisies pour approcher l'« infini » et le « zéro » sans casser les calculs.

## 1.7 À retenir

- Le **courant** (`I`, ampères) est un débit de charges ; il a un **sens** conventionnel et donc un signe.
- La **tension** (`U`, volts) est *toujours* une **différence** entre deux points : `U_AB = V_A − V_B`. Jamais une valeur isolée.
- La **masse** (`GND`) est le nœud de référence, fixé à **0 V** par convention. Tout le reste se mesure par rapport à elle. Sans elle, pas de résolution possible.
- La **puissance** `P = U·I` (watts) mesure l'énergie échangée par seconde.
- L'électronique manie de très grands et très petits nombres ; les **préfixes** (`k`, `m`, `µ`, `n`…) sont indispensables.

**Dans le prochain chapitre**, nous découvrirons les deux lois qui gouvernent *tous* les circuits, sans exception : les **lois de Kirchhoff**. L'une d'elles, la loi des nœuds, est le fondement même de la matrice que construit le simulateur.
