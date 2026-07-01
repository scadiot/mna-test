# ui/unified_app.py
import tkinter as tk
from tkinter import filedialog, messagebox

from shared_state import SharedState
from circuit_loader import build_circuit
from simulator.engine import SimulationEngine
from editor.circuit_model import CircuitModel
from editor.editor_canvas import EditorCanvas
from editor.component_panel import ComponentPanel
from editor.properties_panel import PropertiesPanel
from editor.validation import validate_for_simulation
from editor import io
from ui.detail_panel import DetailPanelWidget
from ui.combined_panel import CombinedGraphWidget


class UnifiedApp(tk.Tk):
    """Application unifiée : édition (mode EDIT) et simulation (mode RUN)
    sur un canvas unique."""

    REFRESH_MS = 200   # rafraîchissement UI à 5 Hz en mode RUN

    def __init__(self):
        super().__init__()
        self.geometry("1200x720")
        self.minsize(900, 500)

        self.model = CircuitModel()
        self._current_file = None
        self._mode = "EDIT"            # "EDIT" | "RUN"
        self._state = SharedState()
        self._engine = None
        self._circuit = None
        self._comp_objects = {}        # {id: composant simulateur}
        self._selected_run_id = None

        self._build_ui()
        self._schedule_refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Raccourcis fichier (mode EDIT)
        self.bind("<Control-n>", lambda e: self._new())
        self.bind("<Control-o>", lambda e: self._open())
        self.bind("<Control-s>", lambda e: self._save())

        self._update_title()

    # ── Construction de l'UI ────────────────────────────────────────────────
    def _build_ui(self):
        bar = tk.Frame(self, bd=1, relief=tk.RIDGE)
        bar.pack(fill=tk.X, side=tk.TOP)

        tk.Button(bar, text="📄 Nouveau", command=self._new).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="📂 Ouvrir", command=self._open).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="💾 Enregistrer", command=self._save).pack(side=tk.LEFT, padx=3, pady=4)
        tk.Button(bar, text="💾+ Enr. sous", command=self._save_as).pack(side=tk.LEFT, padx=3, pady=4)

        self._run_btn = tk.Button(bar, text="▶  Démarrer", command=self._toggle_simulation)
        self._run_btn.pack(side=tk.RIGHT, padx=5, pady=4)
        self._status_label = tk.Label(bar, text="", fg="red")
        self._status_label.pack(side=tk.RIGHT, padx=10)

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        self.canvas = EditorCanvas(body, self.model)

        self.comp_panel = ComponentPanel(body, self.canvas, self)
        self.comp_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Panneau droit : propriétés (EDIT) ou graphe (RUN) — swap par pack/pack_forget
        self._right = tk.Frame(body)
        self._right.pack(side=tk.RIGHT, fill=tk.Y)
        self._props = PropertiesPanel(self._right, self.model, self.canvas)
        self._detail = DetailPanelWidget(self._right)
        self._combined = CombinedGraphWidget(self._right)
        self._props.pack(fill=tk.BOTH, expand=True)

        self.canvas.set_on_selection_change(self._on_selection)
        self.canvas.set_on_model_change(self._on_model_change)

    def _show_props_panel(self):
        self._detail.pack_forget()
        self._combined.pack_forget()
        self._props.pack(fill=tk.BOTH, expand=True)

    def _show_detail_panel(self):
        self._props.pack_forget()
        self._combined.pack_forget()
        self._detail.pack(fill=tk.BOTH, expand=True)

    def _show_combined_panel(self):
        self._props.pack_forget()
        self._detail.pack_forget()
        self._combined.pack(fill=tk.BOTH, expand=True)

    # ── Titre ────────────────────────────────────────────────────────────────
    def _update_title(self):
        prefix = "* " if self.model.is_dirty else ""
        name = self.model.name or "Nouveau circuit"
        suffix = " — Simulation" if self._mode == "RUN" else ""
        self.title(f"{prefix}{name} — Éditeur/Simulateur{suffix}")

    def _on_model_change(self):
        self._update_title()

    # ── Sélection ──────────────────────────────────────────────────────────
    def _on_selection(self, comp_id, node_id):
        if self._mode == "RUN":
            if comp_id and comp_id in self._comp_objects:
                self._selected_run_id = comp_id
                self._detail.show_component(self._comp_objects[comp_id])
                self._show_detail_panel()
            else:
                self._selected_run_id = None
                self._show_combined_panel()
            return
        if comp_id:
            self._props.show_component(comp_id)
        elif node_id:
            self._props.show_node(node_id)
        else:
            self._props.show_empty()

    # ── Machine à états EDIT ↔ RUN ───────────────────────────────────────────
    def _toggle_simulation(self):
        if self._mode == "RUN":
            self._stop_to_edit()
        else:
            self._start_run()

    def _start_run(self):
        errors = validate_for_simulation(self.model)
        if errors:
            messagebox.showerror("Circuit invalide", "\n".join(errors))
            return
        try:
            self._circuit = build_circuit(io.model_to_dict(self.model))
        except Exception as e:
            messagebox.showerror("Erreur de construction", str(e))
            return

        self._comp_objects = {c.id: c for c in self._circuit.components}
        self._state = SharedState()
        for cid, hist_size in self._circuit.histories.items():
            self._state.init_histories([cid], hist_size)

        self._engine = SimulationEngine(self._circuit, self._state)
        self._engine.start()

        self._mode = "RUN"
        self._selected_run_id = None
        self.canvas.set_read_only(True)
        self.comp_panel.set_enabled(False)
        self._combined.set_meters(self._comp_objects)
        self._show_combined_panel()
        self._run_btn.config(text="⏹  Arrêter")
        self._status_label.config(text="")
        self._update_title()

    def _stop_to_edit(self):
        if self._engine:
            self._engine.stop()
            self._engine = None
        self._status_label.config(text="")
        self._mode = "EDIT"
        self._comp_objects = {}
        self._selected_run_id = None
        self.canvas.set_read_only(False)
        self.comp_panel.set_enabled(True)
        self.canvas.redraw()       # efface l'overlay (delete("all"))
        self._show_props_panel()
        self._props.show_empty()
        self._run_btn.config(text="▶  Démarrer")
        self._update_title()

    # ── Rafraîchissement RUN ─────────────────────────────────────────────────
    def _schedule_refresh(self):
        self._refresh()
        self.after(self.REFRESH_MS, self._schedule_refresh)

    def _refresh(self):
        if self._mode != "RUN":
            return
        data = self._state.read()
        if data["error"]:
            self._status_label.config(text=f"Erreur : {data['error']}")
            self._stop_to_edit()
            return
        self.canvas.redraw()
        self.canvas.draw_live_overlay(
            data["node_voltages"], data["comp_states"], self._comp_objects)
        if self._selected_run_id:
            cs = data["comp_states"].get(self._selected_run_id, {})
            history = data["histories"].get(self._selected_run_id, [])
            self._detail.update(cs, history, self._circuit.dt)
        else:
            self._combined.update(
                data["histories"], self._comp_objects, self._circuit.dt)

    # ── Opérations fichier (mode EDIT) ───────────────────────────────────────
    def _confirm_unsaved(self) -> bool:
        if not self.model.is_dirty:
            return True
        return messagebox.askyesno(
            "Modifications non sauvegardées",
            "Des modifications non sauvegardées seront perdues. Continuer ?")

    def _ensure_edit_mode(self):
        if self._mode == "RUN":
            self._stop_to_edit()

    def _new(self):
        self._ensure_edit_mode()
        if not self._confirm_unsaved():
            return
        self.model = CircuitModel()
        self._current_file = None
        self.canvas.model = self.model
        self._props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self._props.show_empty()
        self._update_title()

    def _open(self):
        self._ensure_edit_mode()
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
        self._props._model = self.model
        self.canvas._selected_comp = None
        self.canvas._selected_node = None
        self.canvas._selected_wire = None
        self.canvas.redraw()
        self._props.show_empty()
        self._update_title()

    def _save(self):
        self._ensure_edit_mode()
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
        self._ensure_edit_mode()
        path = filedialog.asksaveasfilename(
            title="Enregistrer sous", defaultextension=".json",
            filetypes=[("JSON", "*.json")], initialdir="circuits")
        if not path:
            return
        self._current_file = path
        self._save()

    def _on_close(self):
        if self._mode == "RUN":
            self._stop_to_edit()
        if self._confirm_unsaved():
            self.destroy()
