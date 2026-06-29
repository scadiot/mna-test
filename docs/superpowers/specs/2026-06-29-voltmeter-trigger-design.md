# Déclenchement (trigger) d'oscilloscope pour le graphe de mesure

Date : 2026-06-29
Statut : approuvé

## Problème

L'affichage du graphe d'historique des voltmètres/ampèremètres est instable :
la trace « saute » à chaque rafraîchissement. Cause : le moteur ajoute un
échantillon par pas de temps `dt` dans un `deque` ([shared_state.py](../../../shared_state.py)),
tandis que l'UI rafraîchit à 5 Hz et trace **tout le buffer aligné à droite**
([detail_panel.py](../../../ui/detail_panel.py)). Entre deux frames, un nombre
**variable** d'échantillons est ajouté, donc la sinusoïde glisse vers la gauche
d'une quantité variable → effet de saut.

## Objectif

Stabiliser visuellement la trace en ré-ancrant, à chaque frame, la fenêtre
affichée sur un front montant du signal — principe du déclenchement
(trigger) d'oscilloscope. La sinusoïde apparaît alors stationnaire.

## Principe général

Transformation **purement côté affichage**, dans `ui/detail_panel.py`. Le moteur
de simulation, le `SharedState` et la collecte d'historique sont **inchangés**.

## Algorithme du trigger

Appliqué dans `DetailPanelWidget.update`, à chaque frame, quand le déclenchement
est actif :

1. **Niveau auto** : `level = moyenne(history)`. Gère un signal centré sur 0
   comme un signal avec offset DC (ex. sortie d'AOP non-inverseur).
2. **Largeur d'affichage fixe** : `W = len(history) // 2`. La moitié restante du
   buffer sert de marge de recherche de front. L'axe X reste **figé** à
   `0..W-1` en permanence (déclenché comme en repli).
3. **Détection des fronts montants** : indices `i` tels que
   `history[i-1] < level <= history[i]`.
4. **Choix du front** : on retient le front montant **le plus récent** tel que
   `c + W <= len(history)`, et on affiche `history[c : c+W]`. Tous les fronts
   montants ayant la même phase, la trace affichée est identique d'une frame à
   l'autre → **stable**. Le décalage par rapport aux données les plus récentes
   est inférieur à une période.
5. **Repli** : si aucun front éligible n'existe (signal continu, plat, bruit non
   périodique, ou buffer pas encore assez rempli), on affiche les `W` derniers
   échantillons alignés à droite — comportement actuel — sur le même axe
   `0..W-1`. Si le buffer contient moins de `W` points (remplissage initial), on
   affiche ce qui est disponible aligné à droite.

## Fonction pure testable

Extraire la logique de calcul de fenêtre dans une fonction pure, indépendante de
tkinter/matplotlib, pour la tester unitairement :

```
_compute_trigger_window(history, width, level) -> (start, end) | None
```

- Renvoie les indices `(start, end)` de la fenêtre déclenchée (front montant le
  plus récent éligible), ou `None` si aucun front éligible.
- `update` appelle cette fonction ; sur `None`, applique le repli aligné à droite.

## Contrôle UI

Case à cocher **« Déclenchement »** ajoutée dans le panneau de détail :

- Visible **uniquement** pour les appareils de mesure (`records_history`),
  gérée dans `show_component` selon le même cycle de vie que le bouton toggle de
  l'interrupteur et le slider du potentiomètre (création/destruction au clic).
- **Cochée par défaut** : le trigger s'applique d'emblée.
- Décochée → ancien comportement (défilement de tout le buffer aligné à droite).
- État stocké dans un `tk.BooleanVar`.

## Capture

Pour que le trigger dispose de plus d'une période, augmenter `history_size` dans
les circuits sinusoïdaux : `dt = 1e-5` et `frequency = 100 Hz` donnent
1000 échantillons/période, donc `history_size = 3000` capture ~3 périodes.

- Circuits concernés : `opamp_noninverting.json`, `opamp_inverting.json`,
  `rc_filter.json`, et `diode_bridge.json` / `diode_bridge_filtered.json` si
  pertinent.
- Documenter dans le README la règle : `history_size` ≥ ~2× la durée d'affichage
  souhaitée (pour laisser une marge de recherche de front au trigger).

## Hors périmètre

- La logique actuelle qui force la ligne 0 V à rester visible
  ([detail_panel.py:120-125](../../../ui/detail_panel.py#L120-L125)) peut aplatir
  un signal à fort offset DC. Non traité ici, sauf demande explicite.
- Aucun changement au moteur, au `SharedState`, ni à la collecte d'historique.

## Tests

Tests unitaires de `_compute_trigger_window` (sans tkinter) :

- Front montant détecté sur une sinusoïde, fenêtre commençant au front.
- Choix du front montant **le plus récent** éligible parmi plusieurs.
- Repli (`None`) quand aucun front montant éligible.
- Signal continu/plat → `None`.
- Buffer plus court que `width` → `None` (repli géré par l'appelant).
- Stabilité : même phase de départ pour des buffers décalés d'un nombre
  arbitraire d'échantillons.
