# Chapitre 12 — Les instruments : voltmètre et ampèremètre

> *Où l'on apprend à mesurer sans perturber, où l'on comprend pourquoi un voltmètre se branche en parallèle et un ampèremètre en série — et où l'on découvre qu'un bon instrument n'est qu'un composant déjà connu, poussé à l'extrême.*

## 12.1 Le dilemme de toute mesure

Mesurer une grandeur, c'est s'immiscer dans le circuit. Le défi est donc : *comment lire une valeur sans la fausser par sa propre présence ?* Les deux instruments de notre simulateur répondent à cette question de deux manières opposées, qui découlent directement de la dualité du chapitre 11.

- Le **voltmètre** mesure une **tension** (une différence de potentiel). Il doit se brancher **en parallèle** de ce qu'on observe, et ne **laisser passer aucun courant** — sinon il dévierait du courant et fausserait le circuit.
- L'**ampèremètre** mesure un **courant**. Il doit se brancher **en série** (sur le chemin du courant), et ne **présenter aucune tension** — sinon il ajouterait une chute de tension parasite.

Idéalement : un voltmètre est une **résistance infinie** (il ne prélève rien), un ampèremètre une **résistance nulle** (il ne s'oppose à rien). Nous savons depuis le chapitre 3 que le simulateur approche ces idéaux par des valeurs extrêmes mais finies.

## 12.2 Le voltmètre : une résistance quasi infinie

Le voltmètre est, électriquement, une résistance gigantesque (`1 GΩ`), donc une conductance minuscule. Son stamping est celui d'une résistance ordinaire, avec une valeur volontairement négligeable ([simulator/components.py](../../simulator/components.py#L247-L257)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    # 1e9 Ω → conductance 1e-9 S, pratiquement invisible pour le circuit
    _stamp_conductance(G, idx_a, idx_b, 1e-9)

def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    voltage = va - vb
    return {"voltage": voltage, "current": voltage * 1e-9}
```

Sa conductance de `1e-9 S` est si faible que le courant qu'il prélève est négligeable : il « voit sans toucher ». Et nous avons découvert au chapitre 8 un bonus inattendu : cette conductance minuscule, en reliant ses deux nœuds, les **ancre** légèrement — ce qui aide à éviter les nœuds flottants et les matrices singulières. Le voltmètre est donc presque invisible, mais pas *tout à fait* — et c'est tant mieux.

## 12.3 L'ampèremètre : une source de tension de 0 V

L'ampèremètre est plus subtil. Pour mesurer le courant qui passe, il faut **être sur son chemin** — donc se placer en série, en coupant un fil en deux nœuds. Mais comment lire un courant ? Souvenez-vous du chapitre 7 : en MNA, le courant d'une branche **est une inconnue directement disponible** dans la solution.

L'astuce est donc géniale de simplicité : on modélise l'ampèremètre comme une **source de tension de 0 volt**. Un court-circuit idéal (aucune chute de tension, donc aucune perturbation), mais qui — étant une source de tension — possède une **branche** dont l'inconnue *est précisément le courant recherché* ([components.py](../../simulator/components.py#L289-L305)) :

```python
def needs_branch(self):
    return True

def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    branch = branch_map[self.id]
    # Contrainte : V_a - V_b = 0 (ligne de branche)
    if idx_a >= 0:
        G[branch, idx_a] += 1.0
        G[idx_a, branch] += 1.0
    if idx_b >= 0:
        G[branch, idx_b] -= 1.0
        G[idx_b, branch] -= 1.0
    b[branch] = 0.0          # tension imposée = 0 V

def get_state(self, x, node_map, branch_map):
    branch = branch_map[self.id]
    current = x[branch]      # courant mesuré = inconnue de branche
    return {"voltage": 0.0, "current": current}
```

Comparez ce stamping à celui de la source de tension (chapitre 7) : c'est **rigoureusement le même**, à ceci près que `b[branch] = 0.0` au lieu de la tension d'une pile. La mesure du courant ne coûte donc *rien de plus* : elle est offerte par la structure même de la MNA. Lire `x[branch]`, et c'est fait.

## 12.4 Pourquoi parallèle pour l'un, série pour l'autre

Résumons cette différence fondamentale, qui n'est pas une convention arbitraire mais une nécessité physique :

- Le **voltmètre** mesure la tension *entre* deux points : il se place **en parallèle**, et doit laisser passer le moins de courant possible (→ résistance maximale).
- L'**ampèremètre** mesure le courant *qui traverse* : il se place **en série** (on coupe le fil), et doit présenter le moins de tension possible (→ résistance minimale).

Brancher un ampèremètre en parallèle d'une source créerait un quasi-court-circuit (danger réel sur un vrai banc !) ; brancher un voltmètre en série interromprait le courant. Le simulateur, lui, ne risque pas l'accident, mais respecte exactement la même logique de placement.

## 12.5 Les instruments ont une mémoire : l'historique

Une différence essentielle sépare ces deux composants des précédents : ils **enregistrent l'évolution de leur mesure dans le temps**, pour qu'on puisse la tracer comme sur un oscilloscope. Tous deux signalent cette particularité ([components.py](../../simulator/components.py#L239-L245)) :

```python
@property
def records_history(self):
    return True

@property
def history_size(self):
    return self._history_size    # nombre de points conservés (500 par défaut)
```

Le moteur consulte ce drapeau à chaque pas. Pour les composants qui enregistrent, il met de côté la bonne grandeur — la **tension** pour le voltmètre, le **courant** pour l'ampèremètre ([simulator/engine.py](../../simulator/engine.py#L76-L78)) :

```python
if comp.records_history:
    # Enregistre la tension pour le voltmètre, le courant pour l'ampèremètre
    history_updates[comp.id] = state["current"] if isinstance(comp, Ammeter) else state["voltage"]
```

Ces points s'accumulent dans l'état partagé (`shared_state`, chapitre 23), dans une file de longueur bornée (`history_size`) : les plus anciens sont oubliés au fur et à mesure, comme une trace qui défile à l'écran. C'est ce qui permet d'afficher une courbe vivante plutôt qu'une simple valeur instantanée.

## 12.6 À retenir

- Mesurer, c'est perturber le moins possible. Voltmètre et ampèremètre répondent par deux extrêmes **duals**.
- Le **voltmètre** = une résistance quasi infinie (`1e-9 S`), branchée **en parallèle** ; il « voit sans toucher » et ancre légèrement ses nœuds (bonus anti-singularité).
- L'**ampèremètre** = une **source de tension de 0 V** branchée **en série** ; sa branche MNA fournit *gratuitement* le courant mesuré (`x[branch]`). Son stamping est celui de la source de tension avec `b[branch] = 0`.
- Les deux **enregistrent un historique** (`records_history`, `history_size`) : le moteur met de côté la tension (voltmètre) ou le courant (ampèremètre) à chaque pas, pour tracer une courbe.

**Dans le prochain chapitre**, nous rencontrerons le premier composant que l'on peut *manipuler pendant que la simulation tourne* : l'**interrupteur**. Il introduira l'idée d'un état modifiable en temps réel, pont vers l'interactivité du moteur.
