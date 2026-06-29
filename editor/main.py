# editor/main.py
import tkinter as tk
from tkinter import filedialog, messagebox

from editor.circuit_model import CircuitModel
from editor.editor_canvas import EditorCanvas
from editor.component_panel import ComponentPanel
from editor.properties_panel import PropertiesPanel
from editor.toolbar import Toolbar
from editor import io


class EditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.model = CircuitModel()
        self._current_file: str | None = None

        root.title("Éditeur de circuit")
        root.geometry("1100x700")

        # Barre d'outils
        self.toolbar = Toolbar(root,
                                on_new=self._new,
                                on_open=self._open,
                                on_save=self._save,
                                on_save_as=self._save_as)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Zone principale
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas au centre
        self.canvas = EditorCanvas(main_frame, self.model)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Panneau droit
        self.props = PropertiesPanel(main_frame, self.model, self.canvas)
        self.props.pack(side=tk.RIGHT, fill=tk.Y)

        # Panneau gauche (inséré avant le canvas)
        self.comp_panel = ComponentPanel(main_frame, self.canvas, root)
        self.comp_panel.pack(side=tk.LEFT, fill=tk.Y, before=self.canvas)

        # Callbacks
        self.canvas.set_on_selection_change(self._on_selection)
        self.canvas.set_on_model_change(self._on_model_change)

        # Raccourcis clavier
        root.bind("<Control-n>", lambda e: self._new())
        root.bind("<Control-o>", lambda e: self._open())
        root.bind("<Control-s>", lambda e: self._save())
        root.bind("<Control-S>", lambda e: self._save_as())

        # Fermeture
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._update_title()

    def _update_title(self):
        prefix = "* " if self.model.is_dirty else ""
        name = self.model.name or "Nouveau circuit"
        self.root.title(f"{prefix}{name} — Éditeur de circuit")

    def _on_selection(self, comp_id, node_id):
        if comp_id:
            self.props.show_component(comp_id)
        elif node_id:
            self.props.show_node(node_id)
        else:
            self.props.show_empty()

    def _on_model_change(self):
        self._update_title()

    def _confirm_unsaved(self) -> bool:
        if not self.model.is_dirty:
            return True
        return messagebox.askyesno(
            "Modifications non sauvegardées",
            "Des modifications non sauvegardées seront perdues. Continuer ?")

    def _new(self):
        if not self._confirm_unsaved():
            return
        self.model = CircuitModel()
        self._current_file = None
        self.canvas.model = self.model
        self.props._model = self.model
        self.canvas.redraw()
        self.props.show_empty()
        self._update_title()

    def _open(self):
        if not self._confirm_unsaved():
            return
        path = filedialog.askopenfilename(
            title="Ouvrir un circuit",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")],
            initialdir="circuits")
        if not path:
            return
        try:
            self.model = io.load_circuit(path)
        except Exception as e:
            messagebox.showerror("Erreur de chargement", str(e))
            return
        self._current_file = path
        self.canvas.model = self.model
        self.props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self.props.show_empty()
        self._update_title()

    def _save(self):
        if self._current_file is None:
            self._save_as()
            return
        try:
            io.save_circuit(self.model, self._current_file)
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", str(e))
            return
        self._update_title()

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title="Enregistrer sous",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir="circuits")
        if not path:
            return
        self._current_file = path
        self._save()

    def _on_close(self):
        if self._confirm_unsaved():
            self.root.destroy()


def main():
    root = tk.Tk()
    EditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
