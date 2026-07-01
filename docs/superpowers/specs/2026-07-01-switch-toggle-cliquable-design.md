# Rectangle cliquable de bascule pour les switches

Date : 2026-07-01
Statut : conception validée

## Objectif

Dans la vue 2D des composants, chaque interrupteur (`switch`) affiche un petit
rectangle coloré que l'utilisateur peut cliquer pour basculer son état **sans
sélectionner le composant** (donc sans changer le panneau de droite :
propriétés en EDIT, détail en RUN).

## Contexte existant

- Le rendu 2D se fait dans `editor/editor_canvas.py`.
  - `_draw_component(comp)` dessine la boîte, le type, l'id et les pattes.
  - `redraw()` redessine tout ; en mode RUN, `unified_app` appelle ensuite
    `draw_live_overlay(node_voltages, comp_states, comp_objects)` toutes les
    200 ms (tag « overlay » supprimé/redessiné à chaque rafraîchissement).
  - `_item_at(x, y)` classe l'item Tkinter cliqué via ses tags
    (`pin_`, `node_`, `wire_`, `comp_`).
  - `_on_press` sélectionne le composant/nœud/wire ou démarre une connexion.
  - Callbacks existants : `set_on_selection_change`, `set_on_model_change`.
- L'état du switch :
  - En EDIT : `comp.params["closed"]` (bool) sur le `ComponentData` du modèle.
  - En RUN : l'objet `simulator.components.Switch` porte `self.closed` et
    expose `toggle()` (déjà prévu « en temps réel » ; docstring existante).
    Le moteur (`simulator/engine.py`) lit `self.closed` dans `stamp()` depuis
    un thread daemon séparé.
- `editor/overlay.py` : `state_indicator(component, comp_state)` renvoie
  `("fermé"/"ouvert", couleur)` pour les switches, `("bloqué"/…)` pour BJT et
  diode. Utilisé par `draw_live_overlay` pour dessiner un texte d'état.

## Comportement cible

Pour chaque `switch`, un rectangle coloré est dessiné en bas de la boîte :

- `closed = True`  → fond vert, libellé « fermé ».
- `closed = False` → fond rouge, libellé « ouvert ».

Un clic sur ce rectangle bascule l'état et **ne modifie pas la sélection**
(pas de `_notify_selection`, pas de démarrage de drag) :

- **EDIT** : bascule `comp.params["closed"]` sur le modèle, appelle
  `model._touch()` (marque le circuit modifié), redessine, `_notify_model()`.
- **RUN** : bascule l'objet `Switch` live via `toggle()`, puis redessine
  immédiatement l'overlay pour un retour visuel instantané (sans attendre le
  prochain rafraîchissement de 200 ms).

### Sûreté vis-à-vis des threads (RUN)

`toggle()` réaffecte un booléen (`self.closed`) et une entrée de dict
(`self.params["closed"]`). Le moteur lit `self.closed` dans `stamp()`. Sous le
GIL, ces opérations sont atomiques : dans le pire cas, la bascule est prise en
compte au pas de simulation suivant. Aucun verrou supplémentaire n'est requis,
conformément à l'usage « temps réel » déjà documenté de `toggle()`.

## Architecture / fichiers touchés

### 1. `editor/editor_canvas.py`

- **Nouvelle méthode** `_draw_switch_toggle(comp, closed, overlay=False)` :
  dessine un rectangle centré horizontalement sur `comp.x`, en bas de la boîte,
  avec libellé « fermé »/« ouvert » et fond vert/rouge. Tag `swtoggle_{comp.id}`
  (plus le tag `"overlay"` quand `overlay=True`, pour être nettoyé/redessiné à
  chaque rafraîchissement RUN). Dessiné par-dessus la boîte → prioritaire au
  clic.
- **`_draw_component`** : en mode EDIT (`not self._read_only`), si
  `comp.type == "switch"`, appelle `_draw_switch_toggle(comp, comp.params.get("closed", False), overlay=False)`.
- **`draw_live_overlay`** : pour un `Switch`, dessine le rectangle cliquable
  (`_draw_switch_toggle(comp, obj.closed, overlay=True)`) **au lieu** du texte
  `state_indicator`. Les autres composants (BJT, diode) conservent leur texte.
- **`_item_at`** : reconnaître le préfixe `swtoggle_` et renvoyer
  `("switch_toggle", comp_id)`. Le rectangle ne porte que ce tag (pas `comp_`),
  donc pas de conflit de classification.
- **`_on_press`** : au tout début du traitement d'un hit (dans les deux
  branches read-only et édition), si `hit[0] == "switch_toggle"` :
  - EDIT : basculer `comp.params["closed"]`, `model._touch()`, `redraw()`,
    `_notify_model()`.
  - RUN : appeler le callback `_on_switch_toggle(comp_id)`.
  - Dans les deux cas : `self._state = "IDLE"`, **`return`** sans toucher à
    `_selected_comp` ni `_notify_selection`, pour ne pas sélectionner ni
    démarrer de drag.
- **Nouveau callback** `set_on_switch_toggle(cb)` (+ attribut
  `self._on_switch_toggle`), pour déléguer la bascule live sans coupler le
  canvas aux objets du simulateur.

### 2. `ui/unified_app.py`

- Câbler `self.canvas.set_on_switch_toggle(self._on_switch_toggle)`.
- `_on_switch_toggle(comp_id)` : si `comp_id in self._comp_objects`, appeler
  `self._comp_objects[comp_id].toggle()`, puis redessiner immédiatement
  l'overlay à partir des dernières données mémorisées.
- `_refresh` : mémoriser les dernières données lues dans `self._last_data`
  (pour permettre le redessin immédiat de l'overlay lors d'une bascule).

### 3. `editor/overlay.py`

- Retirer la branche `Switch` de `state_indicator` (le rectangle cliquable
  remplace désormais le texte « fermé/ouvert »), afin d'éviter un doublon
  d'affichage. Les branches BJT et diode restent inchangées.

## Hors périmètre (YAGNI)

- Pas d'animation de bascule, pas de raccourci clavier.
- Pas de bascule cliquable pour d'autres types de composants.
- Pas de changement du modèle de données ni du format de fichier.

## Critères de réussite

- En EDIT, un switch affiche un rectangle vert « fermé » / rouge « ouvert »
  reflétant `params["closed"]` ; cliquer dessus bascule l'état, marque le
  circuit modifié, sans sélectionner le composant.
- En RUN, le rectangle reflète l'état live du switch ; cliquer dessus bascule
  la simulation en temps réel avec retour visuel immédiat, sans ouvrir le
  panneau détail.
- Cliquer ailleurs sur la boîte du switch sélectionne toujours le composant
  (comportement inchangé).
