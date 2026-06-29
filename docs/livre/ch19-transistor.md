# Chapitre 19 — Le transistor bipolaire NPN

> *Où l'on rencontre le composant qui a changé le monde : un petit courant qui en commande un grand. Trois bornes, trois régimes, et une source de courant contrôlée au cœur du modèle.*

## 19.1 Le composant qui amplifie

Le transistor est sans doute le composant le plus important de l'histoire de l'électronique. Son principe : **un petit courant en commande un grand**. C'est ce qui permet d'**amplifier** (un signal faible pilote un signal puissant) et de **commuter** (un courant de commande ouvre ou ferme un interrupteur électronique). Toute l'informatique repose sur des milliards de transistors commutant.

Un transistor bipolaire NPN a **trois bornes** :

- la **base** (`B`) : la borne de commande, où l'on injecte un petit courant `I_B` ;
- le **collecteur** (`C`) : par où entre le grand courant `I_C` ;
- l'**émetteur** (`E`) : par où ressort l'ensemble du courant.

La relation magique, dans son régime normal, est :

$$
I_C = \beta \cdot I_B
$$

où `β` (bêta, souvent ~100) est le **gain en courant**. Un microampère sur la base commande cent microampères sur le collecteur. C'est l'amplification incarnée.

## 19.2 Trois régimes de fonctionnement

Le transistor est plus riche que la diode : il possède **trois** états, déterminés par les tensions à ses bornes. Notre simulateur les modélise ainsi :

- **Bloqué** (*cut-off*) : la tension base-émetteur `V_BE` est sous le seuil (`vbe_threshold ≈ 0,6 V`). La base ne commande rien ; le transistor est ouvert entre collecteur et émetteur. Aucun courant ne passe. C'est l'« interrupteur ouvert ».

- **Actif** (*active*) : `V_BE` dépasse le seuil **et** la tension collecteur-émetteur `V_CE` reste assez grande (`> vce_sat`). C'est le régime d'**amplification** : le collecteur se comporte comme une **source de courant** délivrant exactement `I_C = β·I_B`, indépendamment de `V_CE`.

- **Saturé** (*saturated*) : `V_BE` dépasse le seuil mais `V_CE` est tombée très bas (`≤ vce_sat`). Le transistor ne peut plus amplifier davantage ; il se comporte comme un **interrupteur fermé** entre collecteur et émetteur. C'est l'« interrupteur fermé » de la commutation.

Bloqué et saturé sont les deux états de l'usage « interrupteur » (tout ou rien) ; actif est l'état de l'usage « amplificateur » (linéaire). Un même composant, trois personnalités.

## 19.3 La décision, encore fondée sur le passé

Comme pour la diode (chapitre 17), le simulateur doit décider du régime *avant* de résoudre — donc il consulte le **pas précédent**. Il lit dans `prev_state` les valeurs `V_BE`, `V_CE`, `I_B`, et deux indices supplémentaires sur l'état du collecteur (`saturated`, `ic`), puis en déduit le régime courant ([simulator/components.py](../../simulator/components.py#L427-L469)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_b = node_map.get(self.node_base, -1)
    idx_c = node_map.get(self.node_collector, -1)
    idx_e = node_map.get(self.node_emitter, -1)

    vbe = prev_state.get("vbe", 0.0)
    vce = prev_state.get("vce", 0.0)
    i_b = prev_state.get("current", 0.0)
    sat_prev = prev_state.get("saturated", False)
    ic_prev = prev_state.get("ic", 0.0)

    if vbe < self.vbe_threshold:
        # Bloqué : jonction B-E quasi ouverte, C-E quasi ouvert.
        self._on = False
        self._sat = False
        _stamp_conductance(G, idx_b, idx_e, 1.0 / self.R_BE_OFF)
        _stamp_conductance(G, idx_c, idx_e, self.R_CE_OFF)
        return

    # Jonction base-émetteur passante : I_B = (V_BE - vbe_threshold) / R_BE_ON.
    # Le courant de base traverse donc la résistance de base externe.
    self._on = True
    _stamp_conductance(G, idx_b, idx_e, 1.0 / self.R_BE_ON)
    _stamp_current(b, idx_b, idx_e, self.vbe_threshold / self.R_BE_ON)

    i_c_drive = self.beta * max(i_b, 0.0)
    if sat_prev:
        self._sat = i_c_drive >= ic_prev   # la base sur-pilote → reste saturé
    else:
        self._sat = vce <= self.vce_sat    # V_CE effondrée → entre en saturation

    if self._sat:
        # Saturé : V_CE ≈ vce_sat (modèle compagnon résistance + offset)
        _stamp_conductance(G, idx_c, idx_e, 1.0 / self.R_CE_SAT)
        _stamp_current(b, idx_c, idx_e, self.vce_sat / self.R_CE_SAT)
    else:
        # Actif : source de courant contrôlée I_C = β·I_B (collector → emitter)
        _stamp_current(b, idx_e, idx_c, i_c_drive)
