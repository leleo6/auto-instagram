import customtkinter as ctk
from datetime import datetime

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.core.scheduler_manager import scheduler_manager
import subprocess

class CollapsibleFrame(ctk.CTkFrame):
    def __init__(self, parent, title="Group", is_open=True):
        super().__init__(parent, fg_color="transparent")
        self.is_open = is_open
        
        self.btn = ctk.CTkButton(self, text=f"▼ {title}" if is_open else f"▶ {title}", 
                                 anchor="w", font=("Inter", 14, "bold"), fg_color="#181a20", 
                                 hover_color="#23262e", text_color="#c0c0c0", command=self.toggle)
        self.btn.pack(fill="x", pady=(5,0))
        
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if self.is_open:
            self.content.pack(fill="x", pady=(2, 5))

    def toggle(self):
        if self.is_open:
            self.content.pack_forget()
            self.btn.configure(text=self.btn.cget("text").replace("▼", "▶"))
            self.is_open = False
        else:
            self.content.pack(fill="x", pady=(2, 5))
            self.btn.configure(text=self.btn.cget("text").replace("▶", "▼"))
            self.is_open = True


class SchedulerView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──
        hdr = ctk.CTkFrame(self, fg_color="#1c1f27", height=50, corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="Upload Queue", font=("Inter", 16, "bold"), text_color="#fff").pack(side="left", padx=16)
        
        btn_refresh = ctk.CTkButton(hdr, text="↻ Refresh", font=FONT_SMALL, width=80, height=26,
                                     fg_color="#2e323c", hover_color="#3e4350",
                                     command=self.refresh)
        btn_refresh.pack(side="right", padx=16)

        # ── List ──
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#1c1f27", corner_radius=8)
        self.scroll.grid(row=1, column=0, sticky="nsew")

    def refresh(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        jobs = scheduler_manager.get_all_jobs()
        if not jobs:
            ctk.CTkLabel(self.scroll, text="No jobs scheduled.", font=FONT_SMALL, text_color="#555").pack(pady=40)
            return

        now_iso = datetime.now().isoformat()
        
        # Group jobs
        groups = {}
        for j in jobs:
            bid = j.get("batch_id", "Ungrouped")
            if bid not in groups:
                groups[bid] = []
            groups[bid].append(j)

        for bid, group_jobs in groups.items():
            is_recent = True  # Could toggle based on dates
            grp = CollapsibleFrame(self.scroll, title=bid, is_open=is_recent)
            grp.pack(fill="x", pady=5)

            for job in group_jobs:
                card = ctk.CTkFrame(grp.content, fg_color="#23262e", corner_radius=6)
                card.pack(fill="x", pady=4, padx=10)

                # Left block: Status & Time
                left = ctk.CTkFrame(card, fg_color="transparent")
                left.pack(side="left", padx=12, pady=10)
                
                sched_time = job.get("scheduled_time", "")
                try:
                    dt = datetime.fromisoformat(sched_time)
                    display_time = dt.strftime("%b %d, %H:%M:%S")
                except:
                    display_time = sched_time
                    
                is_overdue = sched_time <= now_iso and job.get("status") == "pending"
                tcolor = "#e0a555" if is_overdue else "#c0c0c0"

                ctk.CTkLabel(left, text=display_time, font=("Inter", 13, "bold"), text_color=tcolor).pack(anchor="w")
                
                status = job.get("status", "unknown")
                scolor = {"pending": "#5599e0", "processing": ACCENT_TEAL, "failed": "#e05555"}.get(status, "#888")
                ctk.CTkLabel(left, text=status.capitalize(), font=FONT_SMALL, text_color=scolor).pack(anchor="w")

                # Middle block: Info
                mid = ctk.CTkFrame(card, fg_color="transparent")
                mid.pack(side="left", padx=16, pady=10, fill="x", expand=True)

                is_pregen = job.get("type") == "upload_only"
                jmode = "Pre-Gen Video attached" if is_pregen else "Just-In-Time Generation"
                
                ctk.CTkLabel(mid, text=f"Platform: {job.get('platform')} | Account: {job.get('account_id')}", font=FONT_MAIN, text_color="#c0c0c0").pack(anchor="w")
                ctk.CTkLabel(mid, text=jmode, font=FONT_SMALL, text_color="#888").pack(anchor="w")
                
                if job.get("error_msg"):
                    ctk.CTkLabel(mid, text=f"Error: {job.get('error_msg')}", font=FONT_SMALL, text_color="#e05555").pack(anchor="w")

                # Right block: Actions
                right = ctk.CTkFrame(card, fg_color="transparent")
                right.pack(side="right", padx=16, pady=10)
                
                # Preview button if video already exists
                if is_pregen and job.get("file_path"):
                    btn_play = ctk.CTkButton(
                        right, text="▶ Preview", font=FONT_SMALL, width=80, height=26,
                        fg_color="transparent", hover_color="#2e323c", text_color="#4dcf9a",
                        command=lambda p=job.get("file_path"): subprocess.Popen(["xdg-open", str(p)])
                    )
                    btn_play.pack(side="left", padx=(0, 10))

                    btn_reroll = ctk.CTkButton(
                        right, text="↺ Reroll", font=FONT_SMALL, width=80, height=26,
                        fg_color="#182335", hover_color="#213350", text_color="#5599e0",
                        command=lambda j=job: self._reroll_job(j)
                    )
                    btn_reroll.pack(side="left", padx=(0, 10))

                btn_delete = ctk.CTkButton(
                    right, text="Cancel Job", font=FONT_SMALL, width=80, height=26,
                    fg_color="#3a1c1c", hover_color="#5a1c1c",
                    command=lambda jid=job["id"]: self._delete_job(jid)
                )
                btn_delete.pack(side="left")

    def _delete_job(self, jid):
        scheduler_manager.delete_job(jid)
        self.refresh()

    def _reroll_job(self, job):
        import traceback, os, threading
        from bot_insta.src.core.video_engine import create_reel
        from bot_insta.src.gui.utils import make_video_context
        from bot_insta.src.core.config_loader import config
        
        job_id = job["id"]
        old_path = job.get("file_path")
        
        scheduler_manager.update_job_status(job_id, "Rerolling...")
        self.refresh()
        
        def worker():
            try:
                # Optionally delete old video
                if old_path and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
                
                profile = job.get("profile", "default")
                sel_quotes = job.get("quotes_override")
                quotes_file_override = config.get_quote_file(sel_quotes) if sel_quotes else None
                
                ctx = make_video_context(config, profile, quotes_file_override=quotes_file_override)
                # Create reel blocking in this thread
                new_reel_path = create_reel(ctx)
                
                # Import here to avoid circular dep
                from bot_insta.src.core.history_manager import history_manager
                history_manager.log_event(new_reel_path.name, job.get("platform", "Local"), job.get("account_id", "local"), "Generated (Reroll)")
                
                scheduler_manager.update_job_file(job_id, str(new_reel_path))
                scheduler_manager.update_job_status(job_id, "pending")
                self.after(0, self.refresh)
            except Exception as e:
                traceback.print_exc()
                scheduler_manager.update_job_status(job_id, "failed", str(e))
                self.after(0, self.refresh)
                
        threading.Thread(target=worker, daemon=True).start()
