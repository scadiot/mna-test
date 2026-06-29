# Chapitre 21 — La boucle de simulation

> *Où l'on prend de la hauteur pour voir la machine tourner : un pas après l'autre, à la cadence de l'horloge, dans un fil d'exécution qui ne bloque jamais le reste du programme.*

## 21.1 De la pièce au moteur

Les vingt premiers chapitres ont décortiqué les *pièces* : composants, stamping, résolution, mémoire. Il est temps de reculer et de regarder le **moteur** dans son ensemble — comment ces pièces s'enchaînent, pas après pas, pour donner vie à un circuit.

Tout repose sur deux méthodes de la classe `SimulationEngine` : `_step`, qui calcule **un** instant, et `_run_loop`, qui enchaîne les instants à la bonne cadence. Étudions-les dans cet ordre.

## 21.2 Anatomie d'un pas : `_step`

Un pas de simulation est exactement le cycle que nous avons assemblé au fil du livre. Le voici en entier ([simulator/engine.py](../../simulator/engine.py#L48-L96)), que vous devriez maintenant lire **sans aucune surprise** :

```python
def _step(self, t):
    size = len(self._node_map) + len(self._branch_map)
    G = np.zeros((size, size))
    b = np.zeros(size)

    # 1. Chaque composant ajoute sa contribution à G et b
    for comp in self._components:
        prev = self._prev_states[comp.id]
        comp.stamp(G, b, self._node_map, self._branch_map, self._dt, t, prev)

    # 2. Résolution du système linéaire G·x = b
    try:
        x = np.linalg.solve(G, b)
    except np.linalg.LinAlgError as e:
        self._state.set_error(f"Matrice singulière à t={t:.6f}s : {e}")
        return False

    # 3. Extraction des tensions et des états
    node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
    node_voltages["GND"] = 0.0
    # ... get_state de chaque composant, recalcul des courants réactifs ...

    # 4. Mémorisation et publication
    self._prev_states = comp_states
    self._state.write(node_voltages, comp_states, history_updates)
    return True
```

Quatre temps, tous déjà connus :

1. **Assembler** : créer `G` et `b` vides, puis laisser chaque composant se tamponner (chapitres 6, 7, 16). C'est ici que `prev_state` est lu — la mémoire du chapitre 14.
2. **Résoudre** `G·x = b`, avec le rattrapage de la matrice singulière (chapitre 8).
3. **Extraire** : les tensions de nœud, la masse à 0 V, puis l'état de chaque composant via `get_state`, et le recalcul des courants réactifs (chapitre 16).
4. **Mémoriser** (`_prev_states = comp_states`) et **publier** les résultats dans l'état partagé (chapitre 23).

Le `return False` en cas d'erreur est important : il signale à la boucle qu'il faut s'arrêter proprement, sans planter.

## 21.3 Enchaîner les pas : `_run_loop`

Un pas calcule un instant `t`. Pour simuler la durée, il faut les enchaîner en incrémentant `t` de `dt` à chaque tour. C'est le rôle de `_run_loop` ([simulator/engine.py](../../simulator/engine.py#L98-L125)) :

```python
def _run_loop(self):
    t = 0.0
    with self._state._lock:
        self._state.running = True

    t_real_start = time.monotonic()        # temps de référence

    while True:
        with self._state._lock:
            if not self._state.running:    # arrêt demandé ?
                break

        ok = self._step(t)
        if not ok:
            break                          # erreur MNA → arrêt propre

        t += self._dt

        # synchronisation avec le temps réel (voir §21.4)
        t_real_elapsed = time.monotonic() - t_real_start
        t_ahead = t - t_real_elapsed
        if t_ahead > 1e-4:
            time.sleep(t_ahead)
```

La structure est une boucle « tant que ça tourne » : on vérifie le drapeau `running` (qui peut être abaissé de l'extérieur, chapitre 13), on exécute un pas, on avance le temps simulé, puis on se synchronise. Si un pas échoue (`ok` faux), on sort proprement.

## 21.4 Le temps simulé contre le temps réel

Voici la partie la plus astucieuse, et la raison d'être d'un simulateur *temps réel*. Il y a **deux horloges** distinctes :

- le **temps simulé** `t` : celui du circuit, qui avance par bonds de `dt` ;
- le **temps réel** : celui de votre montre, mesuré par `time.monotonic()`.

L'objectif est que les deux **coïncident** : une seconde simulée doit s'écouler en une seconde réelle, pour qu'un signal de `50 Hz` clignote effectivement 50 fois par seconde à l'écran. Or l'ordinateur calcule chaque pas bien plus vite que `dt`. Sans précaution, il « foncerait » : mille pas en un clin d'œil, et le temps simulé s'envolerait.

La parade est ce petit calcul de fin de boucle :

```python
t_ahead = t - t_real_elapsed     # de combien le simulé est-il en avance ?
if t_ahead > 1e-4:
    time.sleep(t_ahead)          # on patiente pour laisser le réel rattraper
```

Si le temps simulé a pris de l'avance sur le temps réel (le cas normal, car le calcul est rapide), on **dort** juste ce qu'il faut pour que le réel rattrape. Le `1e-4` (100 µs) est une marge : inutile de dormir pour des écarts infimes. Résultat : la simulation **se cale sur l'horloge murale**. Si, à l'inverse, les calculs étaient trop lents (`t_ahead` négatif), on ne dort pas et on enchaîne au plus vite — la simulation ralentirait alors par rapport au réel, mais sans jamais se figer.

## 21.5 Un fil d'exécution dédié

Une dernière question : *qui* appelle `_run_loop` ? Si on l'appelait directement, la boucle infinie **bloquerait** tout le programme — plus aucune interface, plus aucune interaction. La simulation tourne donc dans un **fil d'exécution séparé** (un *thread*), lancé par `start` ([simulator/engine.py](../../simulator/engine.py#L127-L136)) :

```python
def start(self):
    self._thread = threading.Thread(target=self._run_loop, daemon=True)
    self._thread.start()

def stop(self):
    self._state.stop()                 # abaisse le drapeau running
    if self._thread:
        self._thread.join(timeout=1.0) # attend la fin du thread
```

Deux détails comptent :

- **`daemon=True`** : ce thread est un « démon », il ne survit pas au programme principal. Quand l'application se ferme, la simulation s'arrête d'elle-même, sans laisser de fil zombie.
- **L'arrêt en deux temps** : `stop` abaisse d'abord le drapeau `running` (ce que la boucle vérifie à chaque tour), puis attend que le thread se termine (`join`). C'est un arrêt **coopératif** et propre, pas une interruption brutale.

Le fait que la simulation tourne dans son propre fil, pendant que l'utilisateur agit depuis un autre (en basculant un interrupteur, chapitre 13), pose la question de la **cohabitation** de ces deux fils. C'est tout le sujet du chapitre 23.

## 21.6 À retenir

- Le moteur s'articule en deux méthodes : **`_step`** (calcule un instant) et **`_run_loop`** (enchaîne les instants).
- Un **pas** suit toujours les quatre temps : **assembler** (stamping, lecture de `prev_state`) → **résoudre** (`np.linalg.solve` + rattrapage singulier) → **extraire** (tensions, états) → **mémoriser & publier**.
- Deux horloges coexistent : le **temps simulé** `t` (par bonds de `dt`) et le **temps réel** (`time.monotonic`). La boucle **dort** (`time.sleep`) pour les caler l'une sur l'autre — c'est ce qui rend la simulation « temps réel ».
- La boucle tourne dans un **thread démon** (`daemon=True`), lancé par `start` et arrêté **coopérativement** par `stop` (drapeau `running` puis `join`).

**Dans le prochain chapitre**, nous remonterons en amont du moteur : d'où vient le circuit ? Nous verrons comment un simple fichier **JSON** se transforme en une liste d'objets composants prêts à être simulés.
