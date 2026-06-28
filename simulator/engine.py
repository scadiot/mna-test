# simulator/engine.py
import time
import threading
import numpy as np
from simulator.components import Inductor, Capacitor, Ammeter


class SimulationEngine:
    """
    Moteur de simulation MNA (Modified Nodal Analysis).
    Tourne dans un thread daemon séparé à la fréquence 1/dt.
    """

    def __init__(self, circuit, shared_state):
        self._circuit = circuit
        self._state = shared_state
        self._dt = circuit.dt
        self._components = circuit.components
        self._thread = None

        # Table des nœuds : {nom: indice} — GND exclu (toujours 0V)
        self._node_map = {}
        # Table des branches : {component_id: indice} — pour sources de tension et ampèremètres
        self._branch_map = {}
        self._build_maps()

        # État précédent de chaque composant pour les modèles compagnons
        self._prev_states = {c.id: {"voltage": 0.0, "current": 0.0} for c in self._components}

    def _build_maps(self):
        """Attribue un indice à chaque nœud non-GND et à chaque branche de tension."""
        node_set = set()
        for comp in self._components:
            for node in comp.get_nodes():
                if node != "GND":
                    node_set.add(node)

        # Tri alphabétique pour un ordre déterministe
        for i, name in enumerate(sorted(node_set)):
            self._node_map[name] = i

        branch_idx = len(self._node_map)
        for comp in self._components:
            if comp.needs_branch():
                self._branch_map[comp.id] = branch_idx
                branch_idx += 1

    def _step(self, t):
        """Effectue un pas de simulation MNA à l'instant t."""
        size = len(self._node_map) + len(self._branch_map)
        G = np.zeros((size, size))
        b = np.zeros(size)

        # Chaque composant ajoute sa contribution à G et b
        for comp in self._components:
            prev = self._prev_states[comp.id]
            comp.stamp(G, b, self._node_map, self._branch_map, self._dt, t, prev)

        # Résolution du système linéaire G·x = b
        try:
            x = np.linalg.solve(G, b)
        except np.linalg.LinAlgError as e:
            self._state.set_error(f"Matrice singulière à t={t:.6f}s : {e}")
            return False

        # Extraction des tensions aux nœuds
        node_voltages = {name: float(x[idx]) for name, idx in self._node_map.items()}
        node_voltages["GND"] = 0.0

        # Extraction de l'état de chaque composant
        comp_states = {}
        history_updates = {}
        for comp in self._components:
            state = comp.get_state(x, self._node_map, self._branch_map)
            comp_states[comp.id] = state
            if comp.records_history:
                # Enregistre la tension pour le voltmètre, le courant pour l'ampèremètre
                history_updates[comp.id] = state["current"] if isinstance(comp, Ammeter) else state["voltage"]

        # Recalcul du courant pour les composants réactifs
        # (get_state ne connaît pas prev_state, donc current=0.0 par défaut)
        for comp in self._components:
            if isinstance(comp, Inductor):
                va = float(x[self._node_map[comp.node_a]]) if comp.node_a in self._node_map else 0.0
                vb = float(x[self._node_map[comp.node_b]]) if comp.node_b in self._node_map else 0.0
                g_eq = self._dt / comp.inductance
                i_prev = self._prev_states[comp.id].get("current", 0.0)
                comp_states[comp.id]["current"] = g_eq * (va - vb) + i_prev
            elif isinstance(comp, Capacitor):
                v_prev = self._prev_states[comp.id].get("voltage", 0.0)
                g_eq = comp.capacitance / self._dt
                comp_states[comp.id]["current"] = g_eq * (comp_states[comp.id]["voltage"] - v_prev)

        self._prev_states = comp_states
        self._state.write(node_voltages, comp_states, history_updates)
        return True

    def _run_loop(self):
        """Boucle principale du simulateur (tourne dans un thread séparé)."""
        t = 0.0
        with self._state._lock:
            self._state.running = True

        # Temps de référence pour synchroniser la simulation avec le temps réel
        t_real_start = time.monotonic()

        while True:
            # Vérifie si l'arrêt a été demandé
            with self._state._lock:
                if not self._state.running:
                    break

            ok = self._step(t)
            if not ok:
                break   # erreur MNA → arrêt propre

            t += self._dt

            # Calcule le décalage entre temps simulé et temps réel écoulé
            # Si on est en avance, on dort ; si on est en retard, on continue
            t_real_elapsed = time.monotonic() - t_real_start
            t_ahead = t - t_real_elapsed
            if t_ahead > 1e-4:
                # On est en avance de plus de 100µs : on dort un peu
                time.sleep(t_ahead)

    def start(self):
        """Démarre la simulation dans un thread daemon."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Arrête proprement la simulation et attend la fin du thread."""
        self._state.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
