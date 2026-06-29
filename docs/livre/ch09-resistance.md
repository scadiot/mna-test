# Chapitre 9 — La résistance

> *Où l'on retrouve notre plus vieille connaissance, mais cette fois en tant que composant réel : ce qu'elle fait dans un circuit, comment on l'associe, et pourquoi elle est le « composant zéro » du simulateur.*

## 9.1 Le composant le plus simple — et le plus utilisé

La résistance est partout. Elle limite un courant, fixe une tension, protège une LED, « tire » un signal vers une valeur connue. Pourtant, elle ne fait qu'une seule chose : **s'opposer au passage du courant**, selon la loi d'Ohm (chapitre 3) :

$$
U = R \cdot I \qquad\Longleftrightarrow\qquad I = G \cdot U, \quad G = \frac{1}{R}
$$

Du point de vue du simulateur, c'est le **composant zéro** : il n'a ni mémoire (contrairement au condensateur), ni état interne (contrairement à la diode), ni branche (contrairement à la source de tension). Sa contribution est une simple conductance constante. Si vous comprenez la résistance, vous comprenez le squelette de tous les autres.

## 9.2 Rappel : son stamping

Nous avons déjà disséqué son code au chapitre 6 ; redonnons-le pour mémoire ([simulator/components.py](../../simulator/components.py#L100-L109)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_a, -1)
    idx_b = node_map.get(self.node_b, -1)
    _stamp_conductance(G, idx_a, idx_b, 1.0 / self.resistance)

def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_a)
    vb = _node_voltage(x, node_map, self.node_b)
    voltage = va - vb
    return {"voltage": voltage, "current": voltage / self.resistance}
```

Remarquez tout ce qui est **absent** : aucun usage de `dt` (pas de temps), aucun de `t` (instant), aucun de `prev_state` (passé). La résistance est **intemporelle** : sa réponse ne dépend que des tensions de l'instant. C'est ce qui la rend si simple.

## 9.3 Associer des résistances : série et parallèle

Deux montages reviennent sans cesse. Il est utile de savoir les calculer, ne serait-ce que pour vérifier les résultats du simulateur à la main.

**En série** (l'une après l'autre, traversées par le même courant), les résistances s'**additionnent** :

$$
R_{\text{série}} = R_1 + R_2
$$

**En parallèle** (entre les deux mêmes nœuds, soumises à la même tension), ce sont les **conductances** qui s'additionnent (chapitre 3) — d'où la formule en inverses pour les résistances :

$$
G_{\text{parallèle}} = G_1 + G_2 \qquad\Longleftrightarrow\qquad R_{\text{parallèle}} = \frac{R_1 R_2}{R_1 + R_2}
$$

Le simulateur, lui, n'a *pas besoin* de ces formules : le stamping additionne automatiquement les conductances dans les cases de la matrice (chapitre 5). Mais elles restent vos meilleures alliées pour un contrôle rapide.

## 9.4 Le diviseur de tension, en pratique

L'usage emblématique de deux résistances en série est le **diviseur de tension**, déjà rencontré au chapitre 7. Si une tension `U` est appliquée aux bornes de `R1 + R2`, la tension récupérée aux bornes de `R2` vaut :

$$
U_{\text{sortie}} = U \cdot \frac{R_2}{R_1 + R_2}
$$

Avec `R1 = R2`, on récupère la moitié (`6 V → 3 V`, comme au chapitre 7). C'est la manière la plus simple d'obtenir une tension intermédiaire à partir d'une tension plus élevée. On le retrouvera, en version *réglable*, dans le potentiomètre — une extension naturelle du simulateur évoquée au chapitre 24.

## 9.5 La puissance dissipée

Une résistance traversée par un courant **chauffe** : elle convertit de l'énergie électrique en chaleur. En combinant `P = U·I` (chapitre 1) et la loi d'Ohm, on obtient les formes équivalentes :

$$
P = U \cdot I = R \cdot I^2 = \frac{U^2}{R}
$$

Le simulateur ne calcule pas cette puissance (elle n'intervient pas dans la résolution MNA), mais `get_state` fournit tension *et* courant : il suffirait de les multiplier pour l'obtenir. C'est une grandeur cruciale dans le monde réel — une résistance sous-dimensionnée grille — même si notre modèle idéal l'ignore.

## 9.6 À retenir

- La résistance est le **composant zéro** : une conductance constante `G = 1/R`, sans mémoire, sans état, sans branche.
- Son stamping n'utilise ni `t`, ni `dt`, ni `prev_state` : elle est **intemporelle**.
- **Série** : les résistances s'additionnent. **Parallèle** : les conductances s'additionnent. Le stamping fait ce cumul tout seul.
- Le **diviseur de tension** (`U_sortie = U · R₂/(R₁+R₂)`) est son usage emblématique.
- Elle dissipe une **puissance** `P = R·I²`, ignorée par le modèle mais essentielle en pratique.

**Dans le prochain chapitre**, nous donnerons vie au circuit en y introduisant le temps par la petite porte : les **sources**, et leurs différentes **formes d'onde** (continu, sinus, impulsion, créneau). Nous y verrons comment une valeur imposée peut varier à chaque pas de simulation.
