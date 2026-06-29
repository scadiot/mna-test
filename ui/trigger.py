"""Calcul de la fenêtre d'affichage déclenchée (trigger d'oscilloscope).

Module sans dépendance GUI : volontairement testable en headless.
"""


def compute_trigger_window(history, width, level):
    """Renvoie (start, end) de la fenêtre déclenchée, ou None.

    Cherche le front montant le plus récent — indice i tel que
    history[i-1] < level <= history[i] — qui laisse assez d'échantillons
    pour afficher `width` points (i + width <= len(history)). Comme tous
    les fronts montants partagent la même phase, retenir le plus récent
    rend la trace affichée stable d'une frame à l'autre.
    """
    n = len(history)
    if width <= 0 or n < width:
        return None
    max_start = n - width
    for i in range(max_start, 0, -1):
        if history[i - 1] < level <= history[i]:
            return (i, i + width)
    return None
