# Chapitre 23 — Concurrence et état partagé

> *Où deux fils d'exécution travaillent sur les mêmes données sans se télescoper, grâce à un cadenas, une boîte aux lettres, et la discipline de ne jamais regarder un calcul à moitié fait.*

## 23.1 Deux fils, un problème

Depuis le chapitre 21, nous savons que la simulation tourne dans son **propre fil d'exécution** (thread), en boucle, à grande cadence. Mais elle ne tourne pas seule : un autre acteur — l'interface utilisateur — vit en parallèle. Il veut **lire** les résultats (pour afficher les tensions, tracer les courbes) et parfois **agir** (basculer un interrupteur, chapitre 13).

Deux fils accèdent donc aux mêmes données *en même temps*. C'est la **concurrence**, et elle est source de bugs redoutables. Imaginez : le thread de simulation est en train d'écrire les nouvelles tensions de nœud, et l'interface vient les lire *au beau milieu* de cette écriture. Elle récupérerait un mélange incohérent — la moitié des tensions du nouveau pas, l'autre moitié de l'ancien. Ce genre de bug, appelé **condition de course** (*race condition*), est intermittent, non reproductible, et cauchemardesque à débusquer.

## 23.2 La solution : une boîte aux lettres protégée

Le simulateur résout ce problème en concentrant *toutes* les données partagées dans un unique objet, `SharedState`, qui joue le rôle de **boîte aux lettres** entre les deux fils. Le thread de simulation y dépose ses résultats ; l'interface vient les y chercher. Aucun des deux ne touche directement aux données de l'autre.

Mais une boîte aux lettres ne suffit pas : il faut empêcher qu'on y écrive et qu'on y lise *simultanément*. C'est le rôle d'un **verrou** (*lock*) — un cadenas que l'on doit posséder pour toucher au contenu ([shared_state.py](../../shared_state.py#L8-L17)) :

```python
class SharedState:
    """Contient les données partagées entre le thread simulateur et l'UI."""
    def __init__(self):
        self._lock = threading.Lock()
        self.node_voltages = {}    # tensions aux nœuds
        self.comp_states = {}      # état de chaque composant
        self.histories = {}        # historiques des appareils de mesure
        self.running = False
        self.error = None
```

## 23.3 Le verrou : un seul à la fois

Le principe d'un verrou est simple : il ne peut être détenu que par **un seul fil à la fois**. En Python, on l'utilise avec le mot-clé `with` : tout le bloc à l'intérieur est protégé. Si un fil entre dans le bloc, tout autre fil qui tente d'y entrer **attend** poliment que le premier ait fini et libéré le verrou.

Voyez l'écriture, appelée par le thread de simulation à la fin de chaque pas ([shared_state.py](../../shared_state.py#L25-L32)) :

```python
def write(self, node_voltages, comp_states, history_updates):
    """Écrit les résultats d'un pas (appelé par le thread simulateur)."""
    with self._lock:                       # ← acquiert le verrou
        self.node_voltages = node_voltages
        self.comp_states = comp_states
        for cid, value in history_updates.items():
            if cid in self.histories:
                self.histories[cid].append(value)
    # ← le verrou est libéré en sortant du bloc
```

Et la lecture, appelée par l'interface ([shared_state.py](../../shared_state.py#L34-L43)) :

```python
def read(self):
    """Lit les données courantes (appelé par l'UI)."""
    with self._lock:                       # ← même verrou
        return {
            "node_voltages": dict(self.node_voltages),
            "comp_states": dict(self.comp_states),
            "histories": {k: list(v) for k, v in self.histories.items()},
            "running": self.running,
            "error": self.error,
        }
```

Comme `write` et `read` partagent le **même** verrou (`self._lock`), ils ne peuvent **jamais** s'exécuter en même temps. La lecture attend que l'écriture soit *entièrement* terminée, et vice-versa. La boîte aux lettres n'est jamais consultée à moitié remplie. La condition de course est éliminée.

