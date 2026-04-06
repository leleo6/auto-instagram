import customtkinter as ctk
from datetime import datetime
from tkcalendar import Calendar

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL
from bot_insta.src.core.history_manager import history_manager

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

    def _load_events(self, date_str: str):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        events = history_manager.get_events_by_date(date_str)
        if not events:
            ctk.CTkLabel(
                self.scroll_list,
                text="No videos generated or uploaded on this date.",
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
            ctk.CTkLabel(mid, text=f"Time: {time_str} | Account: {ev.get('account_id', 'local')} | ID: {ev.get('media_id', 'N/A')}", 
                         font=FONT_SMALL, text_color="#888").pack(anchor="w")

    def refresh(self):
        """Allows app to refresh view if data changed externally."""
        self._highlight_active_days()
        self._on_date_select(None)
