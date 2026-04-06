import customtkinter as ctk
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.core.config_loader import config
from bot_insta.src.gui.components.dropdown import DropdownButton

class QuotesView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Controls ────────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(ctrl, text="Quote Group", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(14,4))
        
        self.selected_group = ctk.StringVar()
        self.dd_group = DropdownButton(ctrl, "", [], self._on_group_select, width=150)
        self.dd_group.pack(side="left", padx=(0,12))

        ctk.CTkButton(ctrl, text="+ New", font=FONT_SMALL, width=60, fg_color="#23262e", hover_color="#2e323c",
                      command=self._new_group).pack(side="left", padx=(4,0))
        ctk.CTkButton(ctrl, text="Delete", font=FONT_SMALL, width=60, fg_color="#2a1a1a", hover_color="#4a1a1a",
                      command=self._del_group).pack(side="left", padx=4)

        ctk.CTkButton(ctrl, text="Save Changes", font=FONT_SMALL, fg_color=ACCENT_TEAL, hover_color="#006060",
                      command=self._save_group).pack(side="right", padx=14)

        # ── Editor Form ─────────────────────────────────────────────────────
        self.form_wrap = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.form_wrap.grid(row=1, column=0, sticky="nsew")
        self.form_wrap.grid_columnconfigure(0, weight=1)
        self.form_wrap.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.form_wrap, text="Quotes (one per line)", font=FONT_MAIN, text_color="#c0c0c0").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        self.txt_content = ctk.CTkTextbox(self.form_wrap, font=FONT_SMALL, fg_color="#23262e")
        self.txt_content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self._refresh()

    def _refresh(self, name_to_select=None):
        groups = config.list_quote_groups()
        self.dd_group.update_options(groups)
        if not groups:
            self.selected_group.set("")
            self.dd_group.set_label("No quote groups")
            self.txt_content.delete("0.0", "end")
            return
        
        target = name_to_select if name_to_select in groups else groups[0]
        self._on_group_select(target)

    def _on_group_select(self, name):
        self.selected_group.set(name)
        self.dd_group.set_label(name)
        content = config.read_quote_group(name)
        
        self.txt_content.delete("0.0", "end")
        self.txt_content.insert("0.0", content)

    def _new_group(self):
        name = simpledialog.askstring("New Quote Group", "Group Name (no extensions):", parent=self)
        if not name or not name.strip(): return
        name = name.strip()
        
        if name in config.list_quote_groups():
            messagebox.showerror("Error", "Quote group already exists.", parent=self)
            return
            
        config.save_quote_group(name, "Nueva frase 1\\nNueva frase 2")
        self._refresh(name)
        self.app.dashboard.refresh_profiles()

    def _del_group(self):
        name = self.selected_group.get()
        if not name: return
        if messagebox.askyesno("Delete", f"Delete quote group '{name}'?", parent=self):
            config.delete_quote_group(name)
            self._refresh()
            self.app.dashboard.refresh_profiles()

    def _save_group(self):
        name = self.selected_group.get()
        if not name: return
        content = self.txt_content.get("0.0", "end").strip()
        config.save_quote_group(name, content)
        messagebox.showinfo("Saved", f"Quote group '{name}' saved.", parent=self)
        self.app.dashboard.refresh_profiles()
