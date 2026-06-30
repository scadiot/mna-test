# Intégration de l'éditeur dans l'application principale

**Date :** 2026-06-30
**Statut :** Design validé, en attente de revue utilisateur

## Objectif

Fusionner l'éditeur de circuits (`editor/`) et le simulateur (`ui/`) en une **application
unique** où l'on dessine et simule un circuit dans une **vue canvas unique**, sans passer
par le disque. Pendant la simulation, le schéma affiche les résultats live (tensions,
couleurs, états des composants) en superposition.

## Décisions de cadrage

| Question | Décision |
|----------|----------|
| Modèle UX | Vue unique : un seul canvas pour éditer **et** afficher les résultats live |
| Édition vs simulation | **Deux modes distincts** : EDIT (canvas éditable) / RUN (canvas figé en lecture seule). Pas de reconstruction du moteur à chaud |
| Overlay live | Tensions aux nœuds (texte) + code couleur des nœuds + indicateurs d'état des composants actifs |
| Graphe oscilloscope | Panneau latéral conservé : le graphe défilant du mètre sélectionné (réutilise `ui/detail_panel.py`) |
| Structure code | Approche A : nouvel orchestrateur `UnifiedApp(tk.Tk)` réutilisant les widgets existants |
| Anciens lanceurs | Retirer la fenêtre simulateur seule (`ui/app.py`) et le lanceur éditeur seul (`editor/main.py`) |

## Architecture

`UnifiedApp(tk.Tk)` est un orchestrateur fin qui coordonne des widgets spécialisés
existants et gère la machine à états, le moteur de simulation et le `SharedState`.

```
┌────────────────────────────────────────────────────────────────┐
│ Barre : 📄Nouveau 📂Ouvrir 💾Enregistrer 💾+ │ ▶Démarrer  ⏱état │
├──────────┬───────────────────────────────────┬──────────────────┤
│ Palette  │            Canvas                  │  Panneau droit   │
│ composants│  édition (mode EDIT)              │  EDIT→Propriétés │
│ (drag)   │  + overlay live (mode RUN)         │  RUN →Graphe osc.│
│ [gelée   │  [gelé en lecture seule en RUN]    │  (du mètre       │
│  en RUN] │                                    │   sélectionné)   │
└──────────┴───────────────────────────────────┴──────────────────┘
```

### Composants réutilisés

| Widget | Rôle dans l'app unifiée | Modification |
|--------|--------------------------|--------------|
| `editor.editor_canvas.EditorCanvas` | Centre : édition + overlay live | Ajout d'un mode lecture seule et d'une couche d'overlay |
| `editor.component_panel.ComponentPanel` | Palette gauche (drag-drop) | Désactivable en mode RUN |
| `editor.properties_panel.PropertiesPanel` | Panneau droit en mode EDIT | Aucune (réutilisé tel quel) |
| `ui.detail_panel.DetailPanelWidget` | Panneau droit en mode RUN (graphe) | Aucune (réutilisé tel quel) |
| `simulator.engine.SimulationEngine` | Moteur MNA | Aucune |
| `shared_state.SharedState` | Pont thread simu → UI | Aucune |
| `circuit_loader` | Construction du `Circuit` | Factorisation (voir Pont de données) |

## Machine à états : EDIT ↔ RUN

- **EDIT** (état initial) : palette active, canvas éditable, panneau droit =
  `PropertiesPanel`, bouton « ▶ Démarrer ».
- **Transition EDIT → RUN** (clic « Démarrer ») :
  1. **Valider** le modèle : au moins un nœud `GND` ; toutes les pattes des composants
     sont connectées à un nœud. Si invalide → `messagebox` avec un message clair listant
     le problème, on reste en EDIT.
  2. Construire un `Circuit` **en mémoire** depuis le `CircuitModel` (voir Pont de données).
     Toute erreur de construction (`ValueError`) → message clair, retour EDIT.
  3. Réinitialiser un `SharedState` neuf ; initialiser les historiques des mètres
     (`init_histories`).
  4. Créer et démarrer le `SimulationEngine` ; passer le canvas en lecture seule ;
     désactiver la palette ; basculer le panneau droit vers `DetailPanelWidget` ;
     bouton → « ⏹ Arrêter ».
