"""
app.py — Auto Instagram Bot
Minimalist two-view UI: Dashboard + Spec Editor
"""

import sys, os, subprocess
from pathlib import Path
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import customtkinter as ctk
from tkinter.colorchooser import askcolor
from tkinter import simpledialog, messagebox
import tkinter as tk
import threading, textwrap, logging, random, time, queue
import PIL.Image, PIL.ImageDraw, PIL.ImageFont, PIL.ImageTk

from bot_insta.src.gui.style import *
from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.api.instagram import upload_reel
from bot_insta.src.api.tiktok import upload_tiktok
from bot_insta.src.api.youtube import upload_youtube
from bot_insta.src.core.config_loader import config
from bot_insta.src.core.account_manager import acc_manager

ctk.set_appearance_mode(THEME_MODE)
ctk.set_default_color_theme("green")

# ── Discover system fonts ─────────────────────────────────────────────────────
def _scan_fonts() -> dict[str, str]:
    """Returns {display_name: full_path} for all .ttf/.otf on the system."""
    font_dirs = [
        Path("/usr/share/fonts"),
        Path.home() / ".local/share/fonts",
        Path(PROJECT_ROOT) / "bot_insta/assets/fonts",
    ]
    fonts = {}
    for d in font_dirs:
        if not d.exists(): continue
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() in (".ttf", ".otf"):
                fonts[f.stem] = str(f)
    return fonts

SYSTEM_FONTS = _scan_fonts()

def create_platform_icon(platform: str) -> ctk.CTkImage:
    img = PIL.Image.new("RGBA", (24, 24), (0,0,0,0))
    d = PIL.ImageDraw.Draw(img)
    if platform == "Instagram":
        d.rounded_rectangle([3, 3, 21, 21], radius=6, outline="#E1306C", width=2)
        d.ellipse([8, 8, 16, 16], outline="#E1306C", width=2)
        d.ellipse([17, 5, 19, 7], fill="#E1306C")
    elif platform == "TikTok":
        d.line([14, 18, 14, 8], fill="#25F4EE", width=2)
        d.line([14, 8, 18, 8], fill="#FE2C55", width=2)
        d.ellipse([8, 14, 14, 20], fill="#25F4EE")
    elif platform == "YouTube":
        d.rounded_rectangle([3, 7, 21, 17], radius=3, fill="#FF0000")
        d.polygon([(10, 9), (10, 15), (15, 12)], fill="white")
    else:
        d.ellipse([4, 4, 20, 20], outline="#aaaaaa", width=2)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))

