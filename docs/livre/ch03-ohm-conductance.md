# Chapitre 3 — La loi d'Ohm et la conductance

> *Où l'on relie enfin la tension au courant par une formule de trois lettres — puis où l'on la retourne comme un gant pour découvrir la grandeur que le simulateur préfère à toutes : la conductance.*

## 3.1 La loi d'Ohm : le pont entre tension et courant

Aux chapitres 1 et 2, nous avons manié séparément la tension (ce qui pousse) et le courant (ce qui circule). La **loi d'Ohm** établit le lien entre les deux, pour le composant le plus fondamental de l'électronique : la **résistance**.

> Aux bornes d'une résistance, la tension est proportionnelle au courant qui la traverse.

$$
U = R \cdot I
$$

- `U` est la tension aux bornes (en volts),
- `I` le courant qui la traverse (en ampères),
- `R` la **résistance** (en ohms, `Ω`), qui est la constante de proportionnalité.

Plus `R` est grande, plus il faut « pousser » fort (tension élevée) pour faire passer un courant donné. Dans l'analogie de l'eau : un tuyau étroit (grande résistance) exige une forte pression pour laisser passer le même débit qu'un tuyau large.

### Un exemple chiffré

Une résistance de `R = 220 Ω` est soumise à une tension de `U = 5 V`. Quel courant la traverse ? On réarrange la loi d'Ohm :

$$
I = \frac{U}{R} = \frac{5}{220} \approx 0{,}0227\ \text{A} = 22{,}7\ \text{mA}.
$$

(Remarquez le préfixe `milli` du chapitre 1 : les courants se comptent souvent en milliampères.)

## 3.2 Le renversement décisif : la conductance

La loi d'Ohm s'écrit naturellement « tension = résistance × courant ». Mais réfléchissons à ce que veut *réellement* faire le simulateur.

Au chapitre 2, nous avons établi que chaque équation du simulateur est une **loi des nœuds** : un bilan de **courants**. Le solveur cherche les **tensions** de nœud (les inconnues `x`). Il lui faut donc, pour chaque composant, une relation de la forme *« quel courant en fonction des tensions ? »* — et non l'inverse.

Retournons donc la loi d'Ohm pour exprimer le courant :

$$
I = \frac{1}{R} \cdot U
$$

On pose alors la grandeur clé :

$$
G = \frac{1}{R} \qquad \text{(la \textbf{conductance})}
$$

ce qui donne la forme que le simulateur adore :

$$
\boxed{\,I = G \cdot U\,}
$$

- `G` est la **conductance**, en **siemens** (`S`). Elle mesure la *facilité* avec laquelle le courant passe, là où la résistance mesurait la *difficulté*. Ce sont deux façons de dire la même chose : `G = 1/R`.
- Une grande conductance = un bon passage (faible résistance). Une conductance nulle = un circuit ouvert (résistance infinie).

### Pourquoi ce renversement change tout

La forme `I = G·U` est *linéaire* et *additive* : le courant est simplement la tension multipliée par un nombre. C'est exactement ce qu'il faut pour remplir une matrice, où chaque case est un coefficient qui multiplie une tension. C'est pour cette raison — et nous le verrons concrètement — que le simulateur stocke partout des **conductances**, jamais des résistances.

## 3.3 Conductances en parallèle : pourquoi elles s'additionnent

Un bénéfice immédiat de raisonner en conductances : leur comportement en parallèle est d'une simplicité parfaite.

Si deux composants relient les *mêmes* deux nœuds (ils sont « en parallèle »), ils subissent la même tension `U`. Leurs courants s'ajoutent (loi des nœuds !) :

$$
I_{\text{total}} = G_1 U + G_2 U = (G_1 + G_2)\,U.
$$

Autrement dit, **les conductances en parallèle s'additionnent** : `G_total = G₁ + G₂`. (En résistances, la formule serait l'inverse de la somme des inverses — bien plus pénible.)