```

Le code est plus dense que celui de la diode, mais chaque régime se réduit encore à des outils **déjà connus** — conductances et sources de courant. La nouveauté de fond se cache dans le bloc « jonction passante », et elle mérite qu'on s'y arrête.

**La jonction base-émetteur est désormais explicitement modélisée.** Dans une première version naïve, le transistor traitait seulement le couple collecteur-émetteur et *supposait* un courant de base ; mais alors ce courant ne traversait jamais réellement le circuit. Le modèle actuel tamponne la jonction B-E comme une **conductance `1/R_BE_ON` en série avec un offset de seuil** (les constantes `R_BE_ON = 10 Ω`, `vbe_threshold ≈ 0,6 V`), exactement la mécanique « résistance + source » d'une diode passante (chapitre 18). Conséquence physique essentielle :

$$
V_{BE} \approx v_{\text{threshold}} + R_{BE\_ON}\cdot I_B
\quad\Longrightarrow\quad
I_B = \frac{V_{BE} - v_{\text{threshold}}}{R_{BE\_ON}}
$$

Le courant de base est donc **fixé par la résistance de base externe** du circuit, et non plus deviné. C'est *ce* courant réel qui pilote ensuite le collecteur via `I_C = β·I_B`.

Reste à choisir entre actif et saturé. En **régime actif**, le collecteur est une **source de courant** `β·I_B` (la source *contrôlée* du chapitre 11). En **saturation**, `V_CE` est figée près de `vce_sat` par une résistance `R_CE_SAT` accompagnée d'un offset — donc on *ne peut plus* relire `V_CE` pour décider d'en sortir (elle est artificiellement basse). Le modèle ruse alors : tant que la base **sur-pilote** (le courant demandé `β·I_B` dépasse le courant `ic_prev` que le circuit collecteur fournit réellement), on **reste** saturé ; sinon on repasse en actif. C'est une petite **hystérésis** qui stabilise la transition, dans le même esprit « décider d'après le passé » que la diode.

Le transistor n'introduit donc aucune brique nouvelle : il **orchestre** conductances, offsets et source de courant selon son régime. C'est toute la beauté de l'abstraction bâtie depuis le chapitre 6.

## 19.4 La richesse de l'état : au-delà de tension et courant

Un point technique mérite attention. Jusqu'ici, l'état d'un composant tenait en deux nombres : `voltage` et `current`. Mais le transistor a besoin de **plus** : pour décider son régime, il lui faut `V_BE`, `V_CE`, mais aussi se *souvenir* s'il était saturé et de quel courant collecteur il débitait. Son `get_state` enrichit donc le dictionnaire d'état ([components.py](../../simulator/components.py#L471-L487)) :

```python
def get_state(self, x, node_map, branch_map):
    vb = _node_voltage(x, node_map, self.node_base)
    vc = _node_voltage(x, node_map, self.node_collector)
    ve = _node_voltage(x, node_map, self.node_emitter)
    vbe = vb - ve
    vce = vc - ve
    # Courant de base cohérent avec l'état réellement stampé (0 si bloqué)
    i_b = max((vbe - self.vbe_threshold) / self.R_BE_ON, 0.0) if self._on else 0.0
    # Courant collecteur : mesuré aux bornes en saturation, sinon β·I_B
    if self._sat:
        i_c = (vce - self.vce_sat) / self.R_CE_SAT
    else:
        i_c = self.beta * i_b
    return {
        "voltage": vce, "current": i_b,
        "vbe": vbe, "vce": vce, "ic": i_c, "saturated": self._sat,
    }
