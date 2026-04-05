"""
app.py — Auto Instagram Bot
Minimalist two-view UI: Dashboard + Spec Editor
"""

import sys, os
from pathlib import Path
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import customtkinter as ctk

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.gui.bootstrap import init_app_theme
from bot_insta.src.gui.views.dashboard import DashboardView
from bot_insta.src.gui.views.spec_editor import SpecEditorView
from bot_insta.src.gui.views.captions import CaptionsView
from bot_insta.src.gui.views.accounts import AccountsView

class BotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_app_theme()
        
        self.title("auto-instagram")
        self.geometry("1220x800")
        self.configure(fg_color="#13151a")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Minimal top bar ───────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="#0e1014", corner_radius=0, height=44)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="auto-instagram", font=("Inter",14,"bold"),
                     text_color="#444").grid(row=0, column=0, padx=18, pady=12, sticky="w")

        nav = ctk.CTkFrame(bar, fg_color="transparent")
        nav.grid(row=0, column=2, padx=12, sticky="e")

        self.btn_d = ctk.CTkButton(nav, text="Dashboard", font=FONT_SMALL, width=100,
                                    fg_color=ACCENT_TEAL, hover_color="#005f5f",
                                    command=lambda: self._show("dashboard"))
        self.btn_d.pack(side="left", padx=(0,6))

        self.btn_e = ctk.CTkButton(nav, text="Spec Editor", font=FONT_SMALL, width=100,
                                    fg_color="#23262e", hover_color="#2e323c",
                                    command=lambda: self._show("editor"))
        self.btn_e.pack(side="left")

        self.btn_c = ctk.CTkButton(nav, text="📝 Captions", font=FONT_SMALL, width=100,
                                    fg_color="#23262e", hover_color="#2e323c",
                                    command=lambda: self._show("captions"))
        self.btn_c.pack(side="left", padx=(6,0))

        self.btn_a = ctk.CTkButton(nav, text="Accounts", font=FONT_SMALL, width=100,
                                    fg_color="#23262e", hover_color="#2e323c",
                                    command=lambda: self._show("accounts"))
        self.btn_a.pack(side="left", padx=(6,0))

        # ── Views ─────────────────────────────────────────────────────────────
        self.wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=14)
        self.wrap.grid_rowconfigure(0, weight=1)
        self.wrap.grid_columnconfigure(0, weight=1)

        self.dashboard = DashboardView(self.wrap, self)
        self.editor    = SpecEditorView(self.wrap, self)
        self.captions  = CaptionsView(self.wrap, self)
        self.accounts  = AccountsView(self.wrap, self)
        self._show("dashboard")

    def _show(self, view):
        self.dashboard.grid_forget()
        self.editor.grid_forget()
        self.captions.grid_forget()
        self.accounts.grid_forget()
        
        # Reset buttons to default color
        self.btn_d.configure(fg_color="#23262e")
        self.btn_e.configure(fg_color="#23262e")
        self.btn_c.configure(fg_color="#23262e")
        self.btn_a.configure(fg_color="#23262e")

        if view == "dashboard":
            self.dashboard.grid(row=0, column=0, sticky="nsew")
            self.btn_d.configure(fg_color=ACCENT_TEAL)
        elif view == "editor":
            self.editor.grid(row=0, column=0, sticky="nsew")
            self.btn_e.configure(fg_color=ACCENT_TEAL)
        elif view == "captions":
            self.captions.grid(row=0, column=0, sticky="nsew")
            self.btn_c.configure(fg_color=ACCENT_TEAL)
        elif view == "accounts":
            self.accounts.grid(row=0, column=0, sticky="nsew")
            self.btn_a.configure(fg_color=ACCENT_TEAL)