Ce n'est pas une curiosité théorique : c'est *exactement* ce qui se produit dans la matrice du simulateur. Au chapitre 6, nous verrons que tamponner une conductance revient à faire `G[i,i] += g`. Si deux composants touchent le même nœud `i`, leurs conductances s'**additionnent** dans la même case grâce au `+=`. Cette mécanique d'assemblage n'est donc rien d'autre que la traduction directe de cette propriété d'addition.

## 3.4 La conductance dans le code

Ouvrons le simulateur. Chaque fois qu'un composant se comporte comme une résistance, il convertit immédiatement sa résistance en conductance par `1.0 / R` avant de la tamponner. C'est visible dès la résistance elle-même ([simulator/components.py](../../simulator/components.py#L100-L103)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    _stamp_conductance(G, idx_a, idx_b, 1.0 / self.resistance)   # R → G = 1/R
```

Le même réflexe s'applique aux composants qui *imitent* une résistance avec des valeurs extrêmes. L'interrupteur, par exemple, ne stocke pas « ouvert/fermé » sous forme abstraite : il choisit une résistance énorme ou minuscule, puis la convertit en conductance ([simulator/components.py](../../simulator/components.py#L208-L212)) :

```python
r = self.R_CLOSED if self.closed else self.R_OPEN   # 1e-6 Ω  ou  1e9 Ω
_stamp_conductance(G, idx_a, idx_b, 1.0 / r)
```

- Fermé : `R = 1e-6 Ω` → `G = 1e6 S`, une conductance énorme : le courant passe presque librement (quasi court-circuit).
- Ouvert : `R = 1e9 Ω` → `G = 1e-9 S`, une conductance quasi nulle : presque aucun courant ne passe.

On retrouve la même idée pour le voltmètre (conductance minuscule `1e-9 S`, pour « voir sans perturber ») et, plus subtilement, pour la diode et le transistor, qui basculent entre une conductance forte et une conductance faible selon leur état. Tous parlent la même langue : celle de la conductance.

## 3.5 Une mise en garde : la résistance nulle et la résistance infinie

Pourquoi le simulateur utilise-t-il `1e-6 Ω` et `1e9 Ω` plutôt que `0 Ω` et `∞ Ω` ? Parce que la conversion `G = 1/R` interdit les deux extrêmes :

- `R = 0` (court-circuit parfait) donnerait `G = 1/0`, une division par zéro.
- `R = ∞` (circuit parfaitement ouvert) donnerait `G = 0`, ce qui peut « débrancher » un nœud et rendre la matrice **singulière** (insoluble — chapitre 8).

La parade est partout la même dans le code : approcher ces idéaux par des valeurs très grandes ou très petites mais *finies et non nulles*. C'est un thème récurrent de la simulation numérique — on remplace les infinis de la physique par des nombres extrêmes que l'arithmétique sait manipuler.

## 3.6 À retenir

- La **loi d'Ohm** relie tension et courant dans une résistance : `U = R·I`.
- Le simulateur la **retourne** en `I = G·U`, où `G = 1/R` est la **conductance** (en siemens). Cette forme « courant en fonction de la tension » est celle qui remplit la matrice.
- **Les conductances en parallèle s'additionnent** (`G_total = G₁ + G₂`) — propriété que l'assemblage de la matrice traduit directement par le `+=` dans une même case.
- Dans le code, toute résistance est convertie en conductance par `1.0 / R` avant d'être tamponnée. Les états « ouvert » / « fermé » sont modélisés par des résistances **extrêmes mais finies** (`1e9 Ω`, `1e-6 Ω`) pour éviter divisions par zéro et matrices singulières.

**Ceci clôt la Partie I.** Vous disposez maintenant des trois piliers physiques : les **grandeurs** (tension, courant, masse), les **lois** (Kirchhoff), et la **relation** qui les unit (Ohm, vue à travers la conductance).

**Dans la Partie II**, nous allons assembler ces pièces pour construire, pas à pas, le système d'équations `G·x = b` — d'abord en modélisant le circuit comme un graphe (chapitre 4), puis en écrivant les équations à la main (chapitre 5), avant de découvrir, au chapitre 6, comment le simulateur assemble ce système automatiquement, composant par composant : une technique nommée *stamping*.
