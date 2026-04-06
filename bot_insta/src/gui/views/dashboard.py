import customtkinter as ctk
import threading
import subprocess
import tkinter.simpledialog as simpledialog
from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL, ACCENT_GOLD
from bot_insta.src.core.config_loader import config
from bot_insta.src.core.account_manager import acc_manager
from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.core.uploader_factory import UploaderFactory
from bot_insta.src.core.history_manager import history_manager
from bot_insta.src.gui.components.dropdown import DropdownButton
from bot_insta.src.gui.utils import create_platform_icon, make_video_context
from bot_insta.src.gui.bootstrap import PROJECT_ROOT

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

        ctk.CTkFrame(ctrl, width=1, height=24, fg_color="#333").pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Quotes", font=FONT_SMALL, text_color="#555").pack(side="left", padx=(12,3))
        self.quotes_options = config.list_quote_groups()
        self.selected_quotes = ctk.StringVar(value=self.quotes_options[0] if self.quotes_options else "")
        self.dd_quotes = DropdownButton(ctrl, self.selected_quotes.get(), self.quotes_options,
                                        self._on_quotes, width=150)
        self.dd_quotes.pack(side="left", padx=(0,12))

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
        
        self.quotes_options = config.list_quote_groups()
        if self.selected_quotes.get() not in self.quotes_options:
            self.selected_quotes.set(self.quotes_options[0] if self.quotes_options else "")
        self.dd_quotes.update_options(self.quotes_options, self.selected_quotes.get())

    def _on_quotes(self, name):
        self.selected_quotes.set(name)

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
            acc_proxy = None
            if type(self.selected_platform_opt) is dict and self.selected_platform_opt.get("id") != "local":
                acc_id = self.selected_platform_opt["id"]
                acc = acc_manager.get_account(acc_id)
                if acc:
                    target_platform = acc.get("platform", "Local")
                    creds = acc.get("credentials", {})
                    acc_proxy = acc.get("proxy")

            try:
                ui("Generating…", "#888", ACCENT_GOLD)
                
                quotes_file_override = None
                sel_quotes = self.selected_quotes.get()
                if sel_quotes:
                    quotes_file_override = config.get_quote_file(sel_quotes)

                ctx = make_video_context(config, profile, quotes_file_override=quotes_file_override)
                reel_path = create_reel(ctx, progress_callback=_update_prog, abort_event=abort_evt)
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
                # No deshabilitamos el botón de Cancelar aún. Permitimos que cancele la subida.

                if target_platform != "Local":
                    ui(f"Uploading to {target_platform}…", "#888", prog=1.0)
                    try:
                        uploader_creds = creds.copy()
                        if target_platform == "Instagram" and acc_id:
                            uploader_creds["session_override"] = str(PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json")
                        
                        uploader = UploaderFactory.get_uploader(target_platform)
                        mid = uploader.upload(reel_path, caption=caption, credentials=uploader_creds, proxy=acc_proxy, abort_event=abort_evt)
                        ui(f"Uploaded  · ID {mid}", "#4dcf9a", "#00c070")
                        acc_manager.update_status(acc_id, "Active")
                        history_manager.log_event(reel_path.name, target_platform, acc_id, "Success", mid)
                    except Exception as e:
                        acc_manager.update_status(acc_id, "Error")
                        history_manager.log_event(reel_path.name, target_platform, acc_id, f"Failed: {str(e)[:50]}")
                        raise e
                else:
                    # "Local" → nothing extra
                    history_manager.log_event(reel_path.name, "Local", "local", "Generated")
                
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
                self.after(0, lambda: btn_cancel.configure(state="disabled", fg_color="transparent", text_color="#333"))
                config._config["active_profile"] = orig
                self._active -= 1
                self.after(0, self._update_q)

        threading.Thread(target=run, daemon=True).start()

    def _update_q(self):
        self.lbl_q.configure(text=f"{self._active} running" if self._active else "")
