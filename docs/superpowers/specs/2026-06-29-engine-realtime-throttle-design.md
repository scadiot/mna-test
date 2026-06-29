# Design — Throttle temps réel du moteur de simulation

Date : 2026-06-29
Statut : approuvé

## Problème

Le moteur ([simulator/engine.py](../../../simulator/engine.py)) exécute un pas MNA par
`dt` secondes de temps réel, synchronisé sur l'horloge murale. Quand un circuit est
trop lourd pour tenir ce rythme (pas plus coûteux que `dt` en temps réel), la boucle
sature un cœur CPU à 100 %.

Deux défauts dans `_run_loop()` :

1. **Ancre fixe** — `t_real_start` est figée au démarrage. `t_ahead = t - t_real_elapsed`
   accumule une dette non bornée ; une fois en retard, le moteur ne dort plus jamais.
2. **Aucun plancher de sleep** — quand `t_ahead <= 1e-4`, la boucle enchaîne les pas
   sans céder le CPU, d'où le spin à 100 %.

Symptôme observé : `circuits/potar_transistor.json` (anciennement `dt=1e-5`, soit
100 000 pas/s visés) sature le CPU. Le `dt` de ce fichier a déjà été ramené à `1e-4`
en correctif ponctuel ; ce design corrige la cause de fond dans le moteur.

## Comportement retenu

« Ralentir proprement » : ne jamais saturer un cœur, quitte à ce que le temps simulé
avance moins vite que le temps réel (slow-motion) quand le circuit est trop lourd.

## Design

### 1. Cadence à échéance ré-ancrée

Remplacer l'ancre globale `t_real_start` par une échéance glissante `next_deadline`.

- **En avance** (`now < next_deadline`) : dormir jusqu'à l'échéance, puis
  `next_deadline += dt`. Comportement temps réel inchangé pour les circuits légers.
- **En retard** (`now >= next_deadline`) : **ré-ancrer** `next_deadline = now + dt`
  au lieu de laisser la dette enfler. Évite tout rattrapage explosif si le circuit
  s'allège ensuite.

### 2. Throttle garanti quand en retard

Quand un pas dépasse `dt` en temps réel, au lieu de spinner, dormir une durée
proportionnelle au temps d'exécution du pas :

```
sleep_throttle = step_duration * THROTTLE_RATIO
```

Cela plafonne l'usage CPU d'un cœur à `1 / (1 + THROTTLE_RATIO)`, indépendamment du
poids du circuit et de la granularité du `sleep` de l'OS.

- `THROTTLE_RATIO = 1.0` → ~50 % d'un cœur au maximum.

### 3. Fonction de timing pure (testabilité)

Extraire la décision de timing dans une fonction pure :

```
_compute_sleep(step_duration, now, next_deadline, dt) -> (sleep_seconds, new_deadline)
```

- Aucun effet de bord, pas d'accès à l'horloge réelle ni au thread.
- La boucle se contente d'appeler `time.sleep(sleep_seconds)` sur son résultat et de
  reprendre `new_deadline`.

Logique :

- `slack = next_deadline - now`
- Si `slack > 0` (en avance) : `sleep = slack`, `new_deadline = next_deadline + dt`.
- Sinon (en retard) : `sleep = step_duration * THROTTLE_RATIO`,
  `new_deadline = now + dt`.

`THROTTLE_RATIO` est une constante de module documentée.

## Impact

- Fichier modifié : `simulator/engine.py` uniquement.
- Aucun changement d'API publique ni de format de circuit JSON.
- Le constructeur, `start()`, `stop()`, `_step()` et `_build_maps()` sont inchangés.

## Tests

Nouveaux tests unitaires sur `_compute_sleep` dans `tests/test_engine.py` :

- **En avance** : `now` avant l'échéance → `sleep == slack > 0`, échéance avancée de `dt`.
- **Pile à l'heure** : `now == next_deadline` → considéré en retard (slack nul),
  throttle appliqué, ré-ancrage.
- **En retard** : `now` après l'échéance → `sleep == step_duration * THROTTLE_RATIO`,
  `new_deadline == now + dt` (ré-ancrage, pas de rattrapage de la dette).
- **Plafond CPU** : pour un `step_duration` donné, vérifier que la fraction
  `step_duration / (step_duration + sleep)` ne dépasse pas `1 / (1 + THROTTLE_RATIO)`.

La fonction étant pure, ces tests n'utilisent ni thread ni horloge réelle.
