import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from pathlib import Path

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL, ACCENT_GOLD
from bot_insta.src.core.config_loader import config, PROJECT_ROOT


def _rel(p: str) -> str:
    """Convert an absolute path string to relative from PROJECT_ROOT if possible."""
    try:
        return str(Path(p).relative_to(PROJECT_ROOT))
    except ValueError:
        return p


def _abs_str(rel: str) -> str:
    """Return the resolved absolute path string."""
    return str(PROJECT_ROOT / rel)


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Centered card ─────────────────────────────────────────────────────
        card = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Title
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(hdr, text="⚙", font=("Inter", 28), text_color=ACCENT_TEAL).pack(side="left", padx=(4, 10))
        ctk.CTkLabel(hdr, text="Configuracion", font=("Inter", 20, "bold"), text_color="#c0c0c0").pack(side="left")

        # ── Path sections ─────────────────────────────────────────────────────
        paths_cfg = config._config.get("paths", {})

        self._path_vars = {}
        path_definitions = [
            ("base_backgrounds", "Fondos (Backgrounds)",
             "Carpeta raiz donde se encuentran los videos de fondo.",
             "bot_insta/assets/backgrounds"),
            ("base_music", "Musica",
             "Carpeta raiz de las pistas de musica de fondo.",
             "bot_insta/assets/music"),
            ("output_dir", "Output (Exports)",
             "Carpeta donde se guardaran los reels exportados.",
             "bot_insta/exports"),
        ]

        for i, (key, label, description, default) in enumerate(path_definitions):
            current = paths_cfg.get(key, default)
            self._build_path_row(card, row=i + 1, key=key,
                                 label=label, description=description,
                                 current_rel=current)

        # ── Save button ───────────────────────────────────────────────────────
        self.btn_save = ctk.CTkButton(
            card, text="Guardar cambios", font=FONT_MAIN,
            fg_color=ACCENT_TEAL, hover_color="#006060",
            height=40, command=self._save
        )
        self.btn_save.grid(row=10, column=0, pady=(24, 8), padx=4, sticky="ew")

        self.lbl_status = ctk.CTkLabel(card, text="", font=FONT_SMALL, text_color="#4dcf9a")
        self.lbl_status.grid(row=11, column=0)

    def _build_path_row(self, parent, row: int, key: str, label: str,
                        description: str, current_rel: str):
        section = ctk.CTkFrame(parent, fg_color="#1c1f27", corner_radius=8)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 12), padx=4)
        section.grid_columnconfigure(0, weight=1)

        # Header row inside card
        top = ctk.CTkFrame(section, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=label, font=FONT_MAIN, text_color="#e0e0e0").grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text=description, font=FONT_SMALL, text_color="#555").grid(
            row=1, column=0, sticky="w")

        # Path input + browse button
        row_inner = ctk.CTkFrame(section, fg_color="transparent")
        row_inner.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 14))
        row_inner.grid_columnconfigure(0, weight=1)

        var = ctk.StringVar(value=_abs_str(current_rel))
        self._path_vars[key] = var

        entry = ctk.CTkEntry(
            row_inner, textvariable=var,
            font=FONT_SMALL, fg_color="#13151a",
            border_color="#333", text_color="#c0c0c0",
            height=36
        )
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        btn = ctk.CTkButton(
            row_inner, text="Examinar...", font=FONT_SMALL,
            width=110, height=36,
            fg_color="#23262e", hover_color="#2e323c",
            command=lambda k=key, v=var: self._browse(k, v)
        )
        btn.grid(row=0, column=1)

    def _browse(self, key: str, var: ctk.StringVar):
        initial = var.get() if Path(var.get()).exists() else str(PROJECT_ROOT)
        chosen = filedialog.askdirectory(
            title=f"Seleccionar carpeta para '{key}'",
            initialdir=initial,
            parent=self
        )
        if chosen:
            var.set(chosen)

    def _save(self):
        paths = config._config.setdefault("paths", {})
        changed = False

        for key, var in self._path_vars.items():
            raw = var.get().strip()
            if not raw:
                continue
            p = Path(raw)
            # Convert to relative if inside PROJECT_ROOT, otherwise keep absolute
            try:
                rel = str(p.relative_to(PROJECT_ROOT))
            except ValueError:
                rel = raw  # keep absolute path as-is

            if paths.get(key) != rel:
                paths[key] = rel
                # Make sure the directory exists
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                changed = True

        if changed:
            config.save()
            config.reload()
            # Refresh any view that caches paths
            self.app.dashboard.refresh_profiles()
            self.lbl_status.configure(text="✓ Guardado correctamente", text_color="#4dcf9a")
        else:
            self.lbl_status.configure(text="Sin cambios.", text_color="#888")

        self.after(2500, lambda: self.lbl_status.configure(text=""))