## 23.4 Copier pour isoler

Un détail subtil mais essentiel dans `read` : on ne renvoie pas directement les dictionnaires internes, mais des **copies** (`dict(self.node_voltages)`, `list(v)`). Pourquoi ?

Parce que si l'on rendait une référence directe à `self.node_voltages`, l'interface continuerait de pointer vers l'objet *vivant* du `SharedState` — que le thread de simulation pourrait modifier juste après, **hors** de la protection du verrou. En renvoyant une copie, on donne à l'interface un **instantané figé**, qu'elle peut consulter tranquillement pendant que la simulation poursuit sa route sur ses propres données. Le verrou protège l'instant de la copie ; la copie protège l'après.

## 23.5 Communiquer dans l'autre sens : les drapeaux

La boîte aux lettres ne sert pas qu'à remonter des résultats ; elle sert aussi à transmettre des **ordres** à la simulation, via de simples **drapeaux** booléens protégés par le même verrou. Nous en avons déjà croisé l'usage :

- **`running`** : la boucle de simulation le vérifie à chaque tour (chapitre 21). L'interface (ou la méthode `stop`) l'abaisse pour demander un arrêt propre ([shared_state.py](../../shared_state.py#L51-L54)) :

```python
def stop(self):
    """Demande l'arrêt propre de la simulation."""
    with self._lock:
        self.running = False
```

- **`error`** : quand le moteur rencontre une matrice singulière (chapitre 8), il appelle `set_error`, qui enregistre le message **et** abaisse `running` d'un même geste ([shared_state.py](../../shared_state.py#L45-L49)). L'interface, à sa prochaine lecture, découvre l'erreur et peut l'afficher.

Ce mécanisme de drapeaux est la forme la plus simple de communication entre fils : on ne s'interrompt pas brutalement, on **dépose une demande** que l'autre fil consultera quand il en aura l'occasion. C'est exactement l'arrêt *coopératif* du chapitre 21.

## 23.6 La philosophie : un point de rendez-vous unique

Reculons d'un pas. La force de cette conception tient à une décision d'architecture : **toute** communication entre les deux fils passe par **un seul objet**, protégé par **un seul verrou**. Il n'y a pas dix endroits où les fils se croisent, mais un seul, soigneusement gardé. Cela rend le raisonnement sur la concurrence **tractable** : pour vérifier qu'il n'y a pas de condition de course, il suffit d'auditer `SharedState`, et rien d'autre.

C'est une leçon qui dépasse ce simulateur : face à la concurrence, on ne saupoudre pas des verrous partout, on **canalise** les échanges vers un point de rendez-vous unique et bien défini. La simplicité est ici une fonctionnalité de sûreté.

## 23.7 À retenir

- La simulation (un thread) et l'interface (un autre) accèdent aux mêmes données : c'est la **concurrence**, source de **conditions de course** si on n'y prend garde.
- Toutes les données partagées sont concentrées dans **`SharedState`**, une boîte aux lettres protégée par un **verrou** (`threading.Lock`).
- `write` et `read` partagent le **même** verrou (`with self._lock`) : ils ne s'exécutent jamais simultanément. On ne lit jamais un état à moitié écrit.
- `read` renvoie des **copies** (`dict(...)`, `list(...)`) : l'interface obtient un **instantané figé**, isolé des modifications ultérieures du moteur.
- Les **drapeaux** `running` et `error` transmettent des ordres en sens inverse (arrêt coopératif, signalement d'erreur).
- Principe d'architecture : **canaliser** toute la concurrence vers **un point de rendez-vous unique** rend le système sûr et auditable.

**Dans le dernier chapitre**, nous prendrons la plus grande hauteur : quelles sont les **limites** de ce simulateur, que sacrifie-t-il par rapport à un outil professionnel, et comment l'**étendre** — en y ajoutant, par exemple, votre propre composant ?
