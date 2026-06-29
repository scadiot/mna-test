# editor/properties_panel.py
import tkinter as tk
from editor.editor_canvas import COMPONENT_TEMPLATES


class PropertiesPanel(tk.Frame):
    def __init__(self, parent, model, canvas):
        super().__init__(parent, width=180, bd=1, relief=tk.SUNKEN)
        self.pack_propagate(False)
        self._model = model
        self._canvas = canvas
        self._widgets = []
        self._err_label = None
        tk.Label(self, text="Propriétés", font=("TkDefaultFont", 9, "bold")).pack(pady=(4, 2))
        self._body = tk.Frame(self)
        self._body.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.show_empty()

    def _clear(self):
        for w in self._widgets:
            w.destroy()
        self._widgets = []
        self._err_label = None

    def show_empty(self):
        self._clear()
        lbl = tk.Label(self._body, text="Sélectionnez un composant\nou un nœud.",
                        font=("TkDefaultFont", 9), fg="gray", justify=tk.CENTER)
        lbl.pack(pady=20)
        self._widgets.append(lbl)

    def show_component(self, comp_id: str):
        self._clear()
        comp = self._model.get_component(comp_id)
        if comp is None:
            self.show_empty()
            return

        # ID
        tk.Label(self._body, text="ID :", anchor="w").pack(fill=tk.X)
        id_var = tk.StringVar(value=comp.id)
        err_lbl = tk.Label(self._body, text="", fg="red", font=("TkDefaultFont", 8))
        err_lbl.pack(fill=tk.X)
        self._err_label = err_lbl
        self._widgets.append(err_lbl)

        def on_id_change(*_):
            new_id = id_var.get().strip()
            if not new_id or new_id == comp.id:
                err_lbl.config(text="")
                return
            ok = self._model.rename_component(comp.id, new_id)
            if ok:
                err_lbl.config(text="")
                self._canvas.redraw()
                self._canvas._notify_model()
            else:
                err_lbl.config(text=f"ID '{new_id}' déjà utilisé")

        id_entry = tk.Entry(self._body, textvariable=id_var)
        id_entry.pack(fill=tk.X)
        id_entry.bind("<FocusOut>", on_id_change)
        id_entry.bind("<Return>", on_id_change)
        self._widgets.append(id_entry)

        # Type
        tk.Label(self._body, text=f"Type : {comp.type}", anchor="w",
                  font=("TkDefaultFont", 9, "italic")).pack(fill=tk.X, pady=(4, 0))

        # Rotation
        def rotate():
            comp.rotation = (comp.rotation + 90) % 360
            self._model._touch()
            self._canvas.redraw()
            self._canvas._notify_model()
            rot_lbl.config(text=f"Rotation : {comp.rotation}°")

        rot_lbl = tk.Label(self._body, text=f"Rotation : {comp.rotation}°", anchor="w")
        rot_lbl.pack(fill=tk.X, pady=(4, 0))
        rot_btn = tk.Button(self._body, text="↻ Tourner 90°", command=rotate)
        rot_btn.pack(fill=tk.X, pady=(0, 6))
        self._widgets += [rot_lbl, rot_btn]

        # Params
        template = COMPONENT_TEMPLATES.get(comp.type, {})
        param_keys = list(template.get("params", {}).keys())
        tk.Label(self._body, text="Paramètres :", anchor="w",
                  font=("TkDefaultFont", 9, "bold")).pack(fill=tk.X, pady=(4, 0))
        param_vars = {}
        for key in param_keys:
            row = tk.Frame(self._body)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{key} :", width=14, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(comp.params.get(key, "")))
            param_vars[key] = var

            def make_updater(k, v):
                def update(*_):
                    raw = v.get().strip()
                    try:
                        val = float(raw)
                    except ValueError:
                        val = raw
                    comp.params[k] = val
                    self._model._touch()
                    self._canvas._notify_model()
                return update

            ent = tk.Entry(row, textvariable=var, width=10)
            ent.pack(side=tk.LEFT)
            updater = make_updater(key, var)
            ent.bind("<FocusOut>", updater)
            ent.bind("<Return>", updater)
            self._widgets.append(row)

        # Connexions
        tk.Label(self._body, text="Pattes :", anchor="w",
                  font=("TkDefaultFont", 9, "bold")).pack(fill=tk.X, pady=(6, 0))
        pins = template.get("pins", [])
        for pin in pins:
            node_id = comp.pin_connections.get(pin.name, "—")
            lbl = tk.Label(self._body, text=f"  {pin.name} → {node_id}", anchor="w",
                            font=("TkDefaultFont", 8))
            lbl.pack(fill=tk.X)
            self._widgets.append(lbl)

    def show_node(self, node_id: str):
        self._clear()
        node = self._model.get_node(node_id)
        if node is None:
            self.show_empty()
            return

        tk.Label(self._body, text="Nœud", font=("TkDefaultFont", 9, "bold"), anchor="w").pack(fill=tk.X)

        tk.Label(self._body, text="ID :", anchor="w").pack(fill=tk.X)
        err_lbl = tk.Label(self._body, text="", fg="red", font=("TkDefaultFont", 8))
        err_lbl.pack(fill=tk.X)
        self._widgets.append(err_lbl)
        id_var = tk.StringVar(value=node.id)

        def on_node_id_change(*_):
            new_id = id_var.get().strip()
            if not new_id or new_id == node.id:
                return
            if self._model.get_node(new_id) is not None:
                err_lbl.config(text=f"ID '{new_id}' déjà utilisé")
                return
            err_lbl.config(text="")
            self._model.rename_node(node.id, new_id)
            self._canvas.redraw()
            self._canvas._notify_model()

        id_entry = tk.Entry(self._body, textvariable=id_var)
        id_entry.pack(fill=tk.X)
        id_entry.bind("<FocusOut>", on_node_id_change)
        id_entry.bind("<Return>", on_node_id_change)
        self._widgets.append(id_entry)

        tk.Label(self._body, text=f"x : {node.x:.1f}", anchor="w").pack(fill=tk.X, pady=(6, 0))
        tk.Label(self._body, text=f"y : {node.y:.1f}", anchor="w").pack(fill=tk.X)
