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

Comme pour la diode (chapitre 17), le simulateur doit décider du régime *avant* de résoudre — donc il consulte le **pas précédent**. Il lit dans `prev_state` les valeurs `V_BE`, `V_CE` et `I_B` d'il y a un pas, et en déduit le régime courant ([simulator/components.py](../../simulator/components.py#L413-L430)) :

```python
def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_c = node_map.get(self.node_collector, -1)
    idx_e = node_map.get(self.node_emitter, -1)

    vbe = prev_state.get("vbe", 0.0)
    vce = prev_state.get("vce", 0.0)
    i_b = prev_state.get("current", 0.0)

    if vbe < self.vbe_threshold:
        # Bloqué : résistance très grande entre collector et emitter
        _stamp_conductance(G, idx_c, idx_e, 1e-9)
    elif vce > self.vce_sat:
        # Actif : source de courant contrôlée I_C = β * I_B (de collector vers emitter)
        i_c = self.beta * i_b
        _stamp_current(b, idx_e, idx_c, i_c)   # I_C entre dans emitter, sort de collector
    else:
        # Saturé : résistance très faible entre C et E
        _stamp_conductance(G, idx_c, idx_e, 1e6)
```

Remarquez comme chaque régime se réduit à un outil **déjà connu** :

- **Bloqué** → une conductance minuscule (`1e-9 S`) : comme un interrupteur ouvert (chapitre 13).
- **Saturé** → une conductance énorme (`1e6 S`) : comme un interrupteur fermé.
- **Actif** → une **source de courant** (`_stamp_current`) de valeur `β·I_B` : c'est la source de courant *contrôlée* annoncée au chapitre 11. Le courant injecté n'est pas fixé d'avance ; il dépend du courant de base mesuré au pas précédent.

Le transistor n'introduit donc aucune mécanique nouvelle : il **orchestre** des briques connues selon son régime. C'est toute la beauté de l'abstraction bâtie depuis le chapitre 6.

## 19.4 La richesse de l'état : au-delà de tension et courant

Un point technique mérite attention. Jusqu'ici, l'état d'un composant tenait en deux nombres : `voltage` et `current`. Mais le transistor a besoin de **plus** : pour décider son régime, il lui faut `V_BE` *et* `V_CE` séparément. Son `get_state` enrichit donc le dictionnaire d'état ([components.py](../../simulator/components.py#L432-L440)) :

```python
def get_state(self, x, node_map, branch_map):
    vb = _node_voltage(x, node_map, self.node_base)
    vc = _node_voltage(x, node_map, self.node_collector)
    ve = _node_voltage(x, node_map, self.node_emitter)
    vbe = vb - ve
    vce = vc - ve
    # Courant de base approximé (résistance base-emitter = 1kΩ par défaut)
    i_b = vbe / 1000.0 if vbe >= self.vbe_threshold else 0.0
    return {"voltage": vce, "current": i_b, "vbe": vbe, "vce": vce}
```

Les clés supplémentaires `"vbe"` et `"vce"` sont précisément celles que le `stamp` ira relire au pas suivant. C'est un bel exemple de la souplesse du contrat `get_state`/`prev_state` : un composant peut y faire transiter **autant d'information d'état que sa physique l'exige**, pas seulement le couple tension-courant. Le courant de base est ici approché en supposant une résistance base-émetteur de `1 kΩ` — une simplification de plus, assumée par ce modèle pédagogique.

## 19.5 Les limites du modèle

Soyons honnêtes sur ce que ce modèle **ne** capture **pas**, dans l'esprit du chapitre 17 :

- Les transitions entre régimes subissent le **retard d'un pas** inhérent à la linéarisation par morceaux.
- Le courant de base est grossièrement approximé (résistance fixe de `1 kΩ`).
- Les effets fins (tension d'Early, dépendance en température, courbes réelles) sont ignorés.

C'est un transistor **idéalisé**, conçu pour illustrer le principe « petit courant commande grand courant » et pour fonctionner en temps réel — pas pour concevoir un circuit de précision. Mais pour comprendre comment un simulateur *gère* un composant à régimes multiples, il est parfait.

## 19.6 À retenir

- Le **transistor bipolaire NPN** : trois bornes (**base**, **collecteur**, **émetteur**) ; un petit courant de base `I_B` commande un grand courant de collecteur `I_C = β·I_B`.
- **Trois régimes** : **bloqué** (interrupteur ouvert), **actif** (amplificateur : source de courant `β·I_B`), **saturé** (interrupteur fermé).
- Le régime est décidé d'après le **pas précédent** (`V_BE`, `V_CE`, `I_B` dans `prev_state`), puis chaque régime se ramène à une **brique connue** : conductance minuscule, conductance énorme, ou source de courant contrôlée.
- L'**état** d'un composant peut porter plus que tension/courant : le transistor fait transiter `"vbe"` et `"vce"` via `get_state`/`prev_state`.
- Modèle **idéalisé** : retard d'un pas, courant de base approximé, effets fins ignorés.

**Dans le prochain chapitre**, nous clôturons le catalogue avec le dernier composant actif : l'**amplificateur opérationnel idéal**. Paradoxalement, c'est le plus simple à tamponner de toute la Partie V — mais comprendre *pourquoi* il fonctionne demande de saisir l'idée subtile de la rétroaction.
