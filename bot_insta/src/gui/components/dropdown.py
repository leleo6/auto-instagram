import tkinter as tk
import customtkinter as ctk
from bot_insta.src.gui.style import FONT_SMALL, ACCENT_TEAL
from bot_insta.src.gui.utils import create_platform_icon

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
                if type(o) is dict and o.get("id") == current_id:
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
            self.btn.configure(text=f" {o.get('label', 'Local')}  ▾", image=icon)
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
