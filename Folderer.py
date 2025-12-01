import os, json, sys, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText


class Folderer(tk.Tk):
    APP_VERSION = "v1.0.0"
    SETTINGS_FILE = Path.home() / ".folderer_settings.json"
    THEMES = {
        "light":  dict(bg="#f3f4f6", text="#111827", muted="#6b7280", entry="#ffffff", btn="#ffffff", border="#d1d5db"),
        "dark":   dict(bg="#070B14", text="#e5e7eb", muted="#9ca3af", entry="#0A1220", btn="#111B2C", border="#233146"),
        "forest": dict(bg="#06110B", text="#E7F2EA", muted="#A9C4B2", entry="#0A1A12", btn="#0E2418", border="#1B3A2A"),
    }

    def __init__(self):
        super().__init__()
        self.title("Folderer")
        self.geometry("760x520")
        self.minsize(700, 470)

        # Vars
        self.base = tk.StringVar(value="New Folder")
        self.path = tk.StringVar(value=str(Path.cwd()))
        self.numbered = tk.BooleanVar(value=True)
        self.count = tk.StringVar(value="5")
        self.start = tk.StringVar(value="1")
        self.sep = tk.StringVar(value=" ")
        self.pad = tk.StringVar(value="0")  # zero-pad WIDTH (0=no padding, 2=01, 3=001)

        self.theme = tk.StringVar(value="Light")  # Light/Dark/Forest
        self.default_path = tk.StringVar(value=str(Path.cwd()))

        # Warning toggles (persisted)
        self.warn_folder_files_confirm = True
        self.warn_create_many = True

        self.style = ttk.Style(self)
        self._after_preview = None
        self._icon_img = None  # keep reference for iconphoto
        self._c = self.THEMES["dark"]  # active theme colors
        self.gear_btn = self.back_btn = None

        self._load_settings()
        self._ui()
        self._set_window_icon()
        self._wire_events()

        self._apply_theme()
        self._toggle_numbering()
        self._schedule_preview()
        self._show(self.main)

    # ---------- icon ----------
    def _resource_path(self, name: str) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / name

    def _set_window_icon(self):
        ico = self._resource_path("folderer.ico")
        png = self._resource_path("folderer.png")
        loaded = False

        if png.exists():
            try:
                self._icon_img = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icon_img)
                loaded = True
            except Exception:
                pass

        if not loaded and ico.exists():
            try:
                self.iconbitmap(str(ico))
                loaded = True
            except Exception:
                pass

        if not loaded:
            messagebox.showwarning(
                "Icon not loaded",
                "Couldn’t load folderer.png or folderer.ico.\n\n"
                f"Looked in:\n{self._resource_path('')}\n\n"
                "Fix: put a valid 'folderer.png' (recommended) or 'folderer.ico' next to Folderer.py.\n"
                "Also make sure Windows isn’t hiding extensions (so it’s not folderer.ico.png)."
            )

    # ---------- UI ----------
    def _ui(self):
        root = ttk.Frame(self, padding=14)
        root.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.main = ttk.Frame(root)
        self.settings = ttk.Frame(root)
        for f in (self.main, self.settings):
            f.grid(row=0, column=0, sticky="nsew")

        self._ui_main()
        self._ui_settings()

    def _square_btn(self, parent, text, cmd, size=40, font=("Segoe UI Symbol", 16)):
        box = ttk.Frame(parent, width=size, height=size)
        box.grid_propagate(False)
        btn = tk.Button(
            box, text=text, command=cmd, font=font, relief="flat", bd=0,
            highlightthickness=1, cursor="hand2", takefocus=False
        )
        btn.place(x=0, y=0, relwidth=1, relheight=1)
        return box, btn

    def _ui_main(self):
        m = self.main
        m.columnconfigure(1, weight=1)
        m.rowconfigure(9, weight=1)

        header = ttk.Frame(m)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Folderer", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        gb, self.gear_btn = self._square_btn(header, "⛭", lambda: self._show(self.settings), size=40)
        gb.grid(row=0, column=1, sticky="e")

        ttk.Label(m, text="Folder base name:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 8))
        ttk.Entry(m, textvariable=self.base).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(m, text="Create in:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 8))
        row = ttk.Frame(m); row.grid(row=2, column=1, sticky="ew", pady=(0, 8)); row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.path).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Browse...", command=self._browse_path).grid(row=0, column=1, padx=(10, 0))

        ttk.Checkbutton(m, text="Number folders (Name 1, Name 2, ...)", variable=self.numbered)\
            .grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 10))

        opts = ttk.Frame(m); opts.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        opts.columnconfigure(7, weight=1)

        def spin(lbl, var, frm, to, c, w=8, padx=(6, 18)):
            ttk.Label(opts, text=lbl).grid(row=0, column=c, sticky="w")
            s = ttk.Spinbox(opts, from_=frm, to=to, textvariable=var, width=w)
            s.grid(row=0, column=c + 1, sticky="w", padx=padx)
            return s

        self.count_spin = spin("Count:", self.count, 1, 9999, 0)
        self.start_spin = spin("Start #:", self.start, 0, 999999, 2)

        ttk.Label(opts, text="Separator:").grid(row=0, column=4, sticky="w")
        self.sep_entry = ttk.Entry(opts, textvariable=self.sep, width=8)
        self.sep_entry.grid(row=0, column=5, sticky="w", padx=(6, 18))

        self.pad_spin = spin("Zero pad:", self.pad, 0, 10, 6, w=6, padx=(6, 0))

        vcmd = (self.register(lambda p: p == "" or p.isdigit()), "%P")
        for sp in (self.count_spin, self.start_spin, self.pad_spin):
            try: sp.configure(validate="key", validatecommand=vcmd)
            except tk.TclError: pass

        ttk.Label(m, text="Preview:").grid(row=5, column=0, sticky="w", padx=(0, 10), pady=(0, 6))
        self.preview = ttk.Label(m, text="", justify="left", wraplength=520)
        self.preview.grid(row=5, column=1, sticky="ew", pady=(0, 6))

        btns = ttk.Frame(m); btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(6, 10))
        btns.columnconfigure(3, weight=1)
        ttk.Button(btns, text="Create Folders", command=self._create).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(btns, text="Open Target Folder", command=self._open_target).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(btns, text="Folder Files", command=self._folder_files_here).grid(row=0, column=2)
        ttk.Button(btns, text="Clear Log", command=lambda: self._set_log("")).grid(row=0, column=4, sticky="e")

        ttk.Label(m, text="Log:").grid(row=7, column=0, sticky="w", padx=(0, 10), pady=(0, 6))
        self.log = ScrolledText(m, height=10, wrap="word")
        self.log.grid(row=9, column=0, columnspan=2, sticky="nsew")
        self._set_log("", append=False)

        self.tip = ttk.Label(m, text="Tip: If numbering is OFF, only 1 folder can be created (duplicates aren’t possible on Windows).")
        self.tip.grid(row=10, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _ui_settings(self):
        s = self.settings
        s.columnconfigure(0, weight=1)
        s.rowconfigure(2, weight=1)

        top = ttk.Frame(s); top.grid(row=0, column=0, sticky="ew", pady=(0, 12)); top.columnconfigure(1, weight=1)
        bb, self.back_btn = self._square_btn(top, "←", lambda: self._show(self.main), size=36, font=("Segoe UI Symbol", 14))
        bb.grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Settings", font=("Segoe UI", 16, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0))

        body = ttk.Frame(s); body.grid(row=1, column=0, sticky="nsew"); body.columnconfigure(0, weight=1)
        ttk.Label(body, text="Theme", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        tr = ttk.Frame(body); tr.grid(row=1, column=0, sticky="w")
        for i, name in enumerate(("Light", "Dark", "Forest")):
            ttk.Radiobutton(tr, text=name, value=name, variable=self.theme)\
                .grid(row=0, column=i, padx=(0, 18) if i < 2 else (0, 0))

        ttk.Separator(body).grid(row=2, column=0, sticky="ew", pady=14)

        ttk.Label(body, text='Default “Create in” folder', font=("Segoe UI", 11, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 6))
        row = ttk.Frame(body); row.grid(row=4, column=0, sticky="ew"); row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.default_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Browse...", command=self._browse_default_path).grid(row=0, column=1, padx=(10, 0))

        ttk.Separator(body).grid(row=5, column=0, sticky="ew", pady=14)

        bottom = ttk.Frame(s); bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.version = ttk.Label(bottom, text=self.APP_VERSION)
        self.version.grid(row=0, column=0, sticky="w")

        right = ttk.Frame(bottom)
        right.grid(row=0, column=1, sticky="e")
        ttk.Button(right, text="Reset warnings", command=self._reset_warnings).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(right, text="Save", command=self._save_and_back).grid(row=0, column=1)

    # ---------- Events ----------
    def _wire_events(self):
        for v in (self.base, self.path, self.numbered, self.count, self.start, self.sep, self.pad):
            v.trace_add("write", lambda *_: (self._toggle_numbering(), self._schedule_preview()))
        self.theme.trace_add("write", lambda *_: (self._apply_theme(), self._save_settings(), self._schedule_preview()))
        self.default_path.trace_add("write", lambda *_: (self.path.set(self.default_path.get()), self._save_settings()))
        self.bind("<Configure>", lambda e: e.widget is self and self._schedule_preview())

    # ---------- Dialogs (with "Don't show again") ----------
    def _confirm_with_dont_show(self, title: str, message: str, flag_name: str, icon_text="!") -> bool:
        if flag_name and not getattr(self, flag_name, True):
            return True

        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.resizable(False, False)
        win.configure(bg=self._c["bg"])
        win.grab_set()

        outer = tk.Frame(win, bg=self._c["bg"], padx=16, pady=14)
        outer.grid(sticky="nsew")
        outer.columnconfigure(1, weight=1)

        # High-contrast icon for dark/forest too
        icon = tk.Label(
            outer, text=icon_text, bg=self._c["bg"], fg=self._c["text"],
            font=("Segoe UI", 22, "bold"), width=2
        )
        icon.grid(row=0, column=0, rowspan=3, sticky="n", padx=(0, 12), pady=(0, 0))

        msg = tk.Label(
            outer, text=message, bg=self._c["bg"], fg=self._c["text"],
            justify="left", wraplength=520, font=("Segoe UI", 10)
        )
        msg.grid(row=0, column=1, sticky="w")

        dont = tk.BooleanVar(value=False)
        cb = None
        if flag_name:
            cb = tk.Checkbutton(
                outer, text="Don't show again", variable=dont,
                bg=self._c["bg"], fg=self._c["text"], activebackground=self._c["bg"],
                activeforeground=self._c["text"], selectcolor=self._c["entry"],
                highlightthickness=0
            )
            cb.grid(row=1, column=1, sticky="w", pady=(12, 0))

        res = {"ok": False}
        btns = tk.Frame(outer, bg=self._c["bg"])
        btns.grid(row=2, column=1, sticky="e", pady=(16, 0))

        def close(ok: bool):
            res["ok"] = ok
            if ok and flag_name and dont.get():
                setattr(self, flag_name, False)
                self._save_settings()
            win.destroy()

        ttk.Button(btns, text="No", command=lambda: close(False)).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(btns, text="Yes", command=lambda: close(True)).grid(row=0, column=1)

        win.bind("<Escape>", lambda *_: close(False))
        win.protocol("WM_DELETE_WINDOW", lambda: close(False))

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

        win.wait_window()
        return res["ok"]

    def _reset_warnings(self):
        msg = "This will re-enable all warning pop-ups.\n\nContinue?"
        if not self._confirm_with_dont_show("Reset warnings?", msg, flag_name=None, icon_text="!"):
            return
        self.warn_folder_files_confirm = True
        self.warn_create_many = True
        self._save_settings()
        messagebox.showinfo("Warnings reset", "All warnings have been re-enabled.")

    # ---------- Helpers ----------
    def _schedule_preview(self):
        if self._after_preview:
            try: self.after_cancel(self._after_preview)
            except Exception: pass
        self._after_preview = self.after(60, self._preview_safe)

    def _preview_safe(self):
        self._after_preview = None
        try: self._update_preview()
        except Exception:
            try: self.preview.config(text="(preview unavailable)")
            except Exception: pass

    def _int(self, s, d=0):
        try: return int(s)
        except Exception: return d

    def _clamp(self, v, lo, hi): return max(lo, min(hi, v))

    def _examples_n(self):
        w = self.winfo_width() or 760
        return 5 if w >= 980 else 4 if w >= 820 else 3

    def _pad_num(self, n, pad_width):
        pad_width = self._clamp(pad_width, 0, 10)
        s = str(n)
        return s if pad_width == 0 else s.zfill(pad_width)

    def _toggle_numbering(self):
        on = self.numbered.get()
        for w in (self.count_spin, self.start_spin, self.sep_entry, self.pad_spin):
            w.configure(state="normal" if on else "disabled")
        if not on:
            self.count.set("1")

    def _update_preview(self):
        self.preview.configure(wraplength=max(260, (self.winfo_width() or 760) - 260))
        base = (self.base.get() or "").strip() or "New Folder"
        if not self.numbered.get():
            self.preview.config(text=base)
            return
        count = self._clamp(self._int(self.count.get(), 1), 1, 9999)
        start = self._clamp(self._int(self.start.get(), 1), 0, 999999)
        padw = self._clamp(self._int(self.pad.get(), 0), 0, 10)
        sep = self.sep.get()
        n = min(self._examples_n(), count)
        items = [f"{base}{sep}{self._pad_num(start + i, padw)}" for i in range(n)]
        self.preview.config(text=", ".join(items) + (", ..." if count > n else ""))

    def _set_log(self, text, append=False):
        self.log.configure(state="normal")
        if not append: self.log.delete("1.0", "end")
        if text: self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show(self, frame): frame.tkraise()

    # ---------- File -> folder ----------
    @staticmethod
    def _unique_dest_path(dest: Path) -> Path:
        if not dest.exists():
            return dest
        stem, suffix, parent = dest.stem, dest.suffix, dest.parent
        i = 1
        while True:
            cand = parent / f"{stem} ({i}){suffix}"
            if not cand.exists():
                return cand
            i += 1

    def _folder_files_here(self):
        try:
            target = Path(self.path.get()).expanduser().resolve()
        except Exception:
            return messagebox.showerror("Bad path", "That path doesn't look valid.")
        if not target.exists():
            return messagebox.showerror("Path not found", f"This path doesn't exist:\n{target}")

        msg = (
            "This will move every file in the selected folder into its own\n"
            "folder named after the file (without extension).\n\n"
            f"Target:\n{target}\n\nContinue?"
        )
        if not self._confirm_with_dont_show("Folder files?", msg, "warn_folder_files_confirm", icon_text="!"):
            return

        moved = errors = 0
        for p in target.iterdir():
            if not p.is_file():
                continue
            dest_folder = target / p.stem
            try:
                dest_folder.mkdir(exist_ok=True)
                dest_file = self._unique_dest_path(dest_folder / p.name)
                shutil.move(str(p), str(dest_file))
                moved += 1
                self._set_log(f"📦 Moved: {p.name} -> {dest_folder.name}\\{dest_file.name}\n", append=True)
            except Exception as e:
                errors += 1
                self._set_log(f"❌ Error: {p.name} -> {e}\n", append=True)

        messagebox.showinfo("Done", f"Moved: {moved}\nErrors: {errors}\n\nTarget:\n{target}")

    # ---------- Theme ----------
    def _apply_theme(self):
        try: self.style.theme_use("clam")
        except tk.TclError: pass

        self._c = self.THEMES.get((self.theme.get() or "Light").lower(), self.THEMES["light"])
        c = self._c

        self.configure(bg=c["bg"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"])
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["text"])
        self.style.configure("TRadiobutton", background=c["bg"], foreground=c["text"])
        self.style.configure("TEntry", fieldbackground=c["entry"], foreground=c["text"])
        self.style.configure("TSpinbox", fieldbackground=c["entry"], foreground=c["text"])
        self.style.configure("TButton", background=c["btn"], foreground=c["text"], bordercolor=c["border"])
        self.style.map("TButton",
                       background=[("active", c["btn"]), ("pressed", c["bg"]), ("disabled", c["bg"])],
                       foreground=[("active", c["text"]), ("pressed", c["text"]), ("disabled", c["muted"])])
        self.style.map("TRadiobutton",
                       background=[("active", c["bg"]), ("disabled", c["bg"])],
                       foreground=[("active", c["text"]), ("disabled", c["muted"])])
        self.style.map("TCheckbutton",
                       background=[("active", c["bg"]), ("disabled", c["bg"])],
                       foreground=[("active", c["text"]), ("disabled", c["muted"])])

        for b in (self.gear_btn, self.back_btn):
            if b:
                b.configure(bg=c["btn"], fg=c["text"], activebackground=c["btn"], activeforeground=c["text"],
                            highlightbackground=c["border"], highlightcolor=c["border"], disabledforeground=c["muted"])

        for w in (getattr(self, "preview", None), getattr(self, "tip", None), getattr(self, "version", None)):
            if w: w.configure(foreground=c["muted"])

        try:
            self.log.configure(background=c["bg"], foreground=c["text"], insertbackground=c["text"],
                               highlightbackground=c["border"], highlightcolor=c["border"])
        except Exception:
            pass

    # ---------- Settings persistence ----------
    def _load_settings(self):
        try:
            if self.SETTINGS_FILE.exists():
                d = json.loads(self.SETTINGS_FILE.read_text(encoding="utf-8"))
                t = d.get("theme")
                if t in ("Light", "Dark", "Forest"): self.theme.set(t)
                p = d.get("default_target_path")
                if isinstance(p, str) and p.strip():
                    self.default_path.set(p.strip())
                    self.path.set(p.strip())

                warns = d.get("warnings", {})
                if isinstance(warns, dict):
                    self.warn_folder_files_confirm = bool(warns.get("folder_files_confirm", True))
                    self.warn_create_many = bool(warns.get("create_many", True))
        except Exception:
            pass

    def _save_settings(self):
        try:
            self.SETTINGS_FILE.write_text(json.dumps({
                "theme": self.theme.get(),
                "default_target_path": self.default_path.get(),
                "warnings": {
                    "folder_files_confirm": self.warn_folder_files_confirm,
                    "create_many": self.warn_create_many,
                }
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _save_and_back(self):
        self._save_settings()
        self._show(self.main)

    # ---------- Browse / actions ----------
    def _browse_path(self):
        d = filedialog.askdirectory(title="Choose a folder", initialdir=self.path.get() or None)
        if d: self.path.set(d)

    def _browse_default_path(self):
        d = filedialog.askdirectory(title='Choose default "Create in" folder', initialdir=self.default_path.get() or None)
        if d: self.default_path.set(d)

    def _open_target(self):
        try:
            p = Path(self.path.get()).expanduser().resolve()
            if not p.exists(): return messagebox.showerror("Path not found", f"This path doesn't exist:\n{p}")
            os.startfile(str(p))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _create(self):
        base = (self.base.get() or "").strip()
        if not base:
            return messagebox.showerror("Missing name", "Folder base name can't be empty.")
        try:
            target = Path(self.path.get()).expanduser().resolve()
        except Exception:
            return messagebox.showerror("Bad path", "That path doesn't look valid.")

        if not target.exists():
            if not messagebox.askyesno("Create path?", f"This folder doesn't exist:\n{target}\n\nCreate it?"):
                return
            try:
                target.mkdir(parents=True, exist_ok=True)
                self._set_log(f"Created target path: {target}\n", append=True)
            except Exception as e:
                return messagebox.showerror("Error creating path", str(e))

        if self.numbered.get():
            count = self._clamp(self._int(self.count.get(), 1), 1, 9999)
            start = self._clamp(self._int(self.start.get(), 1), 0, 999999)
            padw = self._clamp(self._int(self.pad.get(), 0), 0, 10)
            sep = self.sep.get()

            if count > 50:
                msg = (
                    f"You are about to create {count} folders.\n"
                    "This can take a moment and is harder to undo.\n\n"
                    f"Target:\n{target}\n\nContinue?"
                )
                if not self._confirm_with_dont_show("Create many folders?", msg, "warn_create_many", icon_text="!"):
                    return

            names = [f"{base}{sep}{self._pad_num(start + i, padw)}" for i in range(count)]
        else:
            names = [base]

        made = skipped = 0
        for name in names:
            p = target / name
            try:
                p.mkdir(exist_ok=False)
                made += 1
                self._set_log(f"✅ Created: {p}\n", append=True)
            except FileExistsError:
                skipped += 1
                self._set_log(f"⚠️ Exists (skipped): {p}\n", append=True)
            except Exception as e:
                self._set_log(f"❌ Error: {p} -> {e}\n", append=True)

        messagebox.showinfo("Done", f"Created: {made}\nSkipped: {skipped}\n\nPath:\n{target}")


if __name__ == "__main__":
    Folderer().mainloop()
