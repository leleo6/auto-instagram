import customtkinter as ctk
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.core.config_loader import config
from bot_insta.src.gui.components.dropdown import DropdownButton

class CaptionsView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Controls ────────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(ctrl, text="Caption Profile", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(14,4))
        
        self.selected_cap = ctk.StringVar()
        self.dd_cap = DropdownButton(ctrl, "", [], self._on_cap_select, width=150)
        self.dd_cap.pack(side="left", padx=(0,12))

        ctk.CTkButton(ctrl, text="+ New", font=FONT_SMALL, width=60, fg_color="#23262e", hover_color="#2e323c",
                      command=self._new_cap).pack(side="left", padx=(4,0))
        ctk.CTkButton(ctrl, text="Delete", font=FONT_SMALL, width=60, fg_color="#2a1a1a", hover_color="#4a1a1a",
                      command=self._del_cap).pack(side="left", padx=4)

        ctk.CTkButton(ctrl, text="Save Changes", font=FONT_SMALL, fg_color=ACCENT_TEAL, hover_color="#006060",
                      command=self._save_cap).pack(side="right", padx=14)

        # ── Editor Form ─────────────────────────────────────────────────────
        self.form_wrap = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.form_wrap.grid(row=1, column=0, sticky="nsew")
        self.form_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.form_wrap, text="Description", font=FONT_MAIN, text_color="#c0c0c0").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        self.txt_desc = ctk.CTkTextbox(self.form_wrap, height=120, font=FONT_SMALL, fg_color="#23262e")
        self.txt_desc.grid(row=1, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(self.form_wrap, text="Hashtags", font=FONT_MAIN, text_color="#c0c0c0").grid(row=2, column=0, sticky="w", padx=20, pady=(20, 5))
        self.txt_tags = ctk.CTkTextbox(self.form_wrap, height=60, font=FONT_SMALL, fg_color="#23262e")
        self.txt_tags.grid(row=3, column=0, sticky="ew", padx=20)

        self._refresh()

    def _refresh(self, name_to_select=None):
        caps = config.list_captions()
        self.dd_cap.update_options(caps)
        if not caps:
            self.selected_cap.set("")
            self.dd_cap.set_label("No profiles")
            self.txt_desc.delete("0.0", "end")
            self.txt_tags.delete("0.0", "end")
            return
        
        target = name_to_select if name_to_select in caps else caps[0]
        self._on_cap_select(target)

    def _on_cap_select(self, name):
        self.selected_cap.set(name)
        self.dd_cap.set_label(name)
        data = config.get_caption_data(name)
        
        self.txt_desc.delete("0.0", "end")
        self.txt_desc.insert("0.0", data.get("description", ""))
        self.txt_tags.delete("0.0", "end")
        self.txt_tags.insert("0.0", data.get("hashtags", ""))

    def _new_cap(self):
        name = simpledialog.askstring("New Caption", "Profile Name:", parent=self)
        if not name or not name.strip(): return
        
        if name in config.list_captions():
            messagebox.showerror("Error", "Caption profile already exists.", parent=self)
            return
            
        config.update_caption(name.strip(), "", "")
        self._refresh(name.strip())
        self.app.dashboard.refresh_profiles()

    def _del_cap(self):
        name = self.selected_cap.get()
        if not name: return
        if messagebox.askyesno("Delete", f"Delete caption profile '{name}'?", parent=self):
            config.delete_caption(name)
            self._refresh()
            self.app.dashboard.refresh_profiles()

    def _save_cap(self):
        name = self.selected_cap.get()
        if not name: return
        config.update_caption(name, self.txt_desc.get("0.0", "end").strip(), self.txt_tags.get("0.0", "end").strip())
        messagebox.showinfo("Saved", f"Caption '{name}' updated.", parent=self)
        self.app.dashboard.refresh_profiles()
