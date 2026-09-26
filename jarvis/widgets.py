"""Floating desktop widgets sharing Core, Store and the single voice controller."""
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from .modules import MODULES
from .reminders import display_due

BG, PANEL, INK, CYAN, MUTED = "#0b1722", "#132634", "#e8f2f1", "#65dcff", "#a7bcbc"
TITLES = {"command": "JARVIS · Comandă", "tasks": "JARVIS · Task-uri",
          "reminders": "JARVIS · Remindere", "notes": "JARVIS · Notițe", "clock": "JARVIS · Ceas"}


def clamp_position(x, y, width, height, screen_width, screen_height):
    """Recover windows from disconnected displays onto the primary screen."""
    return max(0, min(x, max(0, screen_width-width))), max(0, min(y, max(0, screen_height-height-60)))


class WidgetPreferences:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS widgets (
                kind TEXT PRIMARY KEY, x INTEGER, y INTEGER,
                pinned INTEGER NOT NULL, visible INTEGER NOT NULL)""")

    def load(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return {row[0]: {"x": row[1], "y": row[2], "pinned": bool(row[3]), "visible": bool(row[4])}
                    for row in db.execute("SELECT kind,x,y,pinned,visible FROM widgets") if row[0] in TITLES}

    def save(self, kind, x, y, pinned, visible):
        if kind not in TITLES:
            raise ValueError("Widget necunoscut")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""INSERT INTO widgets VALUES(?,?,?,?,?) ON CONFLICT(kind) DO UPDATE SET
                x=excluded.x,y=excluded.y,pinned=excluded.pinned,visible=excluded.visible""",
                       (kind, int(x), int(y), int(bool(pinned)), int(bool(visible))))


def widget_rows(store, kind, module=None):
    """Read current data, never sample or duplicate domain records."""
    if kind == "notes":
        return store.memories(module)
    tasks = store.tasks(module)
    return [t for t in tasks if t["due_at"]] if kind == "reminders" else tasks


class WidgetManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.windows = {}
        self.capture_target = None
        self.preferences = WidgetPreferences(app.core.store.path.with_name("widgets.sqlite3"))
        self.saved = self.preferences.load()
        self.restore_timer = self.root.after(250, self.restore)

    def restore(self):
        self.restore_timer = None
        for kind, settings in self.saved.items():
            if settings["visible"]:
                self.open(kind)

    def open(self, kind):
        if kind not in TITLES:
            raise ValueError("Widget necunoscut")
        if kind in self.windows:
            self.windows[kind].window.deiconify()
            self.windows[kind].window.lift()
            return self.windows[kind]
        widget = FloatingWidget(self, kind, self.saved.get(kind, {}))
        self.windows[kind] = widget
        widget.window.update_idletasks()
        widget.persist(True)
        return widget

    def show_main(self):
        self.root.deiconify()
        self.root.lift()

    def activate_from_wake(self):
        widget = self.open("command")
        widget.window.lift()
        if widget.input.get().strip():
            self.app.voice.set_state("review", "Ai deja un mesaj în widget. Trimite-l sau apasă Stop înainte de o comandă nouă.")
            widget.input.focus_set()
        else:
            widget.response.configure(text="Te ascult. Așteaptă indicatorul ASCULT, apoi spune comanda.")
            widget.listen()

    def desktop_mode(self):
        if not self.windows:
            self.open("command")
            self.open("tasks")
        self.root.withdraw()

    def accept_transcript(self, text):
        widget = self.capture_target
        self.capture_target = None
        if widget and widget.kind in self.windows:
            if widget.input.get().strip():
                widget.input.insert("end", " " + text)
            else:
                widget.input.insert(0, text)
            widget.window.lift()
            widget.input.focus_set()
            return True
        return False

    def refresh(self):
        for widget in list(self.windows.values()):
            widget.refresh()

    def close(self):
        if self.restore_timer:
            self.root.after_cancel(self.restore_timer)
        for widget in list(self.windows.values()):
            widget.close(shutdown=True)


