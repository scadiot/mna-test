# Vue combinée multi-courbes — Design

Date : 2026-07-01

## Objectif

Permettre d'afficher les historiques de **tous** les appareils de mesure
(voltmètres et ampèremètres) d'un circuit sur **un seul graphe**, chaque courbe
d'une couleur différente, afin d'**observer les déphasages** entre les signaux.

## Choix validés

- **Accès** : vue par défaut du panneau droit en mode RUN tant qu'**aucun**
  appareil n'est sélectionné. Cliquer sur un appareil rebascule sur la vue
  détaillée d'un seul appareil (comportement actuel inchangé).
- **Échelles** : un **seul axe Y**, courbes tracées en **valeurs brutes**
  (pas de normalisation, pas de double axe).
- **Déclenchement** : déclenchement sur un **appareil de référence**. La fenêtre
  déclenchée est calculée sur le signal de référence puis appliquée à l'identique
  à toutes les courbes.
- **Choix de la référence** : **menu déroulant** listant les appareils + case
  **« Déclenchement »** pour activer/désactiver (repli sur buffer complet si off).

## Architecture

Nouveau widget `CombinedGraphWidget` dans `ui/combined_panel.py`, frère de
`DetailPanelWidget`. Il possède sa propre `Figure` / `FigureCanvasTkAgg` et ses
contrôles :

- une case à cocher **« Déclenchement »** (activée par défaut) ;
- un **menu déroulant** de sélection de l'appareil de référence.

Dans `ui/unified_app.py`, le panneau droit gère désormais **trois** panneaux
permutés par `pack` / `pack_forget` :

| Panneau    | Quand                                             |
|------------|---------------------------------------------------|
| `props`    | mode EDIT                                          |
| `detail`   | mode RUN, un appareil sélectionné                 |
| `combined` | mode RUN, **aucun** appareil sélectionné          |

Aiguillage :

- `_start_run` : peuple la liste des appareils du widget combiné et affiche le
  panneau `combined` par défaut (`_selected_run_id` vaut `None`).
- `_on_selection` (RUN) : si un appareil de mesure est sélectionné → afficher
  `detail` ; sinon → afficher `combined`.
- `_refresh` : si `_selected_run_id` → `detail.update(...)` (inchangé) ; sinon →
  `combined.update(histories, comp_objects, dt)`.

Aucune modification du simulateur ni de `SharedState` : les données existent déjà
dans `data["histories"]` (historique de tous les appareils) et `_comp_objects`.

## Flux de données

À chaque rafraîchissement (5 Hz), `_refresh` lit `SharedState.read()` puis, en
l'absence de sélection, appelle `CombinedGraphWidget.update(histories,
comp_objects, dt)` avec :

- `histories` : `{id: [float, ...]}` pour tous les appareils ;
- `comp_objects` : `{id: composant}` (pour le type/unité et `records_history`) ;
- `dt` : pas de simulation (pour l'axe temps).

## Tracé et déclenchement

`CombinedGraphWidget.update` :

1. Sélectionne les appareils ayant `records_history` et un historique non vide.
2. **Déclenchement** :
   - Si la case est cochée et une référence valide est choisie : calcule
     `(start, end)` via `compute_trigger_window(ref_history, width, level)` où
     `width = len(ref_history) // 2` (ou la longueur totale si trop court) et
     `level = moyenne(ref_history)`. Applique le **même** découpage `[start:end]`
     à **toutes** les courbes.
   - Si décoché, ou front introuvable (`None`), ou pas de référence : repli sur
     le **buffer complet** aligné à droite (même base de temps pour toutes).
3. Trace une courbe par appareil, couleur issue d'une **palette cyclique**, avec
   une **légende** affichant l'ID et l'unité (ex. `V1 (V)`, `A1 (A)`).
4. Axe X en temps via l'utilitaire `_time_unit` existant (factorisé pour être
   partagé entre `detail_panel` et `combined_panel`). Un seul axe Y libellé
   `Valeur (V / A)`. Ligne des 0 en pointillés, grille légère.
5. Si aucun appareil n'a d'historique : affiche un message d'invite.

Comme toutes les deques partagent la même `maxlen` et sont alimentées au même
rythme (un `append` par pas pour chaque appareil), les indices sont alignés :
appliquer un unique `(start, end)` préserve exactement les déphasages relatifs.

## Contrôles

- **Menu déroulant de référence** : peuplé au démarrage RUN avec les IDs des
  appareils de mesure. Si la liste change (elle ne change pas en cours de RUN),
  la valeur par défaut est le premier appareil.
- **Case « Déclenchement »** : cochée par défaut ; décochée → buffer complet.

## Gestion des cas limites

- Aucun appareil de mesure dans le circuit → message « Aucun appareil de mesure ».
- Historique encore vide au tout début → rien à tracer (attendre le remplissage).
- Référence sélectionnée dont l'historique est vide → repli buffer complet.

## Facteur de refactor

`_time_unit` est actuellement local à `ui/detail_panel.py`. Il sera déplacé dans
un module partagé (ex. `ui/plot_utils.py`) et importé par les deux panneaux, pour
éviter la duplication.

## Tests

- La logique de fenêtre déclenchée est déjà couverte par les tests de
  `compute_trigger_window` (`tests/test_trigger.py`).
- Ajout d'un test headless vérifiant qu'un unique `(start, end)` appliqué à
  plusieurs historiques de même longueur préserve l'alignement des indices
  (donc le déphasage) : deux signaux sinusoïdaux déphasés, découpés avec la même
  fenêtre, conservent leur écart de phase.
- Le tracé GUI lui-même n'est pas testé unitairement, cohérent avec l'existant.

## Hors périmètre (YAGNI)

- Pas de normalisation ni de double axe Y.
- Pas de sélection d'un sous-ensemble d'appareils (toutes les courbes affichées).
- Pas de curseurs de mesure de déphasage ni de calcul numérique du déphasage.
- Pas de zoom/pan interactif au-delà de ce que matplotlib fournit par défaut.
