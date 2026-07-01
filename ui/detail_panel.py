import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui.trigger import compute_trigger_window
from ui.plot_utils import time_unit


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
        self._ratio_slider = None
        self._ratio_label = None

        # Case à cocher de déclenchement (créée pour les appareils de mesure)
        self._trigger_chk = None
        self._trigger_var = tk.BooleanVar(value=True)

    def show_component(self, component):
        """Affiche les informations statiques d'un composant (appel au clic)."""
        self._current_component = component

        # Supprime le bouton toggle précédent s'il existe
        if self._toggle_btn:
            self._toggle_btn.destroy()
            self._toggle_btn = None

        if self._ratio_label:
            self._ratio_label.destroy()
            self._ratio_label = None

        if self._ratio_slider:
            self._ratio_slider.destroy()
            self._ratio_slider = None

        if self._trigger_chk:
            self._trigger_chk.destroy()
            self._trigger_chk = None

        # Affiche les paramètres JSON du composant
        lines = [f"ID      : {component.id}",
                 f"Type    : {type(component).__name__}",
                 "─" * 30,
                 "Paramètres :"]
        for key, val in component.params.items():
            lines.append(f"  {key:<14}: {val}")
        self._info_var.set("\n".join(lines))

        # Bouton toggle pour l'interrupteur et slider pour le potentiomètre
        from simulator.components import Switch, Potentiometer
        if isinstance(component, Switch):
            self._toggle_btn = tk.Button(
                self, text="Basculer l'interrupteur",
                command=component.toggle
            )
            self._toggle_btn.pack(pady=5)
        elif isinstance(component, Potentiometer):
            self._ratio_label = tk.Label(self, text="Ratio curseur :")
            self._ratio_label.pack()
            self._ratio_slider = tk.Scale(
                self, from_=0.0, to=1.0, resolution=0.01,
                orient=tk.HORIZONTAL, length=200,
                command=lambda v: component.set_ratio(float(v)),
            )
            self._ratio_slider.set(component.ratio)
            self._ratio_slider.pack(pady=5)

        # Graphique et case de déclenchement pour les appareils de mesure
        if component.records_history:
            self._trigger_chk = tk.Checkbutton(
                self, text="Déclenchement", variable=self._trigger_var
            )
            self._trigger_chk.pack()
            self._canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        else:
            self._canvas_widget.pack_forget()

    def update(self, comp_state, history, dt=None):
        """Rafraîchit l'état dynamique et le graphique (appelé à 5 Hz).

        `dt` est le pas de temps de simulation (s) ; chaque échantillon de
        l'historique correspond à un pas. S'il est fourni, l'axe X est tracé
        en temps, sinon en nombre d'échantillons.
        """
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

            if self._trigger_var.get():
                # Fenêtre déclenchée : moitié du buffer affichée, moitié réservée
                # à la recherche de front. Axe X figé à 0..width-1.
                width = len(history) // 2 or len(history)
                level = sum(history) / len(history)
                win = compute_trigger_window(history, width, level)
                if win is not None:
                    start, end = win
                    ys = history[start:end]
                    xs = range(len(ys))
                else:
                    # Repli : derniers échantillons alignés à droite
                    ys = history[-width:]
                    xs = range(width - len(ys), width)
                # max(..., 1) évite un axe de largeur nulle au tout début du
                # remplissage (width == 1), qui ferait râler matplotlib.
                x_max = max(width - 1, 1)
            else:
                # Comportement historique : tout le buffer aligné à droite
                n = comp.history_size
                ys = history
                xs = range(n - len(history), n)
                x_max = n - 1

            # Convertit l'axe X en temps si le pas de simulation est connu :
            # chaque échantillon = un pas dt. L'unité est choisie selon la
            # durée totale de la fenêtre affichée.
            if dt:
                unit, scale = time_unit(x_max * dt)
                factor = dt * scale
                xs = [x * factor for x in xs]
                x_max = x_max * factor
                xlabel = f"Temps ({unit})"
            else:
                xlabel = "Échantillons"

            self._ax.plot(xs, ys, color="#1f77b4", linewidth=0.8)
            self._ax.axhline(0, color="#888888", linewidth=0.8, linestyle="--")
            self._ax.set_xlim(0, x_max)
            self._ax.set_ylabel("Tension (V)" if "voltmeter" in type(comp).__name__.lower()
                                else "Courant (A)")
            self._ax.set_xlabel(xlabel)
            self._ax.grid(True, alpha=0.3)
            # Garantit que la ligne des 0 reste visible
            ymin, ymax = self._ax.get_ylim()
            if ymin > 0:
                self._ax.set_ylim(bottom=0)
            elif ymax < 0:
                self._ax.set_ylim(top=0)
            self._fig.tight_layout()
            self._canvas.draw_idle()
