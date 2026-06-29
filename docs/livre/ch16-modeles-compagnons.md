# Chapitre 16 — Les modèles compagnons

> *Où l'aboutissement de deux chapitres se révèle d'une simplicité déconcertante : à chaque pas, un condensateur n'est qu'une résistance accompagnée d'une pile. On le « tamponne » alors avec des outils vieux de dix chapitres.*

## 16.1 La reconnaissance

Au chapitre 15, nous avons transformé la loi du condensateur en une équation algébrique :

$$
i(t) = g_{eq}\, v(t) \;-\; g_{eq}\, v_{\text{prev}}, \qquad g_{eq} = \frac{C}{dt}
$$

Prenons un instant pour *reconnaître* ce que nous avons sous les yeux. Cette équation dit que le courant traversant le condensateur est la somme de deux contributions :

1. `g_eq · v(t)` : un courant proportionnel à la tension actuelle. C'est **exactement le comportement d'une conductance** `g_eq` (une résistance, chapitre 3).
2. `− g_eq · v_prev` : un courant qui ne dépend **que du passé connu**. C'est une constante à ce pas — donc **exactement le comportement d'une source de courant** (chapitre 11).

Autrement dit :

> **À chaque pas de temps, un condensateur se comporte comme une conductance `g_eq` en parallèle avec une source de courant.**

Ce déguisement porte un nom : le **modèle compagnon** (en anglais *companion model*). C'est un équivalent temporaire, valable pour *ce pas-là* seulement, qui remplace un composant compliqué (réactif, différentiel) par un assemblage de composants que nous savons déjà tamponner depuis le chapitre 6. La pièce qui manquait est en place : nous n'avons besoin d'**aucun outil nouveau**.

## 16.2 Le condensateur tamponné

