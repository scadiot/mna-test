# editor/validation.py
from editor.circuit_model import CircuitModel
from editor.editor_canvas import COMPONENT_TEMPLATES


def validate_for_simulation(model: CircuitModel) -> list[str]:
    """Retourne la liste des erreurs empêchant de simuler le circuit.

    Liste vide => le circuit peut être simulé.
    """
    errors: list[str] = []

    if not model.components:
        errors.append("Le circuit est vide.")

    # Toutes les pattes de chaque composant doivent être connectées à un nœud.
    for comp in model.components:
        template = COMPONENT_TEMPLATES.get(comp.type, {})
        for pin in template.get("pins", []):
            if pin.name not in comp.pin_connections:
                errors.append(f"{comp.id} : patte '{pin.name}' non connectée.")

    # Au moins un nœud GND doit être relié à un composant.
    connected_nodes = set()
    for comp in model.components:
        connected_nodes.update(comp.pin_connections.values())
    if "GND" not in connected_nodes:
        errors.append("Aucun nœud 'GND' (masse) connecté à un composant.")

    return errors
