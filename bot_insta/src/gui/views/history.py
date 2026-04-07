import os
import threading
import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from tkcalendar import Calendar

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL, ACCENT_GOLD
from bot_insta.src.core.history_manager import history_manager
from bot_insta.src.core.config_loader import config
from bot_insta.src.core.account_manager import acc_manager
from bot_insta.src.core.uploader_factory import UploaderFactory
from bot_insta.src.gui.components.dropdown import DropdownButton
from bot_insta.src.gui.bootstrap import PROJECT_ROOT

class HistoryView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        # Grid: Left (List) | Right (Calendar)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # ── Left: Event List ──────────────────────────────────────────────────
        self.list_wrap = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.list_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_wrap.grid_columnconfigure(0, weight=1)
        self.list_wrap.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.list_wrap, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        self.lbl_selected_date = ctk.CTkLabel(
            header, text="Select a date", font=FONT_MAIN, text_color="#c0c0c0"
        )
        self.lbl_selected_date.pack(side="left")

        # Small circular button to sync orphans and view ALL history
        self.btn_view_all = ctk.CTkButton(
            header, text="👁", font=("Inter", 16), width=28, height=28, corner_radius=14,
            fg_color="#2e323c", hover_color="#3e4350",
            command=self._view_all_and_sync
        )
        self.btn_view_all.pack(side="right", padx=(10, 0))

        self.scroll_list = ctk.CTkScrollableFrame(
            self.list_wrap, fg_color="transparent", corner_radius=0
        )
        self.scroll_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        # ── Right: Calendar ───────────────────────────────────────────────────
        self.cal_wrap = ctk.CTkFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.cal_wrap.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            self.cal_wrap, text="Calendar", font=FONT_MAIN, text_color="#c0c0c0"
        ).pack(pady=(16, 12))

        # tkcalendar setup
        today = datetime.today()
        self.calendar = Calendar(
            self.cal_wrap,
            selectmode="day",
            year=today.year,
            month=today.month,
            day=today.day,
            background="#13151a",
            foreground="#c0c0c0",
            headersbackground="#0e1014",
            headersforeground="#ffffff",
            selectbackground=ACCENT_TEAL,
            selectforeground="white",
            normalbackground="#23262e",
            normalforeground="#c0c0c0",
            weekendbackground="#2a2d36",
            weekendforeground="#c0c0c0",
            othermonthbackground="#13151a",
            othermonthforeground="#555",
            othermonthwebackground="#13151a",
            othermonthweforeground="#555",
            bordercolor="#333",
            font="Inter 10"
        )
        self.calendar.pack(pady=10, padx=20, fill="both", expand=True)

        self.calendar.bind("<<CalendarSelected>>", self._on_date_select)

        # Highlight days with events
        self._highlight_active_days()
        
        # Select today initially
        self._on_date_select(None)

    def _highlight_active_days(self):
        active_dates = history_manager.get_all_active_dates()
        for date_str in active_dates:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                self.calendar.calevent_create(d, "Upload", "upload")
            except Exception:
                pass
        
        self.calendar.tag_config("upload", background="#2a4536", foreground="#4dcf9a")

    def _on_date_select(self, event):
        # selected date comes as a datetime.date object from selection_get()
        sel_date = self.calendar.selection_get()
        date_str = sel_date.strftime("%Y-%m-%d")
        self.lbl_selected_date.configure(text=f"Records for {date_str}")
        self._load_events(date_str)

    def _load_events(self, date_str: str = None):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        if date_str:
            events = history_manager.get_events_by_date(date_str)
        else:
            all_data = history_manager._cache if history_manager._cache is not None else history_manager._load()
            events = sorted(all_data, key=lambda x: x.get("timestamp", ""), reverse=True)
            
        if not events:
            ctk.CTkLabel(
                self.scroll_list,
                text="No videos found here.",
                font=FONT_SMALL,
                text_color="#555",
            ).pack(pady=40)
            return

        for ev in events:
            card = ctk.CTkFrame(self.scroll_list, fg_color="#23262e", corner_radius=6)
            card.pack(fill="x", pady=6, padx=4)

            # Left block: Status & Platform
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=12, pady=10)

            is_success = "Success" in ev.get("status", "") or "Generated" in ev.get("status", "")
            scolor = "#4dcf9a" if is_success else "#e05555"

            ctk.CTkLabel(left, text=ev.get("platform", "Local"), font=("Inter", 13, "bold"), text_color="#fff").pack(anchor="w")
            ctk.CTkLabel(left, text=ev.get("status", "Unknown"), font=FONT_SMALL, text_color=scolor).pack(anchor="w")

            # Middle block: Info
            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(side="left", padx=16, pady=10, fill="x", expand=True)

            try:
                time_str = datetime.fromisoformat(ev.get("timestamp", "")).strftime("%H:%M:%S")
            except Exception:
                time_str = "00:00"

            ctk.CTkLabel(mid, text=ev.get("filename", "unknown.mp4"), font=FONT_MAIN, text_color="#c0c0c0").pack(anchor="w")
            ctk.CTkLabel(mid, text=f"Time: {time_str} | Account: {ev.get('account_id', 'Unknown')} | ID: {ev.get('media_id', 'Unknown')}", 
                         font=FONT_SMALL, text_color="#888").pack(anchor="w")

            # Right block: Actions/Local Config
            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=16, pady=10)
            
            filename = ev.get("filename", "")
            local_path = config.get_path("output_dir") / filename
            if local_path.exists() and local_path.is_file():
                mb_size = local_path.stat().st_size / (1024 * 1024)
                ctk.CTkLabel(right, text=f"Available Local ({mb_size:.1f} MB)", font=FONT_SMALL, text_color="#4dcf9a").pack(side="top", anchor="e", pady=(0, 4))
                
                btn_row = ctk.CTkFrame(right, fg_color="transparent")
                btn_row.pack(side="top", anchor="e")
                
                btn_recycle = ctk.CTkButton(
                    btn_row, text="Recycle", font=FONT_SMALL, width=60, height=24,
                    fg_color=ACCENT_TEAL, hover_color="#006060",
                    command=lambda p=local_path, e=ev: self._show_recycle_modal(p, e)
                )
                btn_recycle.pack(side="left", padx=(0, 6))

                btn_delete = ctk.CTkButton(
                    btn_row, text="Delete", font=FONT_SMALL, width=60, height=24,
                    fg_color="#a83232", hover_color="#7a2121",
                    command=lambda p=local_path: self._delete_local_video(p)
                )
                btn_delete.pack(side="left")
            else:
                ctk.CTkLabel(right, text="Not available", font=FONT_SMALL, text_color="#555").pack(side="right")

    def _delete_local_video(self, file_path: Path):
        try:
            if file_path.exists():
                os.remove(file_path)
            self._on_date_select(None)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    def _show_recycle_modal(self, file_path: Path, ev: dict):
        import subprocess
        import PIL.Image
        from moviepy.editor import VideoFileClip
        
        modal = ctk.CTkToplevel(self)
        modal.title("Recycle Video")
        modal.geometry("450x650")
        modal.attributes("-topmost", True)
        modal.wait_visibility()
        modal.grab_set()

        ctk.CTkLabel(modal, text="Recycle & Upload", font=("Inter", 18, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(modal, text=f"File: {file_path.name}", font=FONT_SMALL, text_color="#aaa").pack(pady=(0, 10))

        # ── Video Preview ──
        try:
            with VideoFileClip(str(file_path)) as clip:
                frame_time = min(2.0, clip.duration / 2) if clip.duration else 0
                frame = clip.get_frame(frame_time)
                thumb_img = PIL.Image.fromarray(frame)
                
            thumb_h = 160
            thumb_w = int(160 * (thumb_img.width / thumb_img.height))
            ctk_img = ctk.CTkImage(light_image=thumb_img, dark_image=thumb_img, size=(thumb_w, thumb_h))
            
            lbl_thumb = ctk.CTkLabel(modal, image=ctk_img, text="", cursor="hand2")
            lbl_thumb.pack(pady=(0, 5))
            lbl_thumb.bind("<Button-1>", lambda event: subprocess.Popen(["xdg-open", str(file_path)]))
        except Exception as e:
            print("Could not load thumbnail:", e)

        btn_play = ctk.CTkButton(
            modal, text="▶ Preview Video (Audio & Video)", font=FONT_SMALL,
            fg_color="#23262e", hover_color="#2e323c", text_color="#4dcf9a",
            command=lambda: subprocess.Popen(["xdg-open", str(file_path)])
        )
        btn_play.pack(pady=(0, 20))

        options = acc_manager.fetch_options_for_dropdown()
        options = [o for o in options if o["id"] != "local"]
        
        if not options:
            ctk.CTkLabel(modal, text="No active accounts found.", text_color="#e05555").pack(pady=20)
            return

        ctk.CTkLabel(modal, text="Select Account", font=FONT_SMALL).pack(anchor="w", padx=20)
        selected_acc_var = {"dict": options[0]}
        dd_account = DropdownButton(
            modal, selected_acc_var["dict"]["id"], options, 
            lambda p: selected_acc_var.update({"dict": p}), width=360
        )
        dd_account.pack(padx=20, pady=(4, 10))

        ctk.CTkLabel(modal, text="Caption Preset", font=FONT_SMALL).pack(anchor="w", padx=20)
        cap_opts = ["Custom"] + config.list_captions()
        selected_cap_var = {"val": "Custom"}
        dd_cap = DropdownButton(
            modal, selected_cap_var["val"], cap_opts, 
            lambda c: selected_cap_var.update({"val": c}), width=360
        )
        dd_cap.pack(padx=20, pady=(4, 10))

        ctk.CTkLabel(modal, text="Custom Text (if Custom)", font=FONT_SMALL).pack(anchor="w", padx=20)
        tb_caption = ctk.CTkTextbox(modal, height=80, width=360)
        tb_caption.pack(padx=20, pady=(4, 20))

        lbl_status = ctk.CTkLabel(modal, text="", text_color=ACCENT_GOLD)
        lbl_status.pack(pady=5)

        def do_upload():
            btn_upload.configure(state="disabled")
            lbl_status.configure(text="Uploading...", text_color=ACCENT_GOLD)
            modal.update()
            
            cap_val = selected_cap_var["val"]
            if cap_val == "Custom":
                caption = tb_caption.get("1.0", "end").strip()
            else:
                data = config.get_caption_data(cap_val)
                caption = f"{data.get('description', '')}\n\n{data.get('hashtags', '')}".strip()

            target_acc = selected_acc_var["dict"]
            acc_id = target_acc["id"]
            
            def thread_task():
                try:
                    target_platform = target_acc["platform"]
                    creds = acc_manager.get_account(acc_id).get("credentials", {})
                    proxy = acc_manager.get_account(acc_id).get("proxy")
                    
                    if target_platform == "Instagram" and acc_id:
                        creds["session_override"] = str(PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json")
                        
                    uploader = UploaderFactory.get_uploader(target_platform)
                    abort_evt = threading.Event()
                    
                    lbl_status.configure(text=f"Uploading to {target_platform}...")
                    mid = uploader.upload(file_path, caption=caption, credentials=creds, proxy=proxy, abort_event=abort_evt)
                    
                    history_manager.log_event(file_path.name, target_platform, acc_id, "Success (Recycled)", mid)
                    acc_manager.update_status(acc_id, "Active")
                    
                    lbl_status.configure(text="Upload successful!", text_color="#4dcf9a")
                    self.after(1500, modal.destroy)
                    self._on_date_select(None)
                    self.app.accounts.refresh_list()
                except Exception as e:
                    history_manager.log_event(file_path.name, target_platform, acc_id, f"Failed Recycle: {str(e)[:50]}")
                    acc_manager.update_status(acc_id, "Error")
                    lbl_status.configure(text=f"Error: {str(e)}", text_color="#e05555")
                    btn_upload.configure(state="normal")
                    self._on_date_select(None)
                    self.app.accounts.refresh_list()

            threading.Thread(target=thread_task, daemon=True).start()

        btn_upload = ctk.CTkButton(modal, text="Upload Video", font=FONT_MAIN, fg_color=ACCENT_TEAL, hover_color="#006060", command=do_upload)
        btn_upload.pack(pady=10)

    def _view_all_and_sync(self):
        import datetime
        output_dir = config.get_path("output_dir")
        all_events = history_manager._cache if history_manager._cache is not None else history_manager._load()
        existing_filenames = {e.get("filename") for e in all_events}
        
        new_events = []
        if output_dir.exists():
            for file_path in output_dir.glob("*.mp4"):
                if "TEMP" in file_path.name or "MPY_wvf_snd" in file_path.name:
                    continue
                if file_path.name not in existing_filenames:
                    mtime = file_path.stat().st_mtime
                    dt = datetime.datetime.fromtimestamp(mtime)
                    entry = {
                        "date": dt.strftime("%Y-%m-%d"),
                        "timestamp": dt.isoformat(),
                        "filename": file_path.name,
                        "platform": "Unknown",
                        "account_id": "Unknown",
                        "status": "Generated",
                        "media_id": "Unknown"
                    }
                    new_events.append(entry)
                    existing_filenames.add(file_path.name)
        
        if new_events:
            all_events.extend(new_events)
            history_manager._save(all_events)
            self._highlight_active_days()
            
        self.lbl_selected_date.configure(text="All Video Records")
        self._load_events(date_str=None)

    def refresh(self):
        """Allows app to refresh view if data changed externally."""
        self._highlight_active_days()
        self._on_date_select(None)