- **RUN** : refresh UI à 5 Hz (`after`, comme l'existant). À chaque tick, lecture du
  `SharedState` ; le canvas redessine le schéma + overlay live ; le panneau droit met à
  jour le graphe du mètre sélectionné. Le clic sur le canvas **sélectionne** un composant
  (pour choisir le mètre affiché) mais **n'autorise aucune mutation**.
- **Transition RUN → EDIT** (clic « Arrêter », ou fermeture fenêtre) :
  `engine.stop()` ; canvas repasse éditable ; palette réactivée ; overlay effacé ;
  panneau droit = `PropertiesPanel` ; bouton → « ▶ Démarrer ».

## Pont de données (point clé)

Le dict JSON produit par `editor.io.save_circuit` est **déjà** exactement le format que
lit `circuit_loader.load_circuit`. On exploite cela pour simuler sans passer par le disque :

1. **Factoriser `circuit_loader`** : extraire une fonction
   `build_circuit(data: dict) -> Circuit` contenant la logique actuelle de `load_circuit`
   (création des composants, vérification GND, détection des historiques). `load_circuit`
   devient :
   ```python
   def load_circuit(path):
       with open(path, "r", encoding="utf-8") as f:
           return build_circuit(json.load(f))
   ```
2. **Helper `model_to_dict(model: CircuitModel) -> dict`** : produit le même dict que
   `editor.io.save_circuit` (réutilisant/partageant sa logique de sérialisation) **sans
   écrire de fichier**. Emplacement : `editor/io.py` (à côté de `save_circuit`), de sorte
   que `save_circuit` puisse s'appuyer dessus (`json.dump(model_to_dict(model), ...)`).
3. Au démarrage de la simulation : `circuit = build_circuit(model_to_dict(self.model))`.

Conséquence : le **Run simule toujours l'état courant à l'écran**, qu'il soit sauvegardé
sur disque ou non.

## Gel du canvas (`EditorCanvas`)

Ajout d'un attribut `read_only` (défaut `False`) et d'une méthode `set_read_only(bool)`.
En lecture seule :
- `_on_press` : ne fait que la **sélection** d'un composant/nœud (notification de sélection
  conservée) ; n'entre jamais dans les états `CONNECTING` ni `DRAGGING`.
- `_on_motion`, `_on_double_click`, `_on_delete` : retour immédiat (no-op).
- `drop_component` (drag-drop depuis la palette) : ignoré (la palette est de toute façon
  désactivée).

Le retour en mode EDIT restaure le comportement normal (aucun état persistant à nettoyer
au-delà de la sélection courante).

## Overlay live (`EditorCanvas`)

Nouvelle méthode `draw_live_overlay(node_voltages: dict, comp_states: dict)`, appelée après
le `redraw()` standard en mode RUN. Les items d'overlay portent un tag `"overlay"` (effaçables
indépendamment au retour en EDIT). Trois rendus :

1. **Tensions aux nœuds** : étiquette texte `« 3.27 V »` près de chaque nœud, à sa position
   connue (`node.x, node.y`). GND affiche `0 V`.
2. **Code couleur des nœuds** : remplissage du disque-nœud selon sa tension, sur une échelle
   bleu → rouge bornée au `[min, max]` des tensions courantes du circuit (recalculé à chaque
   tick). GND reste noir.
3. **État des composants actifs** : indicateur visuel dérivé de `comp_states` :
   - `switch` : ouvert / fermé,
   - `transistor_bjt` : bloqué / saturé / actif,
   - `diode` : passante / bloquée.
   La logique « état → libellé/couleur » est une **fonction pure** (sans Tk), testable
   isolément.

## Point d'entrée et nettoyage

- `main.py` instancie et lance `UnifiedApp`.
- **Suppression** de `ui/app.py` (fenêtre simulateur seule) et `editor/main.py` (lanceur
  éditeur seul), désormais redondants.
- `ui/component_list.py` : la liste cliquable du simulateur n'est plus utilisée dans la vue
  unique (la sélection se fait sur le canvas). À **retirer** si plus aucun consommateur.
- Mettre à jour `README.md` (lancement unique `python main.py`, suppression des sections
  obsolètes) et `editor/README.md`.

## Gestion des erreurs

- **Validation pré-run** : GND absent ou pattes non connectées → `messagebox` clair, reste
  en EDIT (pas de démarrage moteur).
- **Erreur de construction** (`build_circuit` lève `ValueError`) → `messagebox`, reste en EDIT.
- **Crash moteur en cours de run** : `SharedState.error` est déjà remonté ; l'app l'affiche
  dans la barre d'état et repasse en EDIT (comme le simulateur actuel).
- **Modifications non sauvegardées** : la logique `is_dirty` / confirmation existante de
  l'éditeur est conservée pour Nouveau / Ouvrir / fermeture.

## Tests

Tests unitaires (sans Tk) :
- `build_circuit(dict)` : round-trip `CircuitModel → model_to_dict → build_circuit`,
  présence de GND, types de composants, détection des historiques.
- `model_to_dict(model)` : équivalence avec le dict écrit par `save_circuit` (même contenu).
- Validation pré-run : détecte GND manquant et pattes non connectées.
- Mapping `comp_states → (libellé, couleur)` d'état (fonction pure).

Le rendu Tkinter (canvas, overlay) n'est pas testé unitairement, cohérent avec la couverture
existante du projet.

## Hors périmètre (YAGNI)

- Édition à chaud pendant la simulation (modes distincts assumés).
- Affichage des valeurs courant/tension par composant sur le schéma (non retenu).
- Animation de flux de courant, sondes déplaçables, multi-circuits/onglets.