Le code traduit cette reconnaissance presque mot pour mot ([simulator/components.py](../../simulator/components.py#L130-L138)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    g_eq = self.capacitance / dt
    v_prev = prev_state.get("voltage", 0.0)
    # Conductance compagnon
    _stamp_conductance(G, idx_a, idx_b, g_eq)
    # Source de courant compagnon : injecte g_eq*v_prev de idx_b vers idx_a
    _stamp_current(b, idx_a, idx_b, g_eq * v_prev)
```

Deux lignes, deux vieilles connaissances : `_stamp_conductance` (la part « résistance ») et `_stamp_current` (la part « source de courant », qui dépose le terme mémoire dans `b`). Le `prev_state.get("voltage", 0.0)` va chercher la tension du pas précédent — c'est *là* que la mémoire du chapitre 14 est consommée. Notez aussi que `dt` est enfin utilisé : nous sommes loin de la résistance intemporelle du chapitre 9.

## 16.3 La bobine tamponnée

La bobine suit la même logique, avec sa propre équation (`i(t) = g_eq·v(t) + i_prev`, `g_eq = dt/L`). Cette fois, le terme mémoire est un **courant** précédent ([components.py](../../simulator/components.py#L165-L174)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    g_eq = dt / self.inductance
    i_prev = prev_state.get("current", 0.0)
    # Conductance compagnon
    _stamp_conductance(G, idx_a, idx_b, g_eq)
    # Source de courant compagnon : le courant de branche i(t)=g_eq*v(t)+i_prev
    # circule de idx_a vers idx_b, donc i_prev quitte idx_a (injection négative).
    _stamp_current(b, idx_a, idx_b, -i_prev)
```

Rigoureusement la même structure. Seules changent la formule de `g_eq` et la grandeur mémorisée (`current` au lieu de `voltage`). La dualité condensateur/bobine, annoncée au chapitre 14, se lit jusque dans le code.

Un détail de **signe** mérite l'attention. Pour le condensateur, le terme mémoire `g_eq·v_prev` est injecté tel quel ; pour la bobine, c'est `−i_prev`. La raison tient à la **convention d'orientation** : on choisit que le courant de branche `i(t) = g_eq·v(t) + i_prev` circule de `idx_a` vers `idx_b`. Le terme constant `i_prev` *quitte* donc `idx_a`, ce qui se traduit par une injection **négative** dans `b` du côté `idx_a` (`_stamp_current(b, idx_a, idx_b, -i_prev)`). Se tromper de signe ici inverserait le sens du courant mémorisé et ferait diverger la dynamique de la bobine — un bug subtil, car la conductance compagnon, elle, resterait correcte.

## 16.4 La boucle de la mémoire

Le modèle compagnon n'a de sens que si la mémoire est **entretenue** : à la fin de chaque pas, l'état courant doit devenir l'état « précédent » du pas suivant. C'est le rôle de cette ligne du moteur ([simulator/engine.py](../../simulator/engine.py#L94)) :

```python
self._prev_states = comp_states
```

Le cycle complet de la mémoire est donc :

1. **Début du pas** : le composant lit `prev_state` (la valeur d'il y a un pas) pour construire son modèle compagnon.
2. **Résolution** : le système `G·x = b` est résolu, donnant les nouvelles tensions.
3. **Fin du pas** : les nouveaux états deviennent les `prev_states`, prêts pour le pas suivant.

Ce fil tendu d'un pas à l'autre est ce qui donne au simulateur sa **mémoire physique**. Sans lui, chaque pas repartirait de zéro et le condensateur ne « chargerait » jamais.

## 16.5 Une subtilité : recalculer le courant après coup

Un détail d'implémentation mérite explication, car il surprend à la lecture du code. Le `get_state` du condensateur renvoie `current: 0.0` ([components.py](../../simulator/components.py#L140-L144)) :

```python
def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    # Le courant réel est recalculé par le moteur depuis prev_state
    return {"voltage": va - vb, "current": 0.0}
```

Pourquoi zéro ? Parce que `get_state` reçoit la solution `x`, mais **pas** le `prev_state` — or le courant du condensateur (`g_eq·(v − v_prev)`) a besoin de la tension précédente. Le moteur s'en charge donc *après* la résolution, dans une passe dédiée ([engine.py](../../simulator/engine.py#L82-L92)) :

```python
for comp in self._components:
    if isinstance(comp, Inductor):
        ...
        comp_states[comp.id]["current"] = g_eq * (va - vb) + i_prev
    elif isinstance(comp, Capacitor):
        v_prev = self._prev_states[comp.id].get("voltage", 0.0)
        g_eq = comp.capacitance / self._dt
        comp_states[comp.id]["current"] = g_eq * (comp_states[comp.id]["voltage"] - v_prev)
```

C'est exactement notre formule du chapitre 15, appliquée une fois la tension connue. Une petite entorse à la symétrie `stamp`/`get_state`, justifiée par le fait que le courant réactif dépend de deux instants à la fois.

## 16.6 Voir la charge se faire : un exemple numérique

Rien ne vaut un calcul concret. Chargeons un condensateur à travers une résistance — le circuit RC, le « bonjour le monde » de l'électronique dynamique.

Montage : une source maintient le nœud `A` à `1 V`. Une résistance `R = 1 Ω` relie `A` au nœud `n`. Un condensateur `C = 1 F` relie `n` à la masse. Prenons un pas `dt = 0,1 s`.

Le modèle compagnon du condensateur donne `g_eq = C/dt = 10 S`. Écrivons la loi des nœuds en `n` (la seule inconnue), avec les conductances qui le touchent — `R` (vers `A`) et `g_eq` (vers la masse) — et les courants injectés :

$$
(1 + 10)\,V_n = \underbrace{1 \cdot V_A}_{\text{via } R} + \underbrace{10 \cdot v_{\text{prev}}}_{\text{source compagnon}}
\;\Rightarrow\;
V_n = \frac{1 + 10\,v_{\text{prev}}}{11}
$$

Déroulons les premiers pas, en partant d'un condensateur déchargé (`v_prev = 0`) :

| Pas | `t` (s) | `v_prev` (V) | `V_n` calculé (V) | Exact `1 − e^{−t}` (V) |
|----:|--------:|-------------:|------------------:|-----------------------:|
| 1   | 0,1     | 0,000        | 0,0909            | 0,0952                 |
| 2   | 0,2     | 0,0909       | 0,1736            | 0,1813                 |
| 3   | 0,3     | 0,1736       | 0,2487            | 0,2592                 |
| 4   | 0,4     | 0,2487       | 0,3170            | 0,3297                 |
| …   | …       | …            | … → 1,000         | … → 1,000              |

Deux enseignements limpides :

- **La charge se construit progressivement**, exactement comme dans un vrai condensateur : montée rapide au début, puis ralentissement asymptotique vers `1 V`. Cette courbe en exponentielle émerge *toute seule* du jeu entre la conductance compagnon et la mémoire `v_prev`.
- **Notre résultat suit la solution exacte** `1 − e^{−t/RC}`, avec un petit retard dû à la discrétisation. C'est l'erreur d'Euler implicite : légèrement en dessous, mais **toujours stable**, jamais divergente (chapitre 15). En réduisant `dt`, l'écart se réduirait.

Vous tenez là, en quelques lignes d'arithmétique, l'essence même de la simulation temporelle : une succession de problèmes statiques, reliés par une mémoire, qui reconstitue une dynamique continue.

## 16.7 À retenir

- Le **modèle compagnon** déguise, à chaque pas, un composant réactif en **une conductance `g_eq` en parallèle avec une source de courant** — deux briques connues depuis le chapitre 6.
- Condensateur : `g_eq = C/dt`, source compagnon `g_eq·v_prev` (mémoire = **tension** précédente).
  Bobine : `g_eq = dt/L`, source compagnon `−i_prev` (mémoire = **courant** précédent ; le signe négatif suit la convention d'orientation de la branche).
- La **mémoire** est entretenue par `self._prev_states = comp_states` en fin de pas. Cycle : lire `prev_state` → résoudre → enregistrer le nouvel état.
- Le **courant** d'un composant réactif est recalculé *après* la résolution, car il dépend de deux instants (la passe dédiée dans `engine.py`).
- Un exemple **RC** montre la charge exponentielle émerger naturellement, fidèle à `1 − e^{−t/RC}`, et **stable** grâce à Euler implicite.

**Ceci clôt la Partie IV** — le cœur conceptuel du livre. Vous savez désormais comment un système algébrique simule une physique différentielle, par le triple jeu de la **discrétisation**, du **modèle compagnon** et de la **mémoire**.

**La Partie V** s'attaquera à un dernier obstacle : la **non-linéarité**. Diode et transistor ne se laissent pas décrire par une conductance fixe — leur comportement dépend de leur propre état. Nous verrons comment le simulateur ruse, là encore, en s'appuyant sur le pas précédent.
