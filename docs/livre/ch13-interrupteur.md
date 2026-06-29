# Chapitre 13 — L'interrupteur

> *Où l'on modélise le geste le plus banal de l'électricité — allumer, éteindre — et où l'on rencontre le premier composant que l'on peut actionner pendant que la simulation tourne.*

## 13.1 Un état binaire, deux résistances

Un interrupteur n'a que deux états : **ouvert** (le courant ne passe pas) ou **fermé** (le courant passe librement). Comment traduire ce « tout ou rien » dans un simulateur qui ne connaît que des conductances ?

La réponse découle directement du chapitre 3 : on n'a pas besoin d'un mécanisme spécial, juste de deux **résistances extrêmes**.

- **Fermé** : une résistance quasi nulle (`R_CLOSED = 1e-6 Ω`), donc une conductance énorme — le courant passe comme dans un fil.
- **Ouvert** : une résistance quasi infinie (`R_OPEN = 1e9 Ω`), donc une conductance négligeable — presque aucun courant ne passe.

On retrouve, là encore, le principe « un presque-infini et un presque-zéro plutôt que les véritables infini et zéro » (chapitre 3), pour éviter divisions par zéro et matrices singulières. L'interrupteur n'est donc qu'une **résistance dont la valeur bascule entre deux extrêmes**.

## 13.2 Le stamping : une résistance à valeur variable

Son code confirme cette idée — c'est le stamping d'une résistance, où seule la valeur change selon l'état ([simulator/components.py](../../simulator/components.py#L208-L219)) :

```python
R_OPEN   = 1e9     # Ω — circuit pratiquement ouvert
R_CLOSED = 1e-6    # Ω — quasi court-circuit

def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    r = self.R_CLOSED if self.closed else self.R_OPEN
    _stamp_conductance(G, idx_a, idx_b, 1.0 / r)

def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    voltage = va - vb
    r = self.R_CLOSED if self.closed else self.R_OPEN
    return {"voltage": voltage, "current": voltage / r}
```

Une seule ligne fait toute la différence : `r = self.R_CLOSED if self.closed else self.R_OPEN`. Le drapeau `self.closed` (un booléen) décide quelle conductance tamponner. Tout le reste est une résistance ordinaire.

## 13.3 La nouveauté : un état que l'on peut changer en cours de route

Jusqu'ici, tous nos composants étaient **figés** : une fois le circuit chargé, une résistance restait de `220 Ω` pour toujours. L'interrupteur introduit une idée neuve : un **état mutable**, que l'on peut basculer *pendant* que la simulation tourne ([components.py](../../simulator/components.py#L200-L203)).

```python
def toggle(self):
    """Bascule l'état de l'interrupteur."""
    self.closed = not self.closed
    self.params["closed"] = self.closed
```

`toggle()` inverse simplement le booléen `self.closed`. Mais la conséquence est profonde. Souvenez-vous (chapitre 8) que le moteur **reconstruit entièrement** la matrice à chaque pas, en redemandant à chaque composant de se tamponner. Donc, **à l'instant même où `closed` change, le pas suivant tamponnera l'autre résistance**, et le circuit se comporte aussitôt différemment. Aucun mécanisme spécial n'est nécessaire : la mutabilité « gratuite » est un cadeau de l'architecture « tout reconstruire à chaque pas ».

## 13.4 Le temps réel et la concurrence

Il y a là une subtilité que ce chapitre se contente d'annoncer, et que le chapitre 23 développera. La simulation tourne dans un **fil d'exécution** (thread) séparé, à grande cadence. L'utilisateur, lui, peut appeler `toggle()` depuis un *autre* fil (une interface, un clavier). Deux fils touchent donc au même objet « en même temps ».

Cette cohabitation exige des précautions (un **verrou**, pour éviter qu'un `toggle()` ne tombe au milieu d'un calcul de pas). L'interrupteur est ainsi notre première fenêtre sur la dimension **interactive et concurrente** du simulateur — un circuit n'est pas qu'une équation figée que l'on résout une fois, mais un système vivant avec lequel on dialogue pendant qu'il évolue.

C'est aussi pourquoi `toggle()` met à jour `self.params["closed"]` en plus de `self.closed` : le dictionnaire `params` est ce que l'interface lit pour afficher l'état courant. Garder les deux synchronisés assure que ce qu'on voit reflète ce que le moteur calcule.

## 13.5 Vers les composants à état

L'interrupteur marque une transition conceptuelle dans le livre. Jusqu'ici, un composant était une fonction pure : *mêmes tensions → même contribution*. Désormais, la contribution peut dépendre d'un **état** (`closed`). Cet état-ci est piloté de l'extérieur, par l'utilisateur.

Mais on peut imaginer un état piloté de l'**intérieur**, par le circuit lui-même et par son passé. C'est exactement ce qui nous attend :

- à la **Partie IV**, le condensateur et la bobine auront un état qui *mémorise le pas précédent* (`prev_state`) ;
- à la **Partie V**, la diode et le transistor auront un état (passant/bloqué, actif/saturé) déterminé par les tensions du pas d'avant.

L'interrupteur, avec son simple booléen, est la version la plus douce de cette idée. Il ouvre la voie aux composants dont le comportement dépend non plus seulement de l'instant présent, mais d'une **histoire**.

## 13.6 À retenir

- Un **interrupteur** se modélise par deux **résistances extrêmes** : `R_CLOSED = 1e-6 Ω` (fermé) et `R_OPEN = 1e9 Ω` (ouvert). C'est une résistance dont la valeur bascule.
- Son stamping est celui d'une résistance ; seul le booléen `self.closed` choisit la conductance.
- `toggle()` permet de changer l'état **pendant** la simulation. Comme le moteur reconstruit la matrice à chaque pas, le changement prend effet **immédiatement**, sans mécanisme dédié.
- C'est le premier composant **mutable** et **interactif** : il introduit la **concurrence** (thread de simulation vs action de l'utilisateur, → chapitre 23) et annonce les composants **à état** des parties IV et V.

**Ceci clôt la Partie III.** Vous connaissez maintenant tout le catalogue des composants « simples » : résistance, sources (et leurs formes), instruments, interrupteur. Tous partagent une caractéristique : leur comportement ne dépend que de l'instant présent (ou d'un état externe).

**La Partie IV** franchit le grand pas : le **temps** comme acteur à part entière. Comment un condensateur « se souvient-il » de sa charge ? Comment transformer une équation différentielle en un stamping ? C'est là que la simulation révèle toute sa profondeur.
