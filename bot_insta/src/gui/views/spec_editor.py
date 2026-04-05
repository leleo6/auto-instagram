import customtkinter as ctk
import tkinter as tk
from tkinter.colorchooser import askcolor
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
import threading, textwrap, random, time, queue, subprocess
from pathlib import Path
import PIL.Image, PIL.ImageDraw, PIL.ImageFont, PIL.ImageTk

from bot_insta.src.gui.style import FONT_SMALL, FONT_MAIN, ACCENT_TEAL, ACCENT_GOLD
from bot_insta.src.core.config_loader import config
from bot_insta.src.gui.components.dropdown import DropdownButton
from bot_insta.src.gui.bootstrap import SYSTEM_FONTS, PROJECT_ROOT
from bot_insta.src.gui.utils import make_video_context
from bot_insta.src.core.video_engine import create_reel

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
                ctx = make_video_context(config, self.active_profile)
                p = create_reel(ctx)
                self.after(0, lambda: self._log(f"✓ {p.name}"))
                self.after(0, lambda: subprocess.Popen(["xdg-open", str(p)]))
            except Exception as e:
                self.after(0, lambda: self._log(f"Error: {e}"))
                import traceback; traceback.print_exc()
            finally:
                self.after(0, lambda: self.btn_test.configure(state="normal", text="▶ Test"))
        threading.Thread(target=run, daemon=True).start()