# ─────────────────────────────────────────────────────────────────────────────
# MINIMAL DROPDOWN POPUP
# ─────────────────────────────────────────────────────────────────────────────
class DropdownButton(ctk.CTkFrame):
    def __init__(self, parent, selected_id, options, on_select, width=170, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.options, self.on_select, self._popup = options, on_select, None
        self.btn = ctk.CTkButton(self, text="▾", width=width, font=FONT_SMALL,
                                  fg_color="#23262e", hover_color="#2e323c", anchor="w",
                                  command=self._toggle)
        self.btn.pack()
        self.update_options(options, selected_id)

    def update_options(self, opts, current_id=None): 
        self.options = opts
        if current_id is not None:
            for o in opts:
                if type(o) is dict and o["id"] == current_id:
                    self.set_label(o)
                    return
            if opts and type(opts[0]) is dict:
                self.set_label(opts[0])
            elif opts and type(opts[0]) is str:
                self.set_label(opts[0])
        elif opts and type(opts[0]) is str:
            self.set_label(opts[0])
        elif opts and type(opts[0]) is dict:
            self.set_label(opts[0])

    def set_label(self, o):
        if type(o) is dict:
            icon = create_platform_icon(o.get("platform", "Local"))
            self.btn.configure(text=f" {o['label']}  ▾", image=icon)
        else:
            self.btn.configure(text=f"{o}  ▾", image="")

    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy(); self._popup = None; return
        self._open()

    def _open(self):
        p = tk.Toplevel(self)
        p.overrideredirect(True)
        p.configure(bg="#23262e")
        self.btn.update_idletasks()
        x = self.btn.winfo_rootx()
        y = self.btn.winfo_rooty() + self.btn.winfo_height() + 2
        p.geometry(f"+{x}+{y}")

        max_h = min(len(self.options) * 36, 250)
        frame = ctk.CTkScrollableFrame(p, fg_color="#23262e", height=max_h, width=max(self.btn.winfo_width(), 170))
        frame.pack(fill="both", expand=True)
        frame._scrollbar.configure(width=10)
        
        for opt in self.options:
            if type(opt) is dict:
                plat = opt.get("platform", "Local")
                label = opt.get("label", "Unknown")
            else:
                plat = "Local (no upload)"
                if "Instagram" in opt: plat = "Instagram"
                elif "TikTok" in opt: plat = "TikTok"
                elif "YouTube" in opt: plat = "YouTube"
                label = opt
                
            icon = create_platform_icon(plat)
            b = ctk.CTkButton(frame, text=f" {label}", font=("Inter", 12), fg_color="transparent", 
                              hover_color=ACCENT_TEAL, anchor="w", image=icon, height=28,
                              command=lambda o=opt: self._select(o, p))
            b.pack(fill="x", pady=1)

        p.bind("<FocusOut>", lambda e: p.destroy())
        p.focus_set()
        self._popup = p

    def _select(self, opt, popup):
        popup.destroy(); self._popup = None
        self.set_label(opt)
        self.on_select(opt)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD VIEW
# ─────────────────────────────────────────────────────────────────────────────
class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Controls bar ──────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(ctrl, text="Profile", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(14,3))
        self.selected_profile = ctk.StringVar(value=config.get_active_profile())
        self.dd_profile = DropdownButton(ctrl, self.selected_profile.get(), config.list_profiles(),
                                         self._on_profile, width=150)
        self.dd_profile.pack(side="left", padx=(0,12))

        # vertical divider
        ctk.CTkFrame(ctrl, width=1, height=24, fg_color="#333").pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Publish to", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(12,3))
        self.platform_options = acc_manager.fetch_options_for_dropdown()
        self.selected_platform_opt = self.platform_options[0] if self.platform_options else {"id":"local","label":"Local (no upload)","platform":"Local"}
        self.dd_platform = DropdownButton(ctrl, self.selected_platform_opt["id"], self.platform_options,
                                           self._on_platform, width=220)
        self.dd_platform.pack(side="left", padx=(0,12))

        ctk.CTkFrame(ctrl, width=1, height=24, fg_color="#333").pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Caption", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(12,3))
        self.caption_options = ["None", "Custom"] + config.list_captions()
        self.selected_cap_opt = ctk.StringVar(value=self.caption_options[2] if len(self.caption_options)>2 else "None")
        self.dd_cap = DropdownButton(ctrl, self.selected_cap_opt.get(), self.caption_options,
                                      self._on_cap, width=180)
        self.dd_cap.pack(side="left", padx=(0,12))

        ctk.CTkFrame(ctrl, width=1, height=24, fg_color="#333").pack(side="left", padx=4)

        self.btn_gen = ctk.CTkButton(ctrl, text="Generate", font=FONT_MAIN, width=100,
                                      fg_color=ACCENT_TEAL, hover_color="#006060",
                                      command=self._queue)
        self.btn_gen.pack(side="left", padx=12)

        self.lbl_q = ctk.CTkLabel(ctrl, text="", font=FONT_SMALL, text_color="#444")
        self.lbl_q.pack(side="right", padx=14)

        # ── Jobs area ─────────────────────────────────────────────────────────
        self.jobs_wrap = ctk.CTkScrollableFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.jobs_wrap.grid(row=1, column=0, sticky="nsew")
        self.jobs_wrap.grid_columnconfigure(0, weight=1)

        self._job_count = 0
        self._active = 0
        self._hint = ctk.CTkLabel(self.jobs_wrap, text="No jobs yet. Press Generate to start.",
                                   font=FONT_SMALL, text_color="#444")
        self._hint.grid(padx=20, pady=40)

    def refresh_profiles(self):
        config.reload()
        self.dd_profile.update_options(config.list_profiles(), self.selected_profile.get())
        self.platform_options = acc_manager.fetch_options_for_dropdown()
        self.dd_platform.update_options(self.platform_options, getattr(self, "selected_platform_opt", {}).get("id"))
        self.caption_options = ["None", "Custom"] + config.list_captions()
        if self.selected_cap_opt.get() not in self.caption_options:
            self.selected_cap_opt.set(self.caption_options[2] if len(self.caption_options)>2 else "None")
        self.dd_cap.update_options(self.caption_options, self.selected_cap_opt.get())

    def _on_profile(self, name):
        self.selected_profile.set(name)

    def _on_platform(self, p):
        self.selected_platform_opt = p

    def _on_cap(self, p):
        self.selected_cap_opt.set(p)

    def _queue(self):
        # ── Handle Custom Caption Input Before Thread ──
        cap_val = self.selected_cap_opt.get()
        custom_desc = ""
        custom_tags = ""
        if cap_val == "Custom":
            dialog = ctk.CTkInputDialog(text="Enter Description (Use \\n for newlines, '#' for tags):", title="Custom Caption")
            res = dialog.get_input()
            if res is None: return # User cancelled
            custom_desc = res

        if self._job_count == 0 and self._hint.winfo_exists():
            self._hint.grid_forget()

        self._job_count += 1
        self._active += 1
        self._update_q()

        job_id = self._job_count
        profile = self.selected_profile.get()
        opt_choice = self.selected_platform_opt if type(self.selected_platform_opt) is dict else {"label": "Local (no upload)", "platform": "Local"}
        
        # Capture caption configuration state at queue time
        job_caption = ""
        if cap_val == "Custom":
            parts = custom_desc.split("#", 1)
            d = parts[0].strip()
            t = ("#" + parts[1].strip()) if len(parts) > 1 else ""
            job_caption = f"{d}\n\n{t}".strip()
        elif cap_val != "None":
            data = config.get_caption_data(cap_val)
            d = data.get("description", "").strip()
            t = data.get("hashtags", "").strip()
            job_caption = f"{d}\n\n{t}".strip()

        # ── Job card ──────────────────────────────────────────────────────────
        card = ctk.CTkFrame(self.jobs_wrap, fg_color="#23262e", corner_radius=6, height=36)
        card.grid(row=job_id, column=0, sticky="ew", padx=8, pady=4)
        card.pack_propagate(False)

        dot = ctk.CTkLabel(card, text="●", font=("Inter", 14), text_color="#444", width=20)
        dot.pack(side="left", padx=(10, 5))

        title = ctk.CTkLabel(card, text=f"#{job_id}  ·  {profile}  →  {opt_choice['label']}",
                             font=FONT_MAIN, text_color="#c0c0c0")
        title.pack(side="left", padx=(0, 15))

        status = ctk.CTkLabel(card, text="Queued…", font=FONT_SMALL, text_color="#555")
        status.pack(side="left", padx=(0, 15))

        link_row = ctk.CTkFrame(card, fg_color="transparent")
        link_row.pack(side="left")

        prog_frame = ctk.CTkFrame(card, fg_color="transparent")
        prog_frame.pack(side="left", fill="x", expand=True, padx=(10, 20))

        progress = ctk.CTkProgressBar(prog_frame, height=4, progress_color=ACCENT_TEAL)
        progress.set(0)
        progress.pack(fill="x", expand=True)

        abort_evt = threading.Event()
        
        btn_cancel = ctk.CTkButton(card, text="✕", width=26, height=26, font=("Inter", 12), text_color="white",
                                   fg_color="#3a1c1c", hover_color="#5a1c1c",
                                   command=lambda: abort_evt.set())
        btn_cancel.pack(side="right", padx=(0, 6))

        def ui(msg, color="#666", dc=None, prog=None):
            self.after(0, lambda: status.configure(text=msg, text_color=color))
            if dc: self.after(0, lambda: dot.configure(text_color=dc))
            if prog is not None: self.after(0, lambda: progress.set(prog))

        def _update_prog(p):
            self.after(0, lambda: progress.set(p))


        def run():
            orig = config.get_active_profile()
            config._config["active_profile"] = profile
            
            # Parse dynamic platform selection
            target_platform = "Local"
            acc_id = None
            creds = {}
            if type(self.selected_platform_opt) is dict and self.selected_platform_opt.get("id") != "local":
                acc_id = self.selected_platform_opt["id"]
                acc = acc_manager.get_account(acc_id)
                if acc:
                    target_platform = acc.get("platform", "Local")
                    creds = acc.get("credentials", {})

            try:
                ui("Generating…", "#888", ACCENT_GOLD)
                reel_path = create_reel(progress_callback=_update_prog, abort_event=abort_evt)
                ui(f"Done", "#4dcf9a", "#4dcf9a", prog=1.0)

                caption = job_caption

                def _link(p=reel_path):
                    b = ctk.CTkButton(link_row, text=f"▶  {p.name}",
                                      font=FONT_SMALL, fg_color="transparent",
                                      hover_color="#1e2820", text_color="#4dcf9a",
                                      height=22, cursor="hand2", anchor="w",
                                      command=lambda: subprocess.Popen(["xdg-open", str(p)]))
                    b.pack(anchor="w")
                    prog_frame.pack_forget()
                self.after(0, _link)

                self.after(0, lambda: btn_cancel.configure(state="disabled", fg_color="transparent", text_color="#333"))

                if target_platform == "Instagram":
                    ui("Uploading to Instagram…", "#888", prog=1.0)
                    try:
                        session_file = str(PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json") if acc_id else None
                        mid = upload_reel(reel_path, caption=caption, username=creds.get("username"), password=creds.get("password"), session_override=session_file)
                        ui(f"Uploaded  · ID {mid}", "#4dcf9a", "#00c070")
                        acc_manager.update_status(acc_id, "Active")
                    except Exception as e:
                        acc_manager.update_status(acc_id, "Error")
                        raise e
                elif target_platform == "YouTube":
                    ui("Uploading to YouTube…", "#888", prog=1.0)
                    priv = config._config.get("profiles", {}).get(profile, {}).get("youtube_privacy", "unlisted")
                    vid_id = upload_youtube(reel_path, caption=caption, privacy=priv, client_secrets_override=creds.get("youtube_client_secrets"))
                    ui(f"Uploaded  · ID {vid_id}", "#4dcf9a", "#00c070")
                    acc_manager.update_status(acc_id, "Active")
                elif target_platform == "TikTok":
                    ui("Uploading to TikTok…", "#888", prog=1.0)
                    upload_tiktok(reel_path, caption=caption, cookies_path_override=creds.get("tiktok_session_id"))
                    ui(f"Uploaded to TikTok", "#4dcf9a", "#00c070")
                    acc_manager.update_status(acc_id, "Active")
                # "Local" → nothing extra
                
                # Refresh accounts view implicitly if on UI
                self.after(0, lambda: self.app.accounts.refresh_list())
                
            except InterruptedError:
                ui("Cancelled by user", "#e05555", "#e05555")
                self.after(0, lambda: prog_frame.pack_forget())
                self.after(0, lambda: btn_cancel.configure(state="disabled", fg_color="transparent", text_color="#333"))
            except Exception as e:
                ui(f"Error: {e}", "#e05555", "#e05555")
                self.after(0, lambda: prog_frame.pack_forget())
                import traceback; traceback.print_exc()
                self.after(0, lambda: self.app.accounts.refresh_list())
            finally:
                config._config["active_profile"] = orig
                self._active -= 1
                self.after(0, self._update_q)

        threading.Thread(target=run, daemon=True).start()

    def _update_q(self):
        self.lbl_q.configure(text=f"{self._active} running" if self._active else "")


# ─────────────────────────────────────────────────────────────────────────────
# SPEC EDITOR VIEW
# ─────────────────────────────────────────────────────────────────────────────
class SpecEditorView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)
        self.text_color, self.stroke_color = "#ffffff", "#000000"
        self.selected_font_path = ""
        self._bg_pil = None
        self._bg_photo = None
        self._preview_photo = None
        self._preview_playing = False
        self._frame_queue: queue.Queue = queue.Queue(maxsize=4)

        # ── Left: Canvas ──────────────────────────────────────────────────────
        lf = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        lf.grid_rowconfigure(1, weight=1)
        lf.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(lf, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,4))
        ctk.CTkLabel(top, text="Preview", font=FONT_MAIN, text_color="#c0c0c0").pack(side="left")
        ctk.CTkButton(top, text="↺", width=32, height=28, font=FONT_SMALL,
                      fg_color="#23262e", hover_color="#2e323c",
                      command=self.reset_pos).pack(side="right")
        self.btn_play = ctk.CTkButton(top, text="▶ Play", width=70, height=28, font=FONT_SMALL,
                                       fg_color="#1a2820", hover_color="#243830",
                                       text_color="#4dcf9a", command=self.play_preview)
        self.btn_play.pack(side="right", padx=(0,6))

        self.c_w, self.c_h = 300, 534  # 9:16
        self.canvas = tk.Canvas(lf, width=self.c_w, height=self.c_h,
                                bg="#13151a", highlightthickness=0, cursor="fleur")
        self.canvas.grid(row=1, column=0, pady=6)
        self.text_pos = (self.c_w//2, self.c_h//2)
        self._drag = {"x":0,"y":0,"item":None}
        self.canvas.bind("<ButtonPress-1>", lambda e: self._drag.update({"x":e.x,"y":e.y,"item":self.canvas.find_withtag("q") or None}))
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self._drag.update({"item":None}))

        # Buttons row
        br = ctk.CTkFrame(lf, fg_color="transparent")
        br.grid(row=2, column=0, sticky="ew", padx=12, pady=(4,12))
        br.grid_columnconfigure((0,1), weight=1)
        self.btn_test = ctk.CTkButton(br, text="▶ Test", font=FONT_SMALL,
                                       fg_color=ACCENT_TEAL, hover_color="#006060",
                                       command=self.test_gen)
        self.btn_test.grid(row=0, column=0, padx=(0,4), sticky="ew")
        self.btn_save = ctk.CTkButton(br, text="Save", font=FONT_SMALL,
                                       fg_color="#23262e", hover_color="#2e323c",
                                       command=self.save_yaml)
        self.btn_save.grid(row=0, column=1, padx=(4,0), sticky="ew")



        # ── Right: Settings (scrollable) ───────────────────────────────────────
        rf = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        rf.grid(row=0, column=1, sticky="nsew")
        rf.grid_columnconfigure(0, weight=1)

        def section(title, row):
            f = ctk.CTkFrame(rf, fg_color="#1c1f27", corner_radius=8)
            f.grid(row=row, column=0, sticky="ew", pady=(0,8))
            f.grid_columnconfigure((0,1), weight=1)
            ctk.CTkLabel(f, text=title, font=FONT_MAIN, text_color="#888").grid(
                row=0, column=0, columnspan=2, padx=14, pady=(12,8), sticky="w")
            return f

        # ── Profile ───────────────────────────────────────────────────────────
        pf = section("Profile", 0)
        pf.grid_columnconfigure((0,1,2), weight=1)
        self.profile_var = ctk.StringVar(value=config.get_active_profile())
        self.opt_prof = ctk.CTkOptionMenu(pf, values=config.list_profiles(),
                                           variable=self.profile_var, command=self.load_profile,
                                           fg_color="#23262e", button_color="#23262e",
                                           button_hover_color=ACCENT_TEAL, font=FONT_SMALL)
        self.opt_prof.grid(row=1, column=0, columnspan=3, padx=14, pady=(0,4), sticky="ew")
        
        self.btn_save_pf = ctk.CTkButton(pf, text="Save Changes", font=FONT_SMALL, fg_color=ACCENT_TEAL, hover_color="#006060",
                      command=self.save_yaml)
        self.btn_save_pf.grid(row=2, column=0, padx=(14,4), pady=(0,12), sticky="ew")
        ctk.CTkButton(pf, text="+ New", font=FONT_SMALL, fg_color="#23262e", hover_color="#2e323c",
                      command=self.new_profile).grid(row=2, column=1, padx=(4,4), pady=(0,12), sticky="ew")
        ctk.CTkButton(pf, text="Delete", font=FONT_SMALL, fg_color="#2a1a1a", hover_color="#4a1a1a",
                      command=self.del_profile).grid(row=2, column=2, padx=(4,14), pady=(0,12), sticky="ew")

        # ── Font ─────────────────────────────────────────────────────────────
        ff = section("Font", 1)
        ff.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ff, text="Typeface", font=FONT_SMALL, text_color="#555").grid(
            row=1, column=0, padx=14, sticky="w")
        current_font_name = Path(config.get_text_settings().get("font_path", "")).stem or "FreeSerifItalic"
        self.dd_font = DropdownButton(ff, current_font_name, sorted(SYSTEM_FONTS.keys()),
                                       self._on_font_select, width=280)
        self.dd_font.grid(row=2, column=0, columnspan=2, padx=14, pady=(2,12), sticky="w")

        # ── Colors ────────────────────────────────────────────────────────────
        cf2 = section("Colors", 2)
        self.btn_tc = ctk.CTkButton(cf2, text="Text color", font=FONT_SMALL,
                                     command=self.pick_tc)
        self.btn_tc.grid(row=1, column=0, padx=(14,4), pady=(0,12), sticky="ew")
        self.btn_sc = ctk.CTkButton(cf2, text="Stroke color", font=FONT_SMALL,
                                     command=self.pick_sc)
        self.btn_sc.grid(row=1, column=1, padx=(4,14), pady=(0,12), sticky="ew")

        # ── Sliders ───────────────────────────────────────────────────────────
        sf = section("Style", 3)
        sf.grid_columnconfigure((0,1), weight=1)
        self.font_size_var    = ctk.IntVar(value=72)
        self.stroke_width_var = ctk.IntVar(value=0)
        self.wrap_var         = ctk.IntVar(value=30)
        self.fadein_var       = ctk.DoubleVar(value=0.5)
        self.volume_var       = ctk.DoubleVar(value=1.0)
        self.duration_var     = ctk.IntVar(value=10)

        def sl(parent, label, row, var, lo, hi, fmt, col=0, cspan=2):
            lbl_v = ctk.CTkLabel(parent, text=fmt(var.get()), font=FONT_SMALL, text_color=ACCENT_GOLD)
            ctk.CTkLabel(parent, text=label, font=FONT_SMALL, text_color="#555").grid(
                row=row, column=0, padx=14, sticky="w")
            lbl_v.grid(row=row, column=1, padx=14, sticky="e")
            ctk.CTkSlider(parent, from_=lo, to=hi, variable=var, progress_color=ACCENT_TEAL,
                          command=lambda v: (lbl_v.configure(text=fmt(v)), self.update_preview())
                          ).grid(row=row+1, column=col, columnspan=cspan, padx=14, pady=(2,8), sticky="ew")

        sl(sf, "Font Size",    1, self.font_size_var,    20, 150, lambda v: str(int(v)))
        sl(sf, "Stroke Width", 3, self.stroke_width_var, 0,  10,  lambda v: f"{int(v)}px")
        sl(sf, "Wrap Width",   5, self.wrap_var,         10, 60,  lambda v: str(int(v)))

        af = section("Audio & Timing", 4)
        sl(af, "Video Duration", 1, self.duration_var, 5, 60, lambda v: f"{int(v)}s")
        sl(af, "Music Volume",   3, self.volume_var, 0.0, 1.0, lambda v: f"{int(float(v)*100)}%")
        sl(af, "Text Fade-In",   5, self.fadein_var, 0.0, 3.0, lambda v: f"{float(v):.1f}s")

        # ── Folders & Content ─────────────────────────────────────────────────
        xf = section("Assets & Content", 5)
        xf.grid_columnconfigure(0, weight=1)

        # ── FolderPicker helper ───────────────────────────────────────────────
        def folder_picker(parent, label, base_key, row, attr_name):
            """
            Visual folder picker: scans <base_dir> for subdirs, shows each
            as a pill button with file count. Also lets user create a new subfolder.
            """
            base_dir = PROJECT_ROOT / self._base_path(base_key)

            hdr = ctk.CTkFrame(parent, fg_color="transparent")
            hdr.grid(row=row, column=0, sticky="ew", padx=14, pady=(10,0))
            hdr.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(hdr, text=label, font=FONT_SMALL, text_color="#555").grid(
                row=0, column=0, sticky="w")

            # "New folder" mini-button
            def _create_new():
                name = simpledialog.askstring(f"New {label}", "Folder name:", parent=self)
                if not name or not name.strip(): return
                new_dir = base_dir / name.strip()
                new_dir.mkdir(parents=True, exist_ok=True)
                _rebuild(name.strip())
                self._log(f"Created folder: {new_dir.relative_to(PROJECT_ROOT)}")

            ctk.CTkButton(hdr, text="+ folder", width=64, height=22, font=FONT_SMALL,
                          fg_color="#1c2030", hover_color="#262d3c",
                          command=_create_new).grid(row=0, column=1, sticky="e")

            # Pills container
            pills = ctk.CTkFrame(parent, fg_color="transparent")
            pills.grid(row=row+1, column=0, sticky="ew", padx=14, pady=(4,0))

            selected_var = ctk.StringVar(value="")
            setattr(self, attr_name, selected_var)

            def _rebuild(pre_select=""):
                for w in pills.winfo_children(): w.destroy()

                # "Root" option (empty subfolder = use base)
                all_opts = [("(root)", "", self._count_files(base_dir))]
                if base_dir.exists():
                    for d in sorted(base_dir.iterdir()):
                        if d.is_dir():
                            all_opts.append((d.name, d.name, self._count_files(d)))

                for col_i, (display, value, count) in enumerate(all_opts):
                    active = (value == (pre_select if pre_select else selected_var.get()))
                    color  = ACCENT_TEAL if active else "#23262e"
                    txt_c  = "white"     if active else "#888"
                    label_str = f"{display}  {count}f" if count > 0 else display

                    def _pick(v=value):
                        selected_var.set(v)
                        _rebuild()
                        self._load_bg_frame()  # refresh preview bg when folder changes

                    b = ctk.CTkButton(pills, text=label_str, width=0, height=26,
                                      font=FONT_SMALL, fg_color=color,
                                      hover_color="#2e5050" if active else "#2e323c",
                                      text_color=txt_c, command=_pick)
                    b.grid(row=0, column=col_i, padx=(0,4), pady=2, sticky="w")

                if pre_select:
                    selected_var.set(pre_select)

            self._folder_rebuilders = getattr(self, "_folder_rebuilders", {})
            self._folder_rebuilders[attr_name] = _rebuild
            _rebuild()

        PROJECT_ROOT_local = PROJECT_ROOT
        folder_picker(xf, "Backgrounds subfolder", "base_backgrounds", 1, "_bg_sel")
        folder_picker(xf, "Music subfolder",        "base_music",       3, "_music_sel")

        # Overlay image picker (single file from overlays dir)
        ov_hdr = ctk.CTkFrame(xf, fg_color="transparent")
        ov_hdr.grid(row=5, column=0, sticky="ew", padx=14, pady=(12,0))
        ov_hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ov_hdr, text="Overlay / Watermark", font=FONT_SMALL, text_color="#555").grid(
            row=0, column=0, sticky="w")

        ov_pills = ctk.CTkFrame(xf, fg_color="transparent")
        ov_pills.grid(row=6, column=0, sticky="ew", padx=14, pady=(4,0))

        self._overlay_sel = ctk.StringVar(value="")

        def _build_overlay_pills():
            for w in ov_pills.winfo_children(): w.destroy()
            ov_dir = PROJECT_ROOT / "bot_insta/assets/overlays"
            files = ["(none)"] + [f.name for f in ov_dir.iterdir() if f.suffix.lower() in (".png",".jpg",".webp")] if ov_dir.exists() else ["(none)"]
            for ci, fname in enumerate(files):
                val = "" if fname == "(none)" else fname
                active = (self._overlay_sel.get() == val)
                c = ACCENT_TEAL if active else "#23262e"
                def _pick(v=val): self._overlay_sel.set(v); _build_overlay_pills()
                ctk.CTkButton(ov_pills, text=fname, width=0, height=26,
                              font=FONT_SMALL, fg_color=c,
                              hover_color="#2e5050" if active else "#2e323c",
                              command=_pick).grid(row=0, column=ci, padx=(0,4), pady=2, sticky="w")

        _build_overlay_pills()
        self._build_overlay_pills = _build_overlay_pills

        ctk.CTkLabel(xf, text="Preview quote", font=FONT_SMALL, text_color="#555").grid(
            row=9, column=0, padx=14, sticky="w", pady=(6,0))
        self.txt_q = ctk.CTkTextbox(xf, height=65, font=FONT_SMALL)
        self.txt_q.grid(row=10, column=0, padx=14, pady=(2,12), sticky="ew")
        self.txt_q.insert("0.0", "Your motivational quote preview.")
        self.txt_q.bind("<KeyRelease>", lambda e: self.update_preview())


        self.load_profile(config.get_active_profile())

    # ── Font selection ────────────────────────────────────────────────────────
    def _on_font_select(self, name):
        self.selected_font_path = SYSTEM_FONTS.get(name, "")
        self.dd_font.set_label(name)
        self.update_preview()

    # ── Canvas ────────────────────────────────────────────────────────────────
    def reset_pos(self):
        self.text_pos = (self.c_w//2, self.c_h//2)
        self.update_preview()

    def _on_drag(self, e):
        if self._drag["item"]:
            dx, dy = e.x-self._drag["x"], e.y-self._drag["y"]
            self.text_pos = (self.text_pos[0]+dx, self.text_pos[1]+dy)
            self._drag["x"], self._drag["y"] = e.x, e.y
            self.update_preview()

    def _load_bg_frame(self):
        """Pick a random background video frame (single snapshot for static preview)."""
        def _worker():
            try:
                bg_dir = config.get_path("backgrounds")
                if not bg_dir.exists(): return
                videos = [f for f in bg_dir.iterdir() if f.suffix.lower() in (".mp4",".mov",".avi")]
                if not videos: return
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(str(random.choice(videos)), audio=False)
                t = random.uniform(0, min(clip.duration-0.1, 5.0))
                frame = clip.get_frame(t)
                clip.close()
                img = PIL.Image.fromarray(frame)
                src_ratio = img.width / img.height
                tgt_ratio = self.c_w / self.c_h
                if src_ratio > tgt_ratio:
                    nw = int(img.height * tgt_ratio); nh = img.height
                else:
                    nw = img.width; nh = int(img.width / tgt_ratio)
                left = (img.width - nw)//2; top = (img.height - nh)//2
                img = img.crop((left, top, left+nw, top+nh))
                img = img.resize((self.c_w, self.c_h), PIL.Image.LANCZOS)
                dark = PIL.Image.new("RGB", img.size, (0,0,0))
                self._bg_pil = PIL.Image.blend(img, dark, alpha=0.35)
                self._bg_photo = PIL.ImageTk.PhotoImage(self._bg_pil)
                self.after(0, self.update_preview)
            except Exception as e:
                print(f"[bg preview] {e}")
        threading.Thread(target=_worker, daemon=True).start()

    # ── Live video preview ────────────────────────────────────────────────────
    def play_preview(self):
        if self._preview_playing:
            self._stop_preview()
            return

        self._preview_playing = True
        self.btn_play.configure(text="■ Stop", text_color="#e05555", fg_color="#2a1a1a")
        # Pre-render text overlay (once)
        text_overlay = self._render_text_overlay()

        def _producer():
            try:
                bg_dir = config.get_path("backgrounds")
                videos = [f for f in bg_dir.iterdir() if f.suffix.lower() in (".mp4",".mov",".avi")]
                if not videos:
                    self.after(0, lambda: self._stop_preview("No videos found"))
                    return
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(str(random.choice(videos)), audio=False)
                target_fps = min(clip.fps, 24)
                tgt = self.c_w / self.c_h
                frame_delay = 1.0 / target_fps

                for frame in clip.iter_frames(fps=target_fps, dtype="uint8"):
                    if not self._preview_playing:
                        break
                    t0 = time.monotonic()
                    # Crop + resize
                    img = PIL.Image.fromarray(frame)
                    sr = img.width / img.height
                    if sr > tgt:
                        nw = int(img.height * tgt); nh = img.height
                    else:
                        nw = img.width; nh = int(img.width / tgt)
                    l2 = (img.width - nw)//2; t2 = (img.height - nh)//2
                    img = img.crop((l2, t2, l2+nw, t2+nh)).resize((self.c_w, self.c_h), PIL.Image.BILINEAR)
                    # Compose text
                    composed = PIL.Image.alpha_composite(img.convert("RGBA"), text_overlay)
                    photo = PIL.ImageTk.PhotoImage(composed)
                    # Throttle to target FPS
                    elapsed = time.monotonic() - t0
                    sleep_s = max(0.0, frame_delay - elapsed)
                    time.sleep(sleep_s)
                    try:
                        self._frame_queue.put_nowait(photo)
                    except queue.Full:
                        pass  # drop frame if consumer is behind

                clip.close()
            except Exception as e:
                print(f"[live preview] {e}")
                import traceback; traceback.print_exc()
            finally:
                self.after(0, self._stop_preview)

        threading.Thread(target=_producer, daemon=True).start()
        self._tick_frame()

    def _tick_frame(self):
        """Poll the frame queue and push to canvas (runs on main thread)."""
        if not self._preview_playing:
            return
        try:
            photo = self._frame_queue.get_nowait()
            self._preview_photo = photo  # prevent GC
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=photo)
        except queue.Empty:
            pass
        self.after(30, self._tick_frame)  # ~33 fps poll rate

    def _render_text_overlay(self) -> PIL.Image.Image:
        """Render the current text settings as a transparent RGBA overlay."""
        q = self.txt_q.get("0.0","end").strip() or "Preview"
        wrapped = textwrap.fill(q, width=self.wrap_var.get())
        fs = max(8, int(self.font_size_var.get() * self.c_w / 1080))
        try:
            fp = self.selected_font_path
            pil_font = PIL.ImageFont.truetype(fp, fs) if fp and Path(fp).exists() else PIL.ImageFont.load_default()
        except Exception:
            pil_font = PIL.ImageFont.load_default()

        overlay = PIL.Image.new("RGBA", (self.c_w, self.c_h), (0,0,0,0))
        draw = PIL.ImageDraw.Draw(overlay)
        bbox = draw.multiline_textbbox((0,0), wrapped, font=pil_font, align="center")
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        tx = self.text_pos[0] - tw//2
        ty = self.text_pos[1] - th//2
        sw = self.stroke_width_var.get()
        if sw > 0:
            sc = self._hex_to_rgb(self.stroke_color)+(255,)
            s = max(1, int(sw*self.c_w/1080))
            for dx,dy in [(-s,-s),(s,-s),(-s,s),(s,s),(0,-s),(0,s),(-s,0),(s,0)]:
                draw.multiline_text((tx+dx,ty+dy), wrapped, font=pil_font, fill=sc, align="center")
        draw.multiline_text((tx,ty), wrapped, font=pil_font,
                             fill=self._hex_to_rgb(self.text_color)+(255,), align="center")
        return overlay

    def _stop_preview(self, msg=""):
        self._preview_playing = False
        # Drain queue
        while not self._frame_queue.empty():
            try: self._frame_queue.get_nowait()
            except queue.Empty: break
        self.btn_play.configure(text="▶ Play", text_color="#4dcf9a", fg_color="#1a2820")
        if msg: self._log(msg)
        self.update_preview()  # restore static preview

    def update_preview(self):
        self.canvas.delete("all")
        q = self.txt_q.get("0.0","end").strip() or "Preview"
        wrapped = textwrap.fill(q, width=self.wrap_var.get())
        fs = max(8, int(self.font_size_var.get() * self.c_w/1080))

        # ── Load PIL font ──────────────────────────────────────────────────────
        try:
            if self.selected_font_path and Path(self.selected_font_path).exists():
                pil_font = PIL.ImageFont.truetype(self.selected_font_path, fs)
            else:
                pil_font = PIL.ImageFont.load_default()
        except Exception:
            pil_font = PIL.ImageFont.load_default()

        # ── Compose image ─────────────────────────────────────────────────────
        if self._bg_pil is not None:
            base = self._bg_pil.copy()
        else:
            base = PIL.Image.new("RGB",(self.c_w,self.c_h),(19,21,26))
        overlay = PIL.Image.new("RGBA",(self.c_w,self.c_h),(0,0,0,0))
        draw = PIL.ImageDraw.Draw(overlay)

        # Measure text to center it
        bbox = draw.multiline_textbbox((0,0), wrapped, font=pil_font, align="center")
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        tx = self.text_pos[0] - tw//2
        ty = self.text_pos[1] - th//2

        # Stroke
        sw = self.stroke_width_var.get()
        if sw > 0:
            sc = self._hex_to_rgb(self.stroke_color)+(255,)
            s = max(1, int(sw*self.c_w/1080))
            for dx,dy in [(-s,-s),(s,-s),(-s,s),(s,s),(0,-s),(0,s),(-s,0),(s,0)]:
                draw.multiline_text((tx+dx,ty+dy), wrapped, font=pil_font, fill=sc, align="center")

        # Main text
        tc = self._hex_to_rgb(self.text_color)+(255,)
        draw.multiline_text((tx,ty), wrapped, font=pil_font, fill=tc, align="center")

        composed = PIL.Image.alpha_composite(base.convert("RGBA"), overlay)
        self._preview_photo = PIL.ImageTk.PhotoImage(composed)
        self.canvas.create_image(0, 0, anchor="nw", image=self._preview_photo)

        # Invisible draggable hit area
        self.canvas.create_rectangle(tx, ty, tx+tw, ty+th, fill="", outline="", tags="q")

    # ── Color & directory helpers ─────────────────────────────────────────────
    def _base_path(self, key: str) -> str:
        return config._config.get("paths", {}).get(key, f"bot_insta/assets/{key.replace('base_', '')}")

    def _count_files(self, d: Path) -> int:
        if not d.exists() or not d.is_dir(): return 0
        return sum(1 for f in d.iterdir() if f.is_file())

    def _hex_to_rgb(self, c):
        try:
            if c.lower() in ("white","#ffffff"): return (255,255,255)
            if c.lower() in ("black","#000000"): return (0,0,0)
            h=c.lstrip("#"); return (int(h[:2],16),int(h[2:4],16),int(h[4:],16))
        except: return (255,255,255)

    def _is_light(self, c):
        try:
            if c.lower() in ("white","#ffffff"): return True
            if c.lower() in ("black","#000000"): return False
            h=c.lstrip("#"); r,g,b=int(h[:2],16),int(h[2:4],16),int(h[4:],16)
            return (0.299*r+0.587*g+0.114*b)>150
        except: return True

    def _set_cb(self, btn, c):
        try: btn.configure(fg_color=c, text_color="black" if self._is_light(c) else "white")
        except: pass

    def pick_tc(self):
        c = askcolor(title="Text Color", color=self.text_color, parent=self)[1]
        if c: self.text_color=c; self._set_cb(self.btn_tc, c); self.update_preview()

    def pick_sc(self):
        c = askcolor(title="Stroke Color", color=self.stroke_color, parent=self)[1]
        if c: self.stroke_color=c; self._set_cb(self.btn_sc, c); self.update_preview()

    # ── Profile CRUD ──────────────────────────────────────────────────────────
    def load_profile(self, name):
        config.reload()
        self.active_profile = name
        prof = config._config.get("profiles",{}).get(name,{})
        text, audio = prof.get("text",{}), prof.get("audio",{})

        self.text_color   = str(text.get("color","#ffffff"))
        self.stroke_color = str(text.get("stroke_color","#000000"))
        self.font_size_var.set(text.get("font_size",72))
        self.stroke_width_var.set(text.get("stroke_width",0))
        self.wrap_var.set(text.get("wrap_width",30))
        self.fadein_var.set(float(text.get("fadein",0.5)))
        self.volume_var.set(float(audio.get("volume",1.0)))
        
        fallback_dir = config._config.get("video",{}).get("duration", 10)
        self.duration_var.set(int(prof.get("duration", fallback_dir)))

        # Font
        fp = text.get("font_path","")
        self.selected_font_path = fp
        fn = Path(fp).stem if fp else "FreeSerifItalic"
        self.dd_font.set_label(fn)

        self._set_cb(self.btn_tc, self.text_color)
        self._set_cb(self.btn_sc, self.stroke_color)

        # Select folder pills from saved profile
        bg_sub = prof.get("backgrounds_subfolder", "")
        mu_sub = prof.get("music_subfolder", "")
        ov_img = prof.get("overlay_image", "")
        if hasattr(self, "_bg_sel"): self._bg_sel.set(bg_sub)
        if hasattr(self, "_music_sel"): self._music_sel.set(mu_sub)
        if hasattr(self, "_overlay_sel"):
            self._overlay_sel.set(ov_img)
            if hasattr(self, "_build_overlay_pills"): self._build_overlay_pills()
        # Rebuild pill buttons to reflect new selection
        for rebuilder in getattr(self, "_folder_rebuilders", {}).values():
            rebuilder()
        
        raw = text.get("position", "center")
        if raw == "center":
            self.text_pos = (self.c_w // 2, self.c_h // 2)
        elif isinstance(raw, list) and len(raw) == 2:
            rx = float(raw[0]) if raw[0] != "center" else 540.0
            self.text_pos = (int(rx * self.c_w / 1080), int(float(raw[1]) * self.c_h / 1920))
        else:
            self.text_pos = (self.c_w // 2, self.c_h // 2)

        self.opt_prof.configure(values=config.list_profiles()); self.profile_var.set(name)
        self._load_bg_frame()  # async: loads a bg frame then re-renders
        self.update_preview()

    def new_profile(self):
        name = simpledialog.askstring("New Profile","Name:",parent=self)
        if not name or not name.strip(): return
        try:
            config.create_profile(name.strip(), self.active_profile)
            self.load_profile(name.strip())
            self.app.dashboard.refresh_profiles()
            self._log(f"Created '{name}'")
        except Exception as e: messagebox.showerror("Error",str(e),parent=self)

    def del_profile(self):
        if len(config.list_profiles())<=1:
            messagebox.showwarning("Warning","Cannot delete the last profile.",parent=self); return
        if not messagebox.askyesno("Delete",f"Delete '{self.active_profile}'?",parent=self): return
        try:
            config.delete_profile(self.active_profile)
            rem = config.list_profiles()
            self.load_profile(rem[0])
            self.app.dashboard.refresh_profiles()
            self._log("Profile deleted")
        except Exception as e: messagebox.showerror("Error",str(e),parent=self)

    def save_yaml(self):
        cfg = config._config
        prof = cfg.setdefault("profiles",{}).setdefault(self.active_profile,{})
        text, audio = prof.setdefault("text",{}), prof.setdefault("audio",{})

        text["color"]        = self.text_color
        text["stroke_color"] = self.stroke_color
        text["font_size"]    = self.font_size_var.get()
        text["stroke_width"] = self.stroke_width_var.get()
        text["wrap_width"]   = self.wrap_var.get()
        text["fadein"]       = round(self.fadein_var.get(),2)
        audio["volume"]      = round(self.volume_var.get(),2)
        if self.selected_font_path:
            text["font_path"] = self.selected_font_path
        prof["backgrounds_subfolder"] = getattr(self, "_bg_sel", ctk.StringVar()).get()
        prof["music_subfolder"]       = getattr(self, "_music_sel", ctk.StringVar()).get()
        prof["overlay_image"]         = getattr(self, "_overlay_sel", ctk.StringVar()).get()
        prof["duration"]              = int(self.duration_var.get())

        x, y = self.text_pos
        ry = int(y*1920/self.c_h)
        text["position"] = ["center",ry] if abs(x-self.c_w/2)<12 else [int(x*1080/self.c_w),ry]

        cfg["active_profile"] = self.active_profile
        config.save()
        self.app.dashboard.refresh_profiles()
        self._log("Saved")
        self.btn_save.configure(text="Saved ✓", fg_color="#005a40")
        self.btn_save_pf.configure(text="Saved ✓", fg_color="#005a40")
        
        def revert():
            self.btn_save.configure(text="Save", fg_color="#23262e")
            self.btn_save_pf.configure(text="Save Changes", fg_color=ACCENT_TEAL)
            
        self.after(1800, revert)

    def _log(self, msg):
        print(f"[Log] {msg}")

    def test_gen(self):
        self.save_yaml()
        self.btn_test.configure(state="disabled", text="…")
        def run():
            try:
                config.reload()
                config._config["active_profile"] = self.active_profile
                p = create_reel()
                self.after(0, lambda: self._log(f"✓ {p.name}"))
                self.after(0, lambda: subprocess.Popen(["xdg-open", str(p)]))
            except Exception as e:
                self.after(0, lambda: self._log(f"Error: {e}"))
                import traceback; traceback.print_exc()
            finally:
                self.after(0, lambda: self.btn_test.configure(state="normal", text="▶ Test"))
        threading.Thread(target=run, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# CAPTIONS CONFIGURATION VIEW
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNTS CONFIGURATION VIEW
# ─────────────────────────────────────────────────────────────────────────────
class AccountsView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ctk.CTkLabel(header, text="Linked Accounts", font=FONT_MAIN, text_color="#c0c0c0").pack(side="left", padx=10)
        
        btn_add = ctk.CTkButton(header, text="+ Add Account", font=FONT_SMALL, width=120,
                                fg_color=ACCENT_TEAL, hover_color="#006060",
                                command=self.open_add_modal)
        btn_add.pack(side="right", padx=10)

        self.list_wrap = ctk.CTkScrollableFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.list_wrap.grid(row=1, column=0, sticky="nsew")
        self.list_wrap.grid_columnconfigure(0, weight=1)

        self.refresh_list()

    def refresh_list(self):
        for widget in self.list_wrap.winfo_children():
            widget.destroy()

        accounts = acc_manager.list_accounts()
        if not accounts:
            ctk.CTkLabel(self.list_wrap, text="No accounts linked. Add one to publish.",
                         font=FONT_SMALL, text_color="#555").pack(pady=40)
            return

        for acc in accounts:
            card = ctk.CTkFrame(self.list_wrap, fg_color="#23262e", corner_radius=6)
            card.pack(fill="x", padx=10, pady=5)
            
            alias = acc.get('name', 'Account')
            icon_img = create_platform_icon(acc['platform'])
            info = f"  {alias}"

            ctk.CTkLabel(card, text=info, image=icon_img, compound="left", padx=8, font=FONT_MAIN, text_color="white").pack(side="left", padx=15, pady=15)
            
            # Status badge
            status = acc.get("status", "Unknown")
            status_color = "#888"
            if status == "Active": status_color = "#4dcf9a"
            elif status == "Error": status_color = "#e05555"

            lbl_status = ctk.CTkLabel(card, text=f"• {status}", font=FONT_SMALL, text_color=status_color)
            lbl_status.pack(side="left", padx=15)

            # Actions
            btn_del = ctk.CTkButton(card, text="Delete", font=FONT_SMALL, width=60, fg_color="#e05555", hover_color="#803030", command=lambda a=acc['id']: self.delete_acc(a))
            btn_del.pack(side="right", padx=10)

            btn_verify = ctk.CTkButton(card, text="Verify", font=FONT_SMALL, width=60, fg_color="#2e323c", hover_color="#444", command=lambda a=acc['id']: self.verify_acc(a))
            btn_verify.pack(side="right", padx=10)

    def verify_acc(self, acc_id):
        acc = acc_manager.get_account(acc_id)
        if not acc: return
        
        acc_manager.update_status(acc_id, "Verifying...")
        self.refresh_list()
        
        def run_verification():
            try:
                creds = acc.get("credentials", {})
                platform = acc.get("platform")
                if platform == "Instagram":
                    from instagrapi import Client
                    cl = Client()
                    # Real login attempt, throws exception if unauthorized
                    session_path = PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json"
                    if session_path.exists():
                        try: cl.load_settings(session_path)
                        except: pass
                    cl.login(creds.get("username", ""), creds.get("password", ""))
                    cl.dump_settings(session_path)
                    acc_manager.update_status(acc_id, "Active")
                elif platform == "YouTube":
                    import json, os
                    path = creds.get("youtube_client_secrets", "")
                    if os.path.exists(path) and path.endswith('.json'):
                        with open(path, 'r') as f:
                            json.load(f)
                        acc_manager.update_status(acc_id, "Active")
                    else:
                        raise ValueError("Invalid client_secrets path")
                elif platform == "TikTok":
                    path = creds.get("tiktok_session_id", "")
                    if len(path) > 7:
                        acc_manager.update_status(acc_id, "Active")
                    else:
                        raise ValueError("Invalid Session ID / cookie path")
            except Exception as e:
                import logging
                logging.error(f"Verify Error for {acc_id}: {e}")
                acc_manager.update_status(acc_id, "Error")
            finally:
                self.after(0, self.refresh_list)
                
        import threading
        threading.Thread(target=run_verification, daemon=True).start()

    def delete_acc(self, acc_id):
        acc_manager.delete_account(acc_id)
        self.app.dashboard.refresh_profiles()
        self.refresh_list()

    def open_add_modal(self):
        AddAccountModal(self)

class AddAccountModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Account")
        self.geometry("400x380")
        self.resizable(False, False)
        self.configure(fg_color="#1c1f27")
        self.transient(parent.app)
        self.after(150, self.grab_set)

        self.parent_view = parent

        ctk.CTkLabel(self, text="Account Name (Alias):", font=FONT_SMALL, text_color="#c0c0c0").pack(pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=250, fg_color="#23262e", border_color="#333", text_color="white")
        self.name_entry.pack(pady=5)

        self.platform_var = ctk.StringVar(value="Instagram")
        ctk.CTkLabel(self, text="Platform:", font=FONT_MAIN, text_color="#c0c0c0").pack(pady=(15, 5))
        
        self.opt_platform = ctk.CTkOptionMenu(self, values=["Instagram", "TikTok", "YouTube"], 
                                              variable=self.platform_var, command=self.on_platform_change)
        self.opt_platform.pack(pady=5)

        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.entries = {}
        self.on_platform_change("Instagram")

        ctk.CTkButton(self, text="Save", font=FONT_MAIN, fg_color=ACCENT_TEAL, hover_color="#006060", command=self.save).pack(pady=20)

    def on_platform_change(self, choice):
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        if choice == "Instagram":
            ctk.CTkLabel(self.form_frame, text="Username:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            ctk.CTkLabel(self.form_frame, text="Password:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e2 = ctk.CTkEntry(self.form_frame, width=250, show="*", fg_color="#23262e", border_color="#333", text_color="white")
            e2.pack(pady=5)
            self.entries = {"username": e1, "password": e2}
        elif choice == "TikTok":
            ctk.CTkLabel(self.form_frame, text="Session ID string / cookie.txt path:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            self.entries = {"tiktok_session_id": e1}
        elif choice == "YouTube":
            ctk.CTkLabel(self.form_frame, text="Path to client_secrets.json:", font=FONT_SMALL, text_color="#888").pack(anchor="w")
            e1 = ctk.CTkEntry(self.form_frame, width=250, fg_color="#23262e", border_color="#333", text_color="white")
            e1.pack(pady=5)
            self.entries = {"youtube_client_secrets": e1}

    def save(self):
        alias_name = self.name_entry.get().strip() or "My Account"
        platform = self.platform_var.get()
        creds = {k: v.get() for k, v in self.entries.items()}
        acc_manager.add_account(alias_name, platform, creds)
        self.parent_view.refresh_list()
        self.parent_view.app.dashboard.refresh_profiles()
        self.destroy()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class BotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
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
