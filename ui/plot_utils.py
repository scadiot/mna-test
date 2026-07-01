"""Helpers de tracé sans dépendance GUI (testables en headless).

Regroupe le choix d'unité de temps et la préparation des données pour les
graphes des appareils de mesure (voltmètres / ampèremètres).
"""
from ui.trigger import compute_trigger_window


def time_unit(duration):
    """Choisit une unité de temps lisible pour une durée donnée (en s).

    Renvoie (libellé, facteur) tel que `valeur_en_s * facteur` donne la
    valeur exprimée dans l'unité retournée.
    """
    if duration >= 1.0:
        return "s", 1.0
    if duration >= 1e-3:
        return "ms", 1e3
    if duration >= 1e-6:
        return "µs", 1e6
    return "ns", 1e9


def shared_trigger_window(ref_history, trigger_on):
    """Fenêtre (start, end) commune à toutes les courbes, ou None.

    Calculée sur le signal de référence : demi-buffer affiché, demi réservé
    à la recherche de front, niveau = moyenne du signal. Renvoie None (=
    afficher le buffer complet) si le déclenchement est désactivé, si la
    référence est vide, ou si aucun front n'est trouvé.
    """
    if not trigger_on or not ref_history:
        return None
    width = len(ref_history) // 2 or len(ref_history)
    level = sum(ref_history) / len(ref_history)
    return compute_trigger_window(ref_history, width, level)


def _meter_unit(comp):
    """Renvoie 'V' pour un voltmètre, 'A' sinon (heuristique par nom de classe)."""
    return "V" if "voltmeter" in type(comp).__name__.lower() else "A"


def build_combined_series(histories, comp_objects, window):
    """Prépare les courbes à tracer pour la vue combinée.

    Renvoie [(label, ys), ...] pour chaque appareil ayant `records_history`
    et un historique non vide, dans l'ordre de `comp_objects`. `label` porte
    l'ID et l'unité. `ys` est découpé selon `window=(start, end)` si fourni,
    sinon le buffer complet.
    """
    series = []
    for cid, comp in comp_objects.items():
        if not getattr(comp, "records_history", False):
            continue
        hist = histories.get(cid)
        if not hist:
            continue
        if window is not None:
            start, end = window
            ys = list(hist[start:end])
        else:
            ys = list(hist)
        series.append((f"{cid} ({_meter_unit(comp)})", ys))
    return series
