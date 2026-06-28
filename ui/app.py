# ui/app.py
import tkinter as tk
from tkinter import filedialog, messagebox

from shared_state import SharedState
from circuit_loader import load_circuit
from simulator.engine import SimulationEngine
from ui.component_list import ComponentListWidget
from ui.detail_panel import DetailPanelWidget


class App(tk.Tk):
    """Fenêtre principale du simulateur de circuit électronique."""

    REFRESH_MS = 200   # rafraîchissement UI à 5 Hz

    def __init__(self):
        super().__init__()
        self.title("Simulateur de circuit")
        self.geometry("900x550")
        self.minsize(700, 400)

        self._state = SharedState()
        self._engine = None
        self._circuit = None
        self._selected_component = None

        self._build_ui()
        self._schedule_refresh()

        # Arrête le moteur proprement à la fermeture de la fenêtre
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """Construit la mise en page : barre supérieure + liste + panneau détail."""
        # ── Barre supérieure ──────────────────────────────────────────────────
        bar = tk.Frame(self, bd=1, relief=tk.RIDGE)
        bar.pack(fill=tk.X, side=tk.TOP)

        tk.Button(bar, text="Ouvrir circuit...", command=self._open_file).pack(
            side=tk.LEFT, padx=5, pady=4
        )
        self._file_label = tk.Label(bar, text="Aucun circuit chargé", fg="gray")
        self._file_label.pack(side=tk.LEFT, padx=10)

        self._run_btn = tk.Button(bar, text="▶  Démarrer", state=tk.DISABLED,
                                  command=self._toggle_simulation)
        self._run_btn.pack(side=tk.RIGHT, padx=5, pady=4)

        self._status_label = tk.Label(bar, text="", fg="red")
        self._status_label.pack(side=tk.RIGHT, padx=10)

        # ── Corps : liste à gauche, détail à droite ───────────────────────────
        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        self._comp_list = ComponentListWidget(body, on_select_callback=self._on_select)
        self._comp_list.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=5)

        ttk_sep = tk.Frame(body, width=2, bd=1, relief=tk.SUNKEN)
        ttk_sep.pack(side=tk.LEFT, fill=tk.Y, padx=3)

        self._detail = DetailPanelWidget(body)
        self._detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _open_file(self):
        """Ouvre un fichier JSON et charge le circuit."""
        path = filedialog.askopenfilename(
            title="Ouvrir un circuit",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return

        # Arrête la simulation en cours si nécessaire
        self._stop_simulation()

        try:
            self._circuit = load_circuit(path)
        except (ValueError, KeyError, Exception) as e:
            messagebox.showerror("Erreur de chargement", str(e))
            return

        # Réinitialise le SharedState et initialise les historiques de mesure
        self._state = SharedState()
        for comp_id, hist_size in self._circuit.histories.items():
            self._state.init_histories([comp_id], hist_size)

        self._file_label.config(text=self._circuit.name, fg="black")
        self._comp_list.populate(self._circuit.components)
        self._run_btn.config(state=tk.NORMAL, text="▶  Démarrer")
        self._status_label.config(text="")
        self._selected_component = None

    def _toggle_simulation(self):
        """Démarre ou arrête la simulation."""
        if self._engine and self._state.running:
            self._stop_simulation()
        else:
            self._start_simulation()

    def _start_simulation(self):
        """Crée et lance le moteur de simulation dans son thread."""
        if self._circuit is None:
            return
        self._engine = SimulationEngine(self._circuit, self._state)
        self._engine.start()
        self._run_btn.config(text="⏹  Arrêter")

    def _stop_simulation(self):
        """Arrête proprement le moteur de simulation s'il tourne."""
        if self._engine:
            self._engine.stop()
            self._engine = None
        self._run_btn.config(text="▶  Démarrer")

    def _on_select(self, component):
        """Appelé quand l'utilisateur clique sur un composant dans la liste."""
        self._selected_component = component
        self._detail.show_component(component)

    def _schedule_refresh(self):
        """Programme le prochain rafraîchissement de l'UI (5 Hz)."""
        self._refresh()
        self.after(self.REFRESH_MS, self._schedule_refresh)

    def _refresh(self):
        """Lit le SharedState et met à jour l'UI."""
        data = self._state.read()

        # Affiche une erreur si le moteur a planté
        if data["error"]:
            self._status_label.config(text=f"Erreur : {data['error']}")
            self._run_btn.config(text="▶  Démarrer")

        # Rafraîchit la liste des composants
        if data["comp_states"]:
            self._comp_list.update_states(data["comp_states"])

        # Rafraîchit le panneau de détail si un composant est sélectionné
        if self._selected_component:
            comp_id = self._selected_component.id
            comp_state = data["comp_states"].get(comp_id, {})
            history = data["histories"].get(comp_id, [])
            self._detail.update(comp_state, history)

    def _on_close(self):
        """Arrête le moteur si actif, puis ferme la fenêtre."""
        self._stop_simulation()
        self.destroy()
