import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DetailPanelWidget(tk.Frame):
    """
    Panneau droit de l'UI : affiche les paramètres et l'état d'un composant sélectionné.
    Pour les voltmètres et ampèremètres, affiche aussi un graphique d'historique.
    """

    def __init__(self, parent):
        super().__init__(parent, relief=tk.SUNKEN, bd=1)
        self._current_component = None

        # Zone texte pour les paramètres et l'état
        self._info_var = tk.StringVar(value="Sélectionnez un composant")
        tk.Label(self, textvariable=self._info_var, justify=tk.LEFT,
                 font=("Courier", 9), anchor="nw").pack(
            fill=tk.X, padx=10, pady=10
        )

        # Graphique matplotlib (visible seulement pour les appareils de mesure)
        self._fig = Figure(figsize=(4, 2.5), dpi=90)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas_widget = self._canvas.get_tk_widget()
        # masqué par défaut — affiché seulement si records_history

        # Bouton toggle pour les interrupteurs
        self._toggle_btn = None

    def show_component(self, component):
        """Affiche les informations statiques d'un composant (appel au clic)."""
        self._current_component = component

        # Supprime le bouton toggle précédent s'il existe
        if self._toggle_btn:
            self._toggle_btn.destroy()
            self._toggle_btn = None

        # Affiche les paramètres JSON du composant
        lines = [f"ID      : {component.id}",
                 f"Type    : {type(component).__name__}",
                 "─" * 30,
                 "Paramètres :"]
        for key, val in component.params.items():
            lines.append(f"  {key:<14}: {val}")
        self._info_var.set("\n".join(lines))

        # Bouton toggle pour l'interrupteur
        from simulator.components import Switch
        if isinstance(component, Switch):
            self._toggle_btn = tk.Button(
                self, text="Basculer l'interrupteur",
                command=component.toggle
            )
            self._toggle_btn.pack(pady=5)

        # Affiche ou masque le graphique
        if component.records_history:
            self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            self._canvas_widget.pack_forget()

    def update(self, comp_state, history):
        """Rafraîchit l'état dynamique et le graphique (appelé à 5 Hz)."""
        if self._current_component is None:
            return

        comp = self._current_component
        v = comp_state.get("voltage", 0.0)
        i = comp_state.get("current", 0.0)

        lines = [f"ID      : {comp.id}",
                 f"Type    : {type(comp).__name__}",
                 "─" * 30,
                 "Paramètres :"]
        for key, val in comp.params.items():
            lines.append(f"  {key:<14}: {val}")
        lines += ["─" * 30,
                  f"  Tension  : {v:+.4f} V",
                  f"  Courant  : {i:+.6f} A"]
        self._info_var.set("\n".join(lines))

        # Mise à jour du graphique pour les appareils de mesure
        if comp.records_history and history:
            self._ax.clear()
            self._ax.plot(history, color="#1f77b4", linewidth=0.8)
            self._ax.set_ylabel("Tension (V)" if "voltmeter" in type(comp).__name__.lower()
                                else "Courant (A)")
            self._ax.set_xlabel("Échantillons")
            self._ax.grid(True, alpha=0.3)
            self._fig.tight_layout()
            self._canvas.draw_idle()
