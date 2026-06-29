# Chapitre 22 — Du fichier au circuit

> *Où l'on remonte à la source : comment un fichier texte au format JSON devient une liste d'objets Python que le moteur sait simuler — et où une simple vérification rappelle l'importance vitale de la masse.*

## 22.1 Décrire un circuit avec du texte

Avant de simuler un circuit, il faut le **décrire**. Plutôt que de coder chaque circuit en dur, le simulateur les lit depuis des fichiers **JSON** — un format texte lisible aussi bien par un humain que par une machine. Un circuit y est décrit comme une liste de composants, chacun avec son type, ses nœuds et ses paramètres. Par exemple :

```json
{
  "name": "Diviseur de tension",
  "dt": 1e-5,
  "components": [
    { "id": "V1", "type": "voltage_source", "node_pos": "in", "node_neg": "GND",
      "params": { "waveform": "dc", "amplitude": 6.0 } },
    { "id": "R1", "type": "resistor", "node_a": "in", "node_b": "out",
      "params": { "resistance": 1000 } },
    { "id": "R2", "type": "resistor", "node_a": "out", "node_b": "GND",
      "params": { "resistance": 1000 } }
  ]
}
```

On y reconnaît tout le vocabulaire du livre : des nœuds nommés (`in`, `out`, `GND`), des types de composants, le pas de temps `dt` (chapitre 15), et des paramètres propres à chacun. Le rôle du **chargeur** (`circuit_loader.py`) est de traduire ce texte en objets Python vivants.

## 22.2 La structure d'accueil : la dataclass `Circuit`

Le résultat du chargement est un objet `Circuit`, simple conteneur de tout ce dont le moteur a besoin ([circuit_loader.py](../../circuit_loader.py#L12-L18)) :

```python
@dataclass
class Circuit:
    """Représentation d'un circuit chargé depuis un fichier JSON."""
    name: str
    dt: float
    components: list
    histories: dict = field(default_factory=dict)   # {component_id: history_size}
```

Quatre champs : un nom, le pas de temps, la liste des composants instanciés, et la liste des appareils qui enregistrent un historique (chapitre 12). C'est précisément ce que `SimulationEngine` reçoit dans son constructeur (chapitre 21).

## 22.3 La fabrique de composants

Le cœur du chargeur est une grande **fabrique** (`_make_component`) : une fonction qui, selon le champ `"type"`, construit la bonne classe de composant. C'est une longue suite de `if/elif`, mais d'une parfaite régularité ([circuit_loader.py](../../circuit_loader.py#L39-L81)) :

```python
def _make_component(data):
    comp_id = data["id"]
    comp_type = data["type"]
    params = data.get("params", {})

    if comp_type == "resistor":
        return Resistor(comp_id, data["node_a"], data["node_b"],
                        float(params["resistance"]))
    elif comp_type == "capacitor":
        return Capacitor(comp_id, data["node_a"], data["node_b"],
                         float(params["capacitance"]))
    # ... un cas par type de composant ...
    elif comp_type == "diode":
        return Diode(comp_id, data["node_anode"], data["node_cathode"],
                     float(params.get("vf", 0.6)))
    else:
        raise ValueError(f"Type de composant inconnu : '{comp_type}'")
```

Chaque branche lit les nœuds (`node_a`, `node_anode`…) et les paramètres attendus par ce composant précis, puis appelle son constructeur. Deux idiomes valent d'être notés :

- **`params.get("vf", 0.6)`** : on lit un paramètre *avec une valeur par défaut*. Si le JSON ne précise pas `vf`, la diode prend `0,6 V`. C'est ce qui rend les fichiers concis : on ne mentionne que ce qui s'écarte de l'usuel.
- **`float(...)`** : une conversion explicite. Le JSON pourrait fournir un entier ou une chaîne ; on garantit le bon type pour les calculs.

Le `else` final est une **sécurité** : un type inconnu lève une erreur claire plutôt que de produire un circuit silencieusement incomplet.

## 22.4 La fabrique de formes d'onde

Les sources (chapitre 10) ont leur propre sous-fabrique, `_make_source`, car une source combine une *connexion* (tension/courant) et une *forme d'onde* — le découplage du chapitre 10 ([circuit_loader.py](../../circuit_loader.py#L21-L36)) :

```python
def _make_source(params):
    waveform = params.get("waveform", "dc")
    amplitude = float(params.get("amplitude", 0.0))
    if waveform == "dc":
        return DCSource(amplitude)
    elif waveform == "sine":
        return SineSource(amplitude, float(params["frequency"]),
                          float(params.get("phase", 0.0)))
    # ... pulse, square ...
    else:
        raise ValueError(f"Forme d'onde inconnue : '{waveform}'")
```

On retrouve le même esprit : un aiguillage selon `"waveform"`, des valeurs par défaut, une erreur explicite sinon. Ce petit objet source sera ensuite passé au constructeur de `VoltageSource` ou `CurrentSource`, qui l'enveloppe — exactement la composition décrite au chapitre 11.

## 22.5 La validation : pas de circuit sans masse

Charger ne suffit pas ; il faut **valider**. La fonction d'entrée `load_circuit` effectue une vérification cruciale, qui résonne avec tout ce que nous savons depuis le chapitre 1 ([circuit_loader.py](../../circuit_loader.py#L84-L109)) :

```python
def load_circuit(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name = data.get("name", "Sans nom")
    dt = float(data.get("dt", 1e-5))
    components = [_make_component(c) for c in data.get("components", [])]

    # Vérifie qu'au moins un composant est connecté à GND
    all_nodes = set()
    for comp in components:
        all_nodes.update(comp.get_nodes())
    if "GND" not in all_nodes:
        raise ValueError("Le circuit doit contenir au moins un nœud 'GND' (masse).")

    # Détecte les appareils de mesure qui enregistrent un historique
    histories = {}
    for comp in components:
        if comp.records_history:
            histories[comp.id] = comp.history_size

    return Circuit(name=name, dt=dt, components=components, histories=histories)
```

L'absence de `GND` lève une erreur *immédiate*, avant même de tenter une simulation. Pourquoi cette sévérité ? Parce que, nous l'avons vu au chapitre 8, un circuit sans référence à la masse produit une **matrice singulière** : tout flotte, rien n'est calculable. Mieux vaut un message clair au chargement (« il manque la masse ») qu'une erreur obscure d'algèbre linéaire en pleine simulation. C'est un principe de bonne ingénierie : **échouer tôt, et avec un message utile**.

Enfin, le chargeur recense les appareils à historique (`records_history`, chapitre 12) pour préparer leurs files de données. La boucle est bouclée : le fichier texte est devenu un `Circuit` prêt à être confié au moteur du chapitre 21.

## 22.6 À retenir

- Un circuit est décrit en **JSON** : nom, pas de temps `dt`, et liste de composants (type, nœuds, paramètres).
- Le chargeur le traduit en un objet **`Circuit`** (une dataclass : nom, `dt`, composants, historiques).
- Deux **fabriques** (`_make_component`, `_make_source`) aiguillent selon le `"type"` / `"waveform"`, avec des **valeurs par défaut** (`params.get(clé, défaut)`) et une **erreur explicite** pour l'inconnu.
- La **validation** exige au moins un nœud `GND`, sinon erreur immédiate — car sans masse, la matrice serait singulière (chapitre 8). Principe : **échouer tôt, clairement**.

**Dans le prochain chapitre**, nous traiterons la question laissée en suspens depuis le chapitre 13 : comment le thread de simulation et l'interface utilisateur échangent-ils des données **sans se marcher dessus** ? Réponse : l'état partagé et son verrou.
