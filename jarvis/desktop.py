"""Native desktop adapter. Core and providers remain independent of Tk."""
import tkinter as tk
import queue
import threading
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from .modules import MODULES
from .reminders import ReminderService, display_due, parse_due
from .voice_ui import VoicePanel
from .widgets import WidgetManager, TITLES

BG = "#0b1722"
PANEL = "#132634"
INK = "#e8f2f1"
MUTED = "#a7bcbc"
ACCENT = "#65dcff"


class Desktop:
    def __init__(self, root, core, voice_controller=None):
        self.root, self.core = root, core
        self.module = "general"
        self.reminders = ReminderService(core.store)
        self.timer = None
        self.reply_timer = None
        self.busy = False
        self.reply_queue = queue.Queue()
        self.voice_controller = voice_controller
        root.title("JARVIS AFNICA · Hey Jarvis")
        root.geometry("1240x860")
        root.minsize(980, 780)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK,
                        rowheight=32, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=BG, foreground=MUTED, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#31574f")])

        sidebar = tk.Frame(root, bg=PANEL, width=220, padx=18, pady=24)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.label(sidebar, "J / A", 26, ACCENT).pack(anchor="w")
        self.label(sidebar, "JARVIS AFNICA", 15).pack(anchor="w", pady=(10, 3))
        self.label(sidebar, "PERSONAL OPERATING SPACE", 8, MUTED).pack(anchor="w")
        self.label(sidebar, "MODULE", 9, MUTED).pack(anchor="w", pady=(35, 12))
        self.module_buttons = {}
        for key, module in MODULES.items():
            button = self.button(sidebar, module.label, lambda k=key: self.select_module(k))
            button.pack(fill="x", pady=4)
            self.module_buttons[key] = button
        self.button(sidebar, "Doar widgeturi ↗", lambda: self.widgets.desktop_mode()).pack(fill="x", pady=(20, 0))
        self.label(sidebar, "LOCAL FIRST", 10, ACCENT).pack(side="bottom", anchor="w", pady=(10, 0))
        self.label(sidebar, "Voce locală Windows\nTelegram: ulterior\nWeb / Google: neconectate", 9, MUTED).pack(side="bottom", anchor="w")

        main = tk.Frame(root, bg=BG, padx=24, pady=22)
        main.pack(side="left", expand=True, fill="both")
        header = tk.Frame(main, bg=BG)
        header.pack(fill="x")
        self.title = self.label(header, "Jarvis Core", 24)
        self.title.pack(side="left")
        self.label(header, "●  HEY JARVIS · v1.3", 10, ACCENT).pack(side="right")
        self.subtitle = self.label(main, "", 10, MUTED)
        self.subtitle.pack(anchor="w", pady=(5, 12))
        self.alert = self.label(main, "Remindere active cât timp aplicația este deschisă.", 10, ACCENT)
        self.alert.pack(anchor="w", pady=(0, 12))

        nav = tk.Frame(main, bg=BG)
        nav.pack(fill="x", pady=(0, 12))
        self.views = {}
        self.view_buttons = {}
        for key, title in (("chat", "Conversație"), ("tasks", "Task-uri"), ("memory", "Memorie"), ("connections", "Conexiuni"), ("widgets", "Widgeturi")):
            button = self.button(nav, title, lambda k=key: self.show(k))
            button.pack(side="left", padx=(0, 8))
            self.view_buttons[key] = button
        body = tk.Frame(main, bg=BG)
        body.pack(fill="both", expand=True)
        for key in self.view_buttons:
            self.views[key] = tk.Frame(body, bg=BG)
        self.build_chat(self.views["chat"])
        self.build_tasks(self.views["tasks"])
        self.build_memory(self.views["memory"])
        self.build_connections(self.views["connections"])
        self.build_widgets(self.views["widgets"])
        self.status = self.label(main, "SQLite local · fără chei API · fără trafic de rețea", 9, MUTED)
        self.status.pack(anchor="w", pady=(12, 0))
        self.widgets = WidgetManager(self)
        self.select_module("general")
        self.show("chat")
        self.poll()

    def label(self, parent, text, size=11, color=INK):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size), justify="left", anchor="w")

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=PANEL, fg=INK,
                         activebackground=ACCENT, activeforeground=BG,
                         font=("Segoe UI", 10), padx=12, pady=9, relief="flat", cursor="hand2")

    def entry(self, parent):
        return tk.Entry(parent, bg=PANEL, fg=INK, insertbackground=ACCENT,
                        font=("Segoe UI", 12), relief="flat")

    def tree(self, parent, columns):
        wrapper = tk.Frame(parent, bg=BG)
        wrapper.pack(expand=True, fill="both", pady=10)
        tree = ttk.Treeview(wrapper, columns=[key for key, _, _ in columns], show="headings", selectmode="browse")
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=50)
        scroll = ttk.Scrollbar(wrapper, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(expand=True, fill="both")
        return tree

    def build_chat(self, frame):
        self.voice = VoicePanel(frame, self.root, self.transcript, self.voice_controller,
                                on_wake=lambda: self.widgets.activate_from_wake())
        wrapper = tk.Frame(frame, bg=PANEL)
        wrapper.pack(expand=True, fill="both")
        self.chat = tk.Text(wrapper, bg=PANEL, fg=INK, wrap="word", relief="flat", padx=18, pady=16,
                            font=("Segoe UI", 11), spacing1=6, spacing3=12, state="disabled")
        scroll = ttk.Scrollbar(wrapper, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.chat.pack(expand=True, fill="both")
        self.chat.tag_configure("speaker", foreground=ACCENT, font=("Segoe UI", 9, "bold"))
        suggestions = tk.Frame(frame, bg=BG)
        suggestions.pack(fill="x", pady=12)
        for title, command in (("Ajutor", "ajutor"), ("Notele mele", "memorie"), ("Task-uri deschise", "task-uri")):
            self.button(suggestions, title, lambda c=command: self.send(c)).pack(side="left", padx=(0, 8))
        composer = tk.Frame(frame, bg=PANEL, padx=12, pady=8)
        composer.pack(fill="x")
        self.input = self.entry(composer)
        self.input.pack(side="left", fill="x", expand=True, ipady=8)
        self.input.bind("<Return>", lambda e: self.submit())
        self.button(composer, "Trimite →", self.submit).pack(side="right")
        self.label(frame, "Încearcă: Jarvis, ce am de făcut? · add task Check the filter · ține minte: o idee", 9, MUTED).pack(anchor="w", pady=(8, 0))

    def build_tasks(self, frame):
        bar = tk.Frame(frame, bg=BG)
        bar.pack(fill="x")
        self.button(bar, "+ Task", lambda: self.task_dialog(False)).pack(side="left", padx=(0, 8))
        self.button(bar, "+ Reminder", lambda: self.task_dialog(True)).pack(side="left")
        self.button(bar, "Marchează finalizat", self.complete_task).pack(side="right")
        self.tasks_tree = self.tree(frame, [("id", "ID", 50), ("title", "Task deschis", 340), ("due", "Termen local", 190)])
        self.task_hint = self.label(frame, "", 10, MUTED)
        self.task_hint.pack(anchor="w")

    def build_memory(self, frame):
        bar = tk.Frame(frame, bg=BG)
        bar.pack(fill="x")
        self.button(bar, "+ Notă", self.note_dialog).pack(side="left")
        self.button(bar, "Șterge nota selectată", self.delete_note).pack(side="right")
        self.memory_tree = self.tree(frame, [("id", "ID", 50), ("content", "Notă salvată", 520)])
        self.memory_tree.bind("<Double-1>", self.view_note)
        self.memory_tree.bind("<Return>", self.view_note)
        self.memory_hint = self.label(frame, "", 10, MUTED)
        self.memory_hint.pack(anchor="w")

    def build_connections(self, frame):
        self.label(frame, "Voce locală activabilă. Servicii externe neconectate.", 18).pack(anchor="w", pady=12)
        items = [
            ("Web search", "Placeholder cu interfață de provider. Nu sunt rezultate live."),
            ("Gmail", "Hook read-only. Necesită provider și autentificare OAuth."),
            ("Google Calendar", "Hook pentru citirea evenimentelor. OAuth nu este implementat."),
            ("Conversație AI", "Punct de extensie LanguageModel. Routerul local funcționează fără el."),
            ("Voice input / output", "Windows Speech: dictare la apăsare, transcriere de verificat și răspunsuri vocale."),
            ("Telegram", "Contract de ieșire. Botul și autentificarea utilizatorilor sunt viitoare."),
        ]
        for title, text in items:
            card = tk.Frame(frame, bg=PANEL, padx=16, pady=12)
            card.pack(fill="x", pady=5)
            self.label(card, title, 12, ACCENT).pack(anchor="w")
            self.label(card, text, 10, MUTED).pack(anchor="w", pady=(4, 0))

    def build_widgets(self, frame):
        self.label(frame, "Spațiul tău de comandă", 22, ACCENT).pack(anchor="w", pady=(8, 4))
        self.label(frame, "Ferestre independente pe desktop. Mută-le, fixează-le și revino oricând la JARVIS.", 10, MUTED).pack(anchor="w", pady=(0, 18))
        descriptions = {
            "command": "Microfon, Stop și comenzi rapide, fără fereastra mare.",
            "tasks": "Task-uri din toate modulele; marchează-le finalizate direct aici.",
            "reminders": "Lista termenelor, actualizată din datele locale.",
            "notes": "Notițele tale, cu filtru pe Fishroom, YouTube, jobs sau game.",
            "clock": "Ora și data PC-ului într-un panou compact.",
        }
        for kind, title in TITLES.items():
            card = tk.Frame(frame, bg=PANEL, padx=16, pady=12)
            card.pack(fill="x", pady=5)
            self.button(card, "Deschide ↗", lambda k=kind: self.widgets.open(k)).pack(side="right")
            self.label(card, title, 12, ACCENT).pack(anchor="w")
            self.label(card, descriptions[kind], 10, MUTED).pack(anchor="w", pady=(4, 0))
        self.button(frame, "Doar widgeturi · ascunde fereastra principală", lambda: self.widgets.desktop_mode()).pack(anchor="w", pady=12)

    def select_module(self, module):
        self.module = module
        self.title.configure(text=MODULES[module].label)
        self.subtitle.configure(text=MODULES[module].description)
        for key, button in self.module_buttons.items():
            button.configure(bg=ACCENT if key == module else PANEL, fg=BG if key == module else INK)
        self.refresh()

    def show(self, key):
        for name, frame in self.views.items():
            frame.pack_forget()
            self.view_buttons[name].configure(fg=ACCENT if name == key else INK)
        self.views[key].pack(fill="both", expand=True)
        if key == "chat":
            self.input.focus_set()

    def refresh(self):
        tasks = self.core.store.tasks(self.module)
        notes = self.core.store.memories(self.module)
        self.tasks_tree.delete(*self.tasks_tree.get_children())
        for task in tasks:
            self.tasks_tree.insert("", "end", iid=str(task["id"]), values=(task["id"], task["title"], display_due(task["due_at"])))
        self.task_hint.configure(text=f"{len(tasks)} task-uri deschise în acest modul. Task-urile finalizate rămân în baza de date.")
        self.memory_tree.delete(*self.memory_tree.get_children())
        for note in notes:
            self.memory_tree.insert("", "end", iid=str(note["id"]), values=(note["id"], note["content"]))
        self.memory_hint.configure(text=f"{len(notes)} note salvate. Dublu-clic sau Enter pentru textul integral.")
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", "JARVIS / LOCAL\n", "speaker")
        self.chat.insert("end", "At your service, sir. Local systems are ready.\nYou may write in Romanian; I shall reply in English. Enter 'help' to begin. Voice commands require review before submission.\n\n")
        # Global chronological history intentionally shows explicit module attribution.
        for item in self.core.store.history():
            who = "TU" if item["role"] == "user" else "JARVIS"
            self.chat.insert("end", f"{who} / {item['module'].upper()}\n", "speaker")
            self.chat.insert("end", item["content"] + "\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send(self, text):
        if self.busy or not text.strip():
            return False
        self.busy = True
        module = self.module
        self.status.configure(text="Thinking locally…")
        def work():
            try:
                self.reply_queue.put((self.core.handle(text, module), None))
            except Exception as error:
                self.reply_queue.put((None, error))
        threading.Thread(target=work, daemon=True).start()
        self.reply_timer = self.root.after(100, self.receive_reply)
        return True

    def receive_reply(self):
        try:
            reply, error = self.reply_queue.get_nowait()
        except queue.Empty:
            self.reply_timer = self.root.after(100, self.receive_reply)
            return
        self.reply_timer = None
        self.busy = False
        if error:
            messagebox.showerror("Operation failed", str(error), parent=self.root)
        else:
            self.select_module(reply.module)
            self.status.configure(text="Salvat local · " + datetime.now().strftime("%H:%M:%S"))
            self.voice.reply(reply.text)

    def submit(self):
        if self.send(self.input.get()):
            self.input.delete(0, "end")

    def transcript(self, text):
        if self.widgets.accept_transcript(text):
            return
        self.show("chat")
        # Preserve an existing draft rather than silently overwriting it.
        if self.input.get().strip():
            self.input.insert("end", " " + text)
        else:
            self.input.insert(0, text)
        self.input.focus_set()

    def dialog(self, title):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=BG, padx=22, pady=22)
        window.geometry("570x300")
        window.transient(self.root)
        window.grab_set()
        window.bind("<Escape>", lambda e: window.destroy())
        return window

    def task_dialog(self, reminder):
        dialog = self.dialog("Reminder nou" if reminder else "Task nou")
        self.label(dialog, "Titlu", 11).pack(anchor="w")
        title = self.entry(dialog)
        title.pack(fill="x", ipady=8, pady=8)
        title.focus_set()
        due = None
        if reminder:
            self.label(dialog, "Data și ora cu fus orar (format ISO)", 10, MUTED).pack(anchor="w")
            due = self.entry(dialog)
            due.pack(fill="x", ipady=8, pady=8)
            due.insert(0, (datetime.now().astimezone() + timedelta(hours=1)).isoformat(timespec="minutes"))

        def save():
            if not title.get().strip():
                messagebox.showerror("Titlu lipsă", "Completează titlul.", parent=dialog)
                return
            if due:
                try:
                    parse_due(due.get())
                except ValueError as error:
                    messagebox.showerror("Dată invalidă", str(error), parent=dialog)
                    return
            command = f"reminder: {due.get()} | {title.get()}" if due else f"task: {title.get()}"
            if self.send(command):
                dialog.destroy()
        self.button(dialog, "Salvează local", save).pack(anchor="e", pady=10)

    def note_dialog(self):
        dialog = self.dialog("Notă nouă")
        self.label(dialog, "Notă pentru " + MODULES[self.module].label).pack(anchor="w")
        content = tk.Text(dialog, bg=PANEL, fg=INK, insertbackground=ACCENT, font=("Segoe UI", 11), height=6, wrap="word")
        content.pack(fill="both", expand=True, pady=8)
        content.focus_set()

        def save():
            text = content.get("1.0", "end").strip()
            if not text:
                messagebox.showerror("Notă goală", "Scrie textul notei.", parent=dialog)
                return
            if self.send("memorează: " + text):
                dialog.destroy()
        self.button(dialog, "Salvează nota", save).pack(anchor="e")

    def view_note(self, event=None):
        selected = self.memory_tree.selection()
        if selected:
            note = next(n for n in self.core.store.memories(self.module) if str(n["id"]) == selected[0])
            messagebox.showinfo("Nota #" + selected[0], note["content"], parent=self.root)

    def complete_task(self):
        selected = self.tasks_tree.selection()
        if selected:
            self.send("gata: " + selected[0])
        else:
            messagebox.showinfo("Selectează un task", "Alege un rând din listă.", parent=self.root)

    def delete_note(self):
        selected = self.memory_tree.selection()
        if selected and messagebox.askyesno("Ștergere notă", "Ștergi definitiv această notă? Textul rămâne în istoricul chatului.", parent=self.root):
            self.send("uită: " + selected[0])

    def poll(self):
        try:
            fresh = self.reminders.poll()
            due = self.core.store.due()
            if due:
                self.alert.configure(text=f"● {len(due)} remindere scadente · primul: #{due[0]['id']} [{due[0]['module']}] {due[0]['title'][:55]}")
            else:
                self.alert.configure(text="Niciun reminder scadent · verificare la fiecare 5 secunde")
            if fresh:
                self.root.bell()
        except Exception:
            self.alert.configure(text="Nu pot verifica reminderele. Verifică accesul la baza locală.")
        self.timer = self.root.after(5000, self.poll)

    def close(self):
        if self.reply_timer:
            self.root.after_cancel(self.reply_timer)
        if hasattr(self.core.integrations.llm, "close"):
            self.core.integrations.llm.close()
        self.widgets.close()
        self.voice.close()
        if self.timer:
            self.root.after_cancel(self.timer)
        self.root.destroy()


def run(core):
    root = tk.Tk()
    Desktop(root, core)
    root.mainloop()
