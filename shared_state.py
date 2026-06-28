import threading
from collections import deque


class SharedState:
    """Contient les données partagées entre le thread simulateur et l'UI."""

    def __init__(self):
        self._lock = threading.Lock()
        # tensions aux nœuds : {nom_nœud: float}
        self.node_voltages = {}
        # état de chaque composant : {id: {"voltage": float, "current": float}}
        self.comp_states = {}
        # historiques des appareils de mesure : {id: deque}
        self.histories = {}
        self.running = False
        self.error = None

    def init_histories(self, component_ids, history_size):
        """Initialise les deques pour les appareils de mesure."""
        with self._lock:
            for cid in component_ids:
                self.histories[cid] = deque(maxlen=history_size)

    def write(self, node_voltages, comp_states, history_updates):
        """Écrit les résultats d'un pas de simulation (appelé par le thread simulateur)."""
        with self._lock:
            self.node_voltages = node_voltages
            self.comp_states = comp_states
            for cid, value in history_updates.items():
                if cid in self.histories:
                    self.histories[cid].append(value)

    def read(self):
        """Lit les données courantes (appelé par l'UI)."""
        with self._lock:
            return {
                "node_voltages": dict(self.node_voltages),
                "comp_states": dict(self.comp_states),
                "histories": {k: list(v) for k, v in self.histories.items()},
                "running": self.running,
                "error": self.error,
            }

    def set_error(self, message):
        """Enregistre une erreur et arrête la simulation."""
        with self._lock:
            self.error = message
            self.running = False

    def stop(self):
        """Demande l'arrêt propre de la simulation."""
        with self._lock:
            self.running = False
