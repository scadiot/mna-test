import tkinter as tk
from tkinter import ttk


class ComponentListWidget(tk.Frame):
    """
    Widget affichant la liste des composants du circuit.
    Appelle on_select_callback(component) quand l'utilisateur clique sur un composant.
    """

    def __init__(self, parent, on_select_callback):
        super().__init__(parent)
        self._callback = on_select_callback
        self._components = []   # liste des objets Component dans l'ordre affiché

        # Titre
        tk.Label(self, text="Composants", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", padx=5, pady=(5, 0)
        )

        # Listbox avec scrollbar
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(
            frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE,
            activestyle="dotbox", font=("Courier", 9)
        )
        scrollbar.config(command=self._listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._listbox.bind("<<ListboxSelect>>", self._on_click)

    def populate(self, components):
        """Remplit la liste depuis les composants du circuit chargé."""
        self._components = list(components)
        self._listbox.delete(0, tk.END)
        for comp in self._components:
            label = f"{comp.id:<8} {type(comp).__name__:<14}"
            self._listbox.insert(tk.END, label)

    def update_states(self, comp_states):
        """Rafraîchit les libellés avec l'état courant (tension)."""
        for i, comp in enumerate(self._components):
            state = comp_states.get(comp.id, {})
            v = state.get("voltage", 0.0)
            label = f"{comp.id:<8} {type(comp).__name__:<14} {v:+.3f}V"
            self._listbox.delete(i)
            self._listbox.insert(i, label)

    def _on_click(self, event):
        """Appelle le callback avec le composant sélectionné."""
        selection = self._listbox.curselection()
        if selection and self._callback:
            idx = selection[0]
            self._callback(self._components[idx])