class FloatingWidget:
    def __init__(self, manager, kind, saved):
        self.manager, self.app, self.kind = manager, manager.app, kind
        self.timer = None
        self.last_rows = None
        self.window = tk.Toplevel(manager.root)
        self.window.title(TITLES[kind])
        self.window.configure(bg=BG)
        # Deliberately not transient: stays visible when the main window is hidden.
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        width, height = (370, 210) if kind == "clock" else (440, 410 if kind == "command" else 350)
        self.window.minsize(width, height)
        screen_w, screen_h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        index = list(TITLES).index(kind)
        columns = max(1, min(3, screen_w // 470))
        x, y = clamp_position(int(saved.get("x", screen_w-width-25-(index % columns)*460)),
                              int(saved.get("y", 45+(index // columns)*385)), width, height, screen_w, screen_h)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.pinned = tk.BooleanVar(value=saved.get("pinned", True))
        self.window.attributes("-topmost", self.pinned.get())
        header = tk.Frame(self.window, bg=PANEL, padx=12, pady=8)
        header.pack(fill="x")
        title = tk.Label(header, text=TITLES[kind].upper(), bg=PANEL, fg=CYAN, font=("Segoe UI", 10, "bold"), cursor="fleur")
        title.pack(side="left")
        title.bind("<ButtonPress-1>", self.start_drag)
        title.bind("<B1-Motion>", self.drag)
        title.bind("<ButtonRelease-1>", lambda e: self.persist(True))
        tk.Checkbutton(header, text="Deasupra", variable=self.pinned, command=self.pin,
                       bg=PANEL, fg=MUTED, selectcolor=BG, activebackground=PANEL).pack(side="right")
        self.body = tk.Frame(self.window, bg=BG, padx=14, pady=12)
        self.body.pack(fill="both", expand=True)
        self.module = tk.StringVar(value="toate")
        if kind in ("tasks", "reminders", "notes"):
            bar = tk.Frame(self.body, bg=BG)
            bar.pack(fill="x")
            self.label(bar, "Modul").pack(side="left", padx=(0, 8))
            combo = ttk.Combobox(bar, state="readonly", textvariable=self.module, values=["toate", *MODULES], width=14)
            combo.pack(side="left")
            combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
            self.build_records()
        elif kind == "command":
            self.build_command()
        else:
            self.time_label = self.label(self.body, "", 34, CYAN)
            self.time_label.pack(anchor="w")
            self.date_label = self.label(self.body, "", 11)
            self.date_label.pack(anchor="w")
        footer = tk.Frame(self.window, bg=PANEL, padx=8, pady=4)
        footer.pack(fill="x")
        self.button(footer, "Deschide JARVIS", manager.show_main).pack(side="left")
        self.button(footer, "Închide widget", self.close).pack(side="right")
        self.hint = self.label(self.body, "", 9, MUTED)
        self.hint.pack(anchor="w", pady=(8, 0))
        self.tick()

    def label(self, parent, text, size=10, color=INK):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size), justify="left", anchor="w", wraplength=390)

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=PANEL, fg=CYAN,
                         activebackground=CYAN, activeforeground=BG, relief="flat", padx=8, pady=6)

    def start_drag(self, event):
        self.drag_offset = (event.x_root-self.window.winfo_x(), event.y_root-self.window.winfo_y())

    def drag(self, event):
        x, y = event.x_root-self.drag_offset[0], event.y_root-self.drag_offset[1]
        self.window.geometry(f"{x:+d}{y:+d}")

    def pin(self):
        self.window.attributes("-topmost", self.pinned.get())
        self.persist(True)

    def persist(self, visible):
        try:
            x, y = self.window.winfo_x(), self.window.winfo_y()
            self.manager.preferences.save(self.kind, x, y, self.pinned.get(), visible)
            self.manager.saved[self.kind] = {"x": x, "y": y, "pinned": self.pinned.get(), "visible": visible}
        except (sqlite3.Error, OSError):
            self.hint.configure(text="Poziția nu a putut fi salvată. Datele sunt separate.")

    def build_records(self):
        wrap = tk.Frame(self.body, bg=BG)
        wrap.pack(fill="both", expand=True, pady=10)
        self.records = tk.Listbox(wrap, bg=PANEL, fg=INK, selectbackground="#315b70", selectforeground=INK,
                                 relief="flat", font=("Segoe UI", 10), exportselection=False, height=6)
        scroll = ttk.Scrollbar(wrap, command=self.records.yview)
        self.records.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.records.pack(fill="both", expand=True)
        self.records.bind("<Double-1>", lambda e: self.details())
        self.records.bind("<Return>", lambda e: self.details())
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x")
        self.button(row, "Detalii", self.details).pack(side="left")
        if self.kind in ("tasks", "reminders"):
            self.button(row, "✓ Finalizat", self.complete).pack(side="left", padx=5)
        self.button(row, "+ Adaugă", self.add_record).pack(side="right")

    def build_command(self):
        self.label(self.body, "J / A   ·   CONTROL LOCAL", 17, CYAN).pack(anchor="w", pady=(0, 6))
        self.voice_status = self.label(self.body, "Microfon oprit", 10, MUTED)
        self.voice_status.pack(fill="x")
        self.input = tk.Entry(self.body, bg=PANEL, fg=INK, insertbackground=CYAN, relief="flat", font=("Segoe UI", 11))
        self.input.pack(fill="x", pady=10, ipady=7)
        self.input.bind("<Return>", lambda e: self.send())
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x")
        self.button(row, "● Vorbește", self.listen).pack(side="left")
        self.button(row, "■ Stop", self.app.voice.stop).pack(side="left", padx=5)
        self.button(row, "Trimite →", self.send).pack(side="right")
        quick = tk.Frame(self.body, bg=BG)
        quick.pack(fill="x", pady=(8, 0))
        self.button(quick, "Task-uri ↗", lambda: self.manager.open("tasks")).pack(side="left")
        self.button(quick, "Notițe ↗", lambda: self.manager.open("notes")).pack(side="left", padx=4)
        self.button(quick, "Remindere ↗", lambda: self.manager.open("reminders")).pack(side="left")
        self.wake_button = self.button(self.body, "Hey Jarvis: oprit", self.app.voice.toggle_wake_button)
        self.wake_button.pack(fill="x", pady=(8, 0))
        self.response = self.label(self.body, "Transcrierea se verifică înainte de trimitere.", 10)
        self.response.pack(fill="both", expand=True, pady=(10, 0))

    def listen(self):
        self.manager.capture_target = self
        self.app.voice.listen()
        if self.app.voice.state != "listening":
            self.manager.capture_target = None

    def send(self):
        if self.app.send(self.input.get()):
            self.input.delete(0, "end")
            self.response.configure(text=self.app.voice.last_reply[:240])
            self.manager.refresh()

    def selected(self):
        selection = self.records.curselection()
        return self.rows[selection[0]] if selection and selection[0] < len(self.rows) else None

    def details(self):
        row = self.selected()
        if row:
            content = row.get("content", row.get("title", ""))
            if "due_at" in row:
                content += "\n\n" + display_due(row["due_at"])
            messagebox.showinfo(f"#{row['id']} · {row['module']}", content, parent=self.window)

    def complete(self):
        row = self.selected()
        if row:
            self.app.send(f"gata: {row['id']}")
            self.manager.refresh()

    def add_record(self):
        self.manager.show_main()
        self.app.select_module(self.module.get() if self.module.get() in MODULES else "general")
        self.app.show("memory" if self.kind == "notes" else "tasks")
        if self.kind == "notes":
            self.app.note_dialog()
        else:
            self.app.task_dialog(self.kind == "reminders")

    def refresh(self):
        if self.kind == "clock":
            now = datetime.now()
            self.time_label.configure(text=now.strftime("%H:%M:%S"))
            self.date_label.configure(text=now.strftime("%d.%m.%Y") + " · ora PC-ului")
        elif self.kind == "command":
            self.voice_status.configure(text=self.app.voice.title.cget("text"))
            wake_text = "Activează Hey Jarvis · ascultare locală"
            if self.app.voice.wake.enabled:
                wake_text = "Hey Jarvis: activ · " + ("microfon în așteptare" if self.app.voice.state == "armed" else "pauză")
            self.wake_button.configure(text=wake_text)
            self.hint.configure(text=f"Modul curent: {MODULES[self.app.module].label}")
        else:
            module = None if self.module.get() == "toate" else self.module.get()
            rows = widget_rows(self.app.core.store, self.kind, module)
            if rows != self.last_rows:
                selected_id = self.selected()["id"] if self.last_rows and self.selected() else None
                self.rows = rows
                self.last_rows = rows
                self.records.delete(0, "end")
                for i, row in enumerate(rows):
                    line = f"#{row['id']} [{row['module']}] " + row.get("content", row.get("title", "")).replace("\n", " ")
                    if self.kind == "reminders":
                        line = display_due(row["due_at"]) + " · " + line
                    self.records.insert("end", line)
                    if row["id"] == selected_id:
                        self.records.selection_set(i)
            self.hint.configure(text=f"{len(rows)} elemente · dublu-clic pentru detalii" if rows else "Nimic aici încă. Folosește + Adaugă.")

    def tick(self):
        try:
            self.refresh()
        except (sqlite3.Error, OSError):
            self.hint.configure(text="Datele nu sunt disponibile momentan.")
        self.timer = self.window.after(1000, self.tick)

    def close(self, shutdown=False):
        self.persist(shutdown)  # Preserve visible widgets for the next launch on app shutdown.
        if self.manager.capture_target is self:
            self.manager.capture_target = None
            self.app.voice.stop()
        if self.timer:
            self.window.after_cancel(self.timer)
        self.manager.windows.pop(self.kind, None)
        self.window.destroy()
        if not shutdown and not self.manager.windows and self.manager.root.state() == "withdrawn":
            self.manager.show_main()
