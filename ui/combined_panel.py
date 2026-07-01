import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.plot_utils import time_unit, shared_trigger_window, build_combined_series

# Palette cyclique : une couleur par courbe (cycle matplotlib « tab10 »).
_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


class CombinedGraphWidget(tk.Frame):
    """Panneau RUN affiché quand aucun appareil n'est sélectionné.

    Trace les historiques de tous les appareils de mesure sur un seul axe,
    une couleur par courbe, pour comparer les déphasages. Déclenchement
    optionnel sur un appareil de référence choisi dans un menu déroulant.
    """

    def __init__(self, parent):
        super().__init__(parent, relief=tk.SUNKEN, bd=1)

        # Barre de contrôles : case déclenchement + menu de référence
        controls = tk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=6)

        self._trigger_var = tk.BooleanVar(value=True)
        tk.Checkbutton(controls, text="Déclenchement",
                       variable=self._trigger_var).pack(side=tk.LEFT)

        tk.Label(controls, text="Réf. :").pack(side=tk.LEFT, padx=(10, 2))
        self._ref_var = tk.StringVar(value="")
        self._ref_menu = ttk.Combobox(
            controls, textvariable=self._ref_var, state="readonly", width=12
        )
        self._ref_menu.pack(side=tk.LEFT)

        # Figure matplotlib
        self._fig = Figure(figsize=(4, 2.5), dpi=90)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True,
                                          padx=5, pady=5)

    def set_meters(self, comp_objects):
        """Peuple le menu déroulant avec les IDs des appareils de mesure."""
        ids = [cid for cid, comp in comp_objects.items()
               if getattr(comp, "records_history", False)]
        self._ref_menu["values"] = ids
        if ids:
            self._ref_var.set(ids[0])
        else:
            self._ref_var.set("")

    def update(self, histories, comp_objects, dt=None):
        """Redessine toutes les courbes (appelé à 5 Hz en mode RUN)."""
        self._ax.clear()

        ref_id = self._ref_var.get()
        ref_history = histories.get(ref_id, [])
        window = shared_trigger_window(ref_history, self._trigger_var.get())
        series = build_combined_series(histories, comp_objects, window)

        if not series:
            self._ax.text(0.5, 0.5, "Aucun appareil de mesure",
                          ha="center", va="center", transform=self._ax.transAxes,
                          color="#888888")
            self._canvas.draw_idle()
            return

        # Longueur commune = plus courte série (buffers alignés en début de fenêtre)
        length = min(len(ys) for _label, ys in series)
        if dt:
            unit, scale = time_unit(max(length - 1, 1) * dt)
            xs = [k * dt * scale for k in range(length)]
            xlabel = f"Temps ({unit})"
        else:
            xs = list(range(length))
            xlabel = "Échantillons"

        for idx, (label, ys) in enumerate(series):
            color = _PALETTE[idx % len(_PALETTE)]
            self._ax.plot(xs, ys[:length], color=color, linewidth=0.8, label=label)

        self._ax.axhline(0, color="#888888", linewidth=0.8, linestyle="--")
        self._ax.set_xlabel(xlabel)
        self._ax.set_ylabel("Valeur (V / A)")
        self._ax.grid(True, alpha=0.3)
        self._ax.legend(loc="upper right", fontsize=7)
        self._fig.tight_layout()
        self._canvas.draw_idle()
