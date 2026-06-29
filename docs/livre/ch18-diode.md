# Chapitre 18 — La diode

> *Où l'on modélise le clapet anti-retour de l'électronique — un composant qui ne laisse passer le courant que dans un sens — et où une petite astuce de décalage révèle toute la finesse de la linéarisation par morceaux.*

## 18.1 La diode : un sens unique

Une diode est un composant à deux bornes, l'**anode** et la **cathode**, qui se comporte comme un clapet anti-retour : il laisse passer le courant dans un sens (de l'anode vers la cathode) et le bloque dans l'autre. C'est le composant de base du **redressement** : transformer une tension alternative (qui change de signe) en une tension toujours positive.

Mais ce clapet n'est pas parfait. Pour s'ouvrir, il faut le « pousser » au-delà d'une tension de **seuil**, notée `vf` (pour *forward voltage*), d'environ `0,6 V` pour une diode au silicium. En dessous, elle reste bloquée ; au-dessus, elle conduit. C'est ce seuil qui crée le coude non-linéaire du chapitre 17.

## 18.2 Le modèle à deux états

Fidèle à la ruse du chapitre 17, le simulateur n'essaie pas de reproduire la courbe exacte de la diode. Il l'approche par **deux états**, chacun étant une simple résistance :

- **Passante** : la diode conduit. On la modélise par une résistance très faible, `R_ON = 0,1 Ω`.
- **Bloquée** : la diode isole. On la modélise par une résistance très grande, `R_OFF = 1e9 Ω`.

Le choix entre les deux se fait — c'est tout le principe du chapitre 17 — d'après la tension du **pas précédent**. Si la diode était suffisamment polarisée juste avant (`v_prev > vf`), on la suppose passante ; sinon, bloquée.

## 18.3 Le piège de l'oscillation, et l'astuce du décalage

Voici la subtilité la plus instructive de tout le simulateur. Modéliser la diode passante par une simple résistance `R_ON` semble naturel… mais conduit à un désastre. Suivons le raisonnement.

Supposons qu'on modélise la diode passante par la seule conductance `1/R_ON`. La diode étant un quasi-court-circuit (`0,1 Ω`), la tension à ses bornes calculée serait minuscule, proche de `0 V`. Or `0 V < vf` : au pas suivant, l'oracle (le pas précédent) déciderait donc que la diode est **bloquée** ! Elle se couperait. Mais une fois bloquée, la tension à ses bornes remonterait au-dessus de `vf`, et au pas d'après elle redeviendrait passante… On obtient une diode qui **clignote** sans fin entre passante et bloquée, à chaque pas — exactement le risque d'oscillation annoncé au chapitre 17.

La parade est d'ancrer le modèle passant autour du seuil `vf`, et non autour de zéro. Physiquement, une diode passante maintient une tension d'environ `vf` à ses bornes (les fameux `0,6 V`). On modélise donc la diode passante non par une simple résistance, mais par :

$$
V_{AK} = vf + R_{ON} \cdot I
$$

c'est-à-dire une chute de tension fixe `vf`, en série avec la petite résistance `R_ON`. En termes de stamping (chapitre 16), cela donne une conductance **plus une source de courant de décalage** `vf / R_ON`. Ainsi, la tension calculée aux bornes reste autour de `vf`, l'oracle la voit toujours passante, et l'oscillation disparaît.

## 18.4 Le code

Tout ce raisonnement tient en quelques lignes ([simulator/components.py](../../simulator/components.py#L464-L482)) :

```python
R_ON  = 0.1    # Ω
R_OFF = 1e9    # Ω

def stamp(self, G, b, node_map, branch_map, dt, t, prev_state):
    idx_a = node_map.get(self.node_anode,   -1)
    idx_k = node_map.get(self.node_cathode, -1)
    v_prev = prev_state.get("voltage", 0.0)
    if v_prev > self.vf:
        # Passante : V_AK = vf + R_ON*I → conductance + source de courant offset
        # Sans l'offset vf, le modèle oscille : V_AK calculé ≈ 0 < vf → coupe à l'étape suivante
        _stamp_conductance(G, idx_a, idx_k, 1.0 / self.R_ON)
        _stamp_current(b, idx_a, idx_k, self.vf / self.R_ON)
    else:
        _stamp_conductance(G, idx_a, idx_k, 1.0 / self.R_OFF)
```

Le commentaire du code raconte exactement le piège du §18.3. Observez la structure :

- `v_prev > self.vf` : la décision fondée sur le pas précédent (l'oracle du chapitre 17).
- État passant : `_stamp_conductance(... 1/R_ON)` **plus** `_stamp_current(... vf/R_ON)` — la conductance *et* le décalage anti-oscillation.
- État bloqué : une seule conductance minuscule (`1/R_OFF`), qui isole tout en ancrant légèrement les nœuds (anti-singularité, chapitre 8).

Et le `get_state` applique la même logique pour rapporter le courant réel ([components.py](../../simulator/components.py#L476-L482)) :

```python
def get_state(self, x, node_map, branch_map):
    va = _node_voltage(x, node_map, self.node_anode)
    vk = _node_voltage(x, node_map, self.node_cathode)
    voltage = va - vk
    if voltage > self.vf:
        return {"voltage": voltage, "current": (voltage - self.vf) / self.R_ON}
    return {"voltage": voltage, "current": voltage / self.R_OFF}
```

En zone passante, le courant est `(voltage − vf)/R_ON` : on retranche le seuil avant d'appliquer la loi d'Ohm, cohérent avec le modèle `V_AK = vf + R_ON·I`.

## 18.5 L'usage emblématique : le redresseur

L'application reine de la diode est le **redressement**. Branchez une diode en série avec une source sinusoïdale et une charge : pendant les alternances positives (au-dessus de `vf`), la diode conduit et le courant passe ; pendant les alternances négatives, elle bloque. En sortie, on ne récupère que les bosses positives — une tension alternative est devenue une tension pulsée, toujours positive. C'est la première étape de toute alimentation qui convertit le secteur en courant continu.

Le dépôt contient justement un circuit `diode_bridge` (un pont de quatre diodes, qui redresse *les deux* alternances) : un excellent terrain de jeu pour observer ce comportement, et pour vérifier que la ruse anti-oscillation tient bien la route.

## 18.6 À retenir

- Une **diode** est un clapet anti-retour : elle conduit de l'anode vers la cathode au-delà d'un **seuil** `vf` (~0,6 V), bloque en dessous.
- Le simulateur la modélise par **deux états résistifs** : `R_ON = 0,1 Ω` (passante), `R_OFF = 1e9 Ω` (bloquée), choisis selon la tension du **pas précédent**.
- **Astuce clé** : la diode passante est modélisée par `V_AK = vf + R_ON·I` (conductance **+ source de courant de décalage** `vf/R_ON`). Sans ce décalage, la tension calculée tomberait sous `vf` et la diode **oscillerait** d'un pas à l'autre.
- Usage emblématique : le **redressement** (transformer de l'alternatif en continu), illustré par le circuit `diode_bridge` du dépôt.

**Dans le prochain chapitre**, nous monterons d'un cran en complexité avec le **transistor bipolaire** : trois bornes, trois régimes, et une source de courant *contrôlée* qui fait de lui l'amplificateur et l'interrupteur fondamental de toute l'électronique.