```

Deux choses sont à noter. D'abord, le **courant de base est désormais calculé de façon cohérente** avec ce qui a réellement été tamponné : `(V_BE − seuil)/R_BE_ON` (et zéro si la jonction était bloquée, d'où le drapeau `self._on` mémorisé par `stamp`). Fini le courant deviné à `V_BE/1000` de la première version — le simulateur rapporte le courant que le circuit fait *vraiment* passer. Ensuite, les clés `"vbe"`, `"vce"`, `"ic"` et `"saturated"` sont précisément celles que le `stamp` ira relire au pas suivant pour reconduire son hystérésis. C'est un bel exemple de la souplesse du contrat `get_state`/`prev_state` : un composant peut y faire transiter **autant d'information d'état que sa physique l'exige**, pas seulement le couple tension-courant.

> **Note d'implémentation.** Les drapeaux `self._on` et `self._sat`, fixés dans `stamp` et relus dans `get_state`, garantissent que la mesure de fin de pas décrit *exactement* le régime qui a été résolu. Sans eux, `get_state` pourrait retomber sur un régime différent de celui réellement tamponné, et l'état publié deviendrait incohérent.

## 19.5 Les limites du modèle

Soyons honnêtes sur ce que ce modèle **ne** capture **pas**, dans l'esprit du chapitre 17 :

- Les transitions entre régimes subissent le **retard d'un pas** inhérent à la linéarisation par morceaux (la décision actif/saturé se fonde sur `prev_state`).
- La jonction base-émetteur est une **droite** (`vbe_threshold + R_BE_ON·I_B`), pas l'exponentielle de Shockley : les constantes `R_BE_ON` et `R_CE_SAT` sont des linéarisations fixes, choisies pour le réalisme qualitatif et la stabilité, pas pour la précision.
- La sortie de saturation repose sur une **heuristique** (comparer `β·I_B` au `ic_prev` du circuit) plutôt que sur une vraie résolution implicite.
- Les effets fins (tension d'Early, dépendance en température, courbes réelles, capacités de jonction) sont ignorés.

C'est un transistor **idéalisé**, conçu pour illustrer le principe « petit courant commande grand courant » et pour fonctionner en temps réel — pas pour concevoir un circuit de précision. Mais pour comprendre comment un simulateur *gère* un composant à régimes multiples, il est parfait.

## 19.6 À retenir

- Le **transistor bipolaire NPN** : trois bornes (**base**, **collecteur**, **émetteur**) ; un petit courant de base `I_B` commande un grand courant de collecteur `I_C = β·I_B`.
- **Trois régimes** : **bloqué** (jonctions ouvertes), **actif** (amplificateur : source de courant `β·I_B`), **saturé** (`V_CE` figée à `vce_sat` par une résistance + offset).
- La **jonction base-émetteur est explicitement modélisée** (`R_BE_ON` + offset de seuil), si bien que le **courant de base traverse réellement la résistance de base externe** : `I_B = (V_BE − seuil)/R_BE_ON`. C'est ce courant réel qui pilote `I_C = β·I_B`.
- Le régime est décidé d'après le **pas précédent**, puis chaque régime se ramène à des **briques connues** : conductances et sources de courant. La sortie de saturation use d'une **hystérésis** (`β·I_B` comparé à `ic_prev`).
- L'**état** d'un composant peut porter plus que tension/courant : le transistor fait transiter `"vbe"`, `"vce"`, `"ic"` et `"saturated"` via `get_state`/`prev_state`.
- Modèle **idéalisé** : retard d'un pas, jonctions linéarisées (pas de Shockley), sortie de saturation heuristique, effets fins ignorés.

**Dans le prochain chapitre**, nous clôturons le catalogue avec le dernier composant actif : l'**amplificateur opérationnel idéal**. Paradoxalement, c'est le plus simple à tamponner de toute la Partie V — mais comprendre *pourquoi* il fonctionne demande de saisir l'idée subtile de la rétroaction.
