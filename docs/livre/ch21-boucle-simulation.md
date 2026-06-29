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

Un pas calcule un instant `t`. Pour simuler la durée, il faut les enchaîner en incrémentant `t` de `dt` à chaque tour. C'est le rôle de `_run_loop` ([simulator/engine.py](../../simulator/engine.py#L126-L154)) :

```python
def _run_loop(self):
    t = 0.0
    with self._state._lock:
        self._state.running = True

    # échéance temps réel glissante, ré-ancrée en cas de retard (§21.4)
    next_deadline = time.monotonic() + self._dt

    while True:
        with self._state._lock:
            if not self._state.running:    # arrêt demandé ?
                break

        step_start = time.monotonic()
        ok = self._step(t)
        if not ok:
            break                          # erreur MNA → arrêt propre
        step_duration = time.monotonic() - step_start

        t += self._dt

        # combien dormir ? (calcul délégué à une fonction pure, voir §21.4)
        sleep_s, next_deadline = _compute_sleep(
            step_duration, time.monotonic(), next_deadline, self._dt
        )
        if sleep_s > 0:
            time.sleep(sleep_s)
```

La structure est une boucle « tant que ça tourne » : on vérifie le drapeau `running` (qui peut être abaissé de l'extérieur, chapitre 13), on **chronomètre** puis on exécute un pas, on avance le temps simulé, puis on se synchronise. Si un pas échoue (`ok` faux), on sort proprement.

## 21.4 Le temps simulé contre le temps réel

Voici la partie la plus astucieuse, et la raison d'être d'un simulateur *temps réel*. Il y a **deux horloges** distinctes :

- le **temps simulé** `t` : celui du circuit, qui avance par bonds de `dt` ;
- le **temps réel** : celui de votre montre, mesuré par `time.monotonic()`.

L'objectif est que les deux **coïncident** : une seconde simulée doit s'écouler en une seconde réelle, pour qu'un signal de `50 Hz` clignote effectivement 50 fois par seconde à l'écran. Or l'ordinateur calcule chaque pas bien plus vite que `dt`. Sans précaution, il « foncerait » : mille pas en un clin d'œil, et le temps simulé s'envolerait.

La décision « combien de temps dormir ? » est isolée dans une **fonction pure** — sans état ni effet de bord, donc testable sans lancer aucun thread ([simulator/engine.py](../../simulator/engine.py#L14-L33)) :

```python
THROTTLE_RATIO = 1.0   # plafonne l'occupation CPU à 1/(1+ratio) ≈ 50 % d'un cœur

def _compute_sleep(step_duration, now, next_deadline, dt):
    slack = next_deadline - now
    if slack > 0:
        # en avance : on dort le temps restant, l'échéance avance de dt
        return slack, next_deadline + dt
    # en retard : on ne spinne pas. On dort proportionnellement au coût du
    # pas (throttle) et on ré-ancre l'échéance sur « now » pour ne pas
    # accumuler de dette → ralenti à CPU borné.
    return step_duration * THROTTLE_RATIO, now + dt
```

On y reconnaît une **échéance glissante** `next_deadline`, l'instant réel visé pour le pas courant. Deux cas se présentent :

- **En avance** (`slack > 0`, le cas normal car le calcul est rapide) : on **dort** le temps restant jusqu'à l'échéance, puis on avance celle-ci de `dt`. La simulation se **cale sur l'horloge murale** — c'est ce qui la rend « temps réel ».

- **En retard** (`slack ≤ 0`, circuit lourd ou machine chargée) : naïvement, on serait tenté de ne pas dormir du tout et d'enchaîner au plus vite. **C'est exactement le piège** : sans aucune pause, la boucle **sature un cœur CPU à 100 %** pour rien, puisqu'elle ne pourra de toute façon pas rattraper le temps réel. La parade est de dormir une durée **proportionnelle au coût du pas** (`step_duration * THROTTLE_RATIO`) : avec `THROTTLE_RATIO = 1.0`, on passe autant de temps à dormir qu'à calculer, ce qui **borne l'occupation à ~50 % d'un cœur**. On ré-ancre alors l'échéance sur `now` pour ne pas accumuler une dette de retard impossible à combler. La simulation tourne au **ralenti**, mais sans jamais faire chauffer le processeur ni se figer.

Le découpage en fonction pure n'est pas un caprice : il rend ce calcul délicat **vérifiable par de simples tests unitaires** (on lui passe des valeurs et on inspecte le `(sleep, deadline)` retourné), sans avoir à orchestrer de threads ni à mesurer du temps réel.

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
- Le calcul du sommeil est délégué à une **fonction pure** `_compute_sleep` (testable sans thread). En avance, on dort le *slack* jusqu'à l'échéance ; **en retard, on dort quand même** une fraction proportionnelle au coût du pas (`THROTTLE_RATIO`) pour **borner l'occupation CPU** (~50 % d'un cœur) au lieu de saturer un cœur à 100 % en pure perte.
- La boucle tourne dans un **thread démon** (`daemon=True`), lancé par `start` et arrêté **coopérativement** par `stop` (drapeau `running` puis `join`).

**Dans le prochain chapitre**, nous remonterons en amont du moteur : d'où vient le circuit ? Nous verrons comment un simple fichier **JSON** se transforme en une liste d'objets composants prêts à être simulés.
