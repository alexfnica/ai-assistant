"""Interactive voice console; mounted into the native desktop chat view."""
import math
import tkinter as tk
from tkinter import ttk
from .voice import VoiceController, preferred_voice
from .wake import WakeGate

BG = "#0b1722"
PANEL = "#132634"
CYAN = "#65dcff"
MUTED = "#aac4d2"


class VoicePanel:
    def __init__(self, parent, root, on_transcript, controller=None, on_wake=None):
        self.root = root
        self.on_transcript = on_transcript
        self.controller = controller or VoiceController()
        self.on_wake = on_wake
        self.wake = WakeGate()
        self.voices, self.recognizers = [], []
        self.state = "ready"
        self.phase = 0
        self.timer = None
        self.last_reply = ""
        self.frame = tk.Frame(parent, bg=PANEL, padx=12, pady=8)
        self.frame.pack(fill="x", pady=(0, 10))
        self.canvas = tk.Canvas(self.frame, width=112, height=112, bg=PANEL, highlightthickness=0)
        self.canvas.pack(side="left", padx=(0, 14))
        self.canvas.create_oval(9, 9, 103, 103, outline="#254b60", width=2)
        self.arc = self.canvas.create_arc(17, 17, 95, 95, start=0, extent=260, style="arc", outline=CYAN, width=3)
        self.pulse = self.canvas.create_oval(28, 28, 84, 84, outline=CYAN, width=1)
        self.canvas.create_text(56, 52, text="J / A", fill=CYAN, font=("Segoe UI", 15, "bold"))
        self.canvas.create_text(56, 70, text="VOICE", fill=MUTED, font=("Segoe UI", 7))
        controls = tk.Frame(self.frame, bg=PANEL)
        controls.pack(side="left", fill="both", expand=True)
        self.title = tk.Label(controls, text="VOICE LINK · INIȚIALIZARE", bg=PANEL, fg=CYAN,
                              font=("Segoe UI", 11, "bold"), anchor="w")
        self.title.pack(fill="x")
        self.detail = tk.Label(controls, text="Verific vocile locale. Microfonul este oprit.", bg=PANEL, fg=MUTED,
                               font=("Segoe UI", 9), anchor="w", justify="left", wraplength=590)
        self.detail.pack(fill="x", pady=(3, 7))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x")
        self.mic = self.button(row, "● Vorbește", self.listen)
        self.mic.pack(side="left", padx=(0, 6))
        self.button(row, "■ Stop", self.stop).pack(side="left", padx=(0, 6))
        self.button(row, "Setări voce", self.settings).pack(side="left", padx=(0, 6))
        self.button(row, "Repetă", lambda: self.speak(self.last_reply)).pack(side="left")
        self.enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(controls, text="Răspunsuri vocale", variable=self.enabled, command=self.toggle,
                       bg=PANEL, fg=MUTED, selectcolor=BG, activebackground=PANEL,
                       activeforeground=CYAN, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        self.wake_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(controls, text='Activează „Hey, Jarvis” · microfon în așteptare',
                       variable=self.wake_enabled, command=self.wake_toggle,
                       bg=PANEL, fg=CYAN, selectcolor=BG, activebackground=PANEL,
                       activeforeground=CYAN, font=("Segoe UI", 9)).pack(anchor="w")
        self.voice_id = ""
        self.recognizer_id = ""
        self.rate = tk.IntVar(value=-1)
        self.volume = tk.IntVar(value=85)
        self.reload()
        self.tick()

    def button(self, parent, label, command):
        return tk.Button(parent, text=label, command=command, bg="#203c4e", fg=CYAN, relief="flat",
                         activebackground=CYAN, activeforeground=BG, padx=9, pady=6, cursor="hand2")

    def set_state(self, state, detail):
        self.state = state
        titles = {"ready": "PREGĂTIT", "loading": "VERIFICARE", "speaking": "VORBESC",
                  "listening": "ASCULT", "review": "VERIFICĂ TRANSCRIEREA", "error": "ATENȚIE",
                  "armed": "HEY JARVIS · MICROFON ÎN AȘTEPTARE"}
        self.title.configure(text="VOICE LINK · " + titles[state])
        self.detail.configure(text=detail)

    def reload(self):
        self.wake.pause()
        self.set_state("loading", "Detectez vocile și limbile de recunoaștere. Microfon oprit.")
        self.mic.configure(state="disabled")
        self.controller.start("inventory")

    def listen(self):
        self.wake.pause()
        if not self.recognizer_id:
            self.set_state("error", "Nu există recunoaștere vocală compatibilă. Chatul text funcționează.")
            return
        culture = next((r["culture"] for r in self.recognizers if r["id"] == self.recognizer_id), "")
        self.set_state("listening", f"Microfon activ · {culture} · spune o propoziție. Stop anulează. Maximum 25 secunde.")
        self.controller.start("listen", recognizer=self.recognizer_id)

    def speak(self, text, sample=False):
        if not text or (not sample and not self.enabled.get()):
            return
        if not self.voice_id:
            self.set_state("error", "Nu este disponibilă o voce. Deschide Setări voce → Reîncarcă.")
            return
        # Never speak over an active microphone recording.
        if self.state == "listening":
            return
        self.wake.pause()
        self.set_state("speaking", "Răspuns audio local · Stop întrerupe imediat. Microfon oprit.")
        spoken = text[:650] + (". Restul răspunsului este în chat." if len(text) > 650 else "")
        self.controller.start("speak", text=spoken, voice=self.voice_id, rate=self.rate.get(), volume=self.volume.get())

    def reply(self, text):
        self.last_reply = text
        if self.state == "review":
            self.set_state("ready", "Comandă procesată.")
        self.speak(text)

    def stop(self):
        self.wake_enabled.set(False)
        self.wake.disable()
        self.controller.stop()
        self.set_state("ready", "Audio oprit. Microfonul este închis.")

    def wake_toggle(self):
        if self.wake_enabled.get():
            if not self.wake.enable(self.recognizers):
                self.wake_enabled.set(False)
                self.set_state("error", self.wake.error)
            elif self.state not in ("listening", "speaking", "review", "loading"):
                self.set_state("ready", "Ascultare locală activată. Spune Hey Jarvis, apoi așteaptă starea ASCULT.")
        else:
            self.wake.disable()
            if self.state == "armed":
                self.set_state("ready", "Activarea vocală este oprită. Microfon închis.")

    def toggle_wake_button(self):
        self.wake_enabled.set(not self.wake_enabled.get())
        self.wake_toggle()

    def toggle(self):
        if not self.enabled.get() and self.state == "speaking":
            self.stop()

    def tick(self):
        for action, result, error in self.controller.drain():
            if error:
                self.set_state("error", "Audio indisponibil: " + error[:170])
            elif action == "inventory":
                self.voices = result.get("voices") or []
                self.recognizers = result.get("recognizers") or []
                voice = preferred_voice(self.voices)
                self.voice_id = voice["id"] if voice else ""
                recognizer = next((r for r in self.recognizers if r["culture"] == "ro-RO"),
                                  self.recognizers[0] if self.recognizers else None)
                self.recognizer_id = recognizer["id"] if recognizer else ""
                self.mic.configure(state="normal" if recognizer else "disabled")
                description = f"Voce: {voice['name'] if voice else 'indisponibilă'} · microfon: {recognizer['culture'] if recognizer else 'indisponibil'}"
                self.set_state("ready", description)
            elif action == "listen":
                text = result.get("text", "").strip()
                if text:
                    self.on_transcript(text)
                    self.set_state("review", "Microfon oprit. Textul este în câmpul mesajului; verifică-l și apasă Trimite.")
                else:
                    self.set_state("ready", "Nu am recunoscut o propoziție. Verifică limba și microfonul, apoi încearcă din nou.")
            else:
                self.set_state("ready", "La dispoziția ta. Apasă Vorbește pentru următoarea comandă.")
        available = not self.controller.busy and self.state in ("ready", "armed")
        if self.wake.tick(available):
            self.set_state("ready", "Hey Jarvis detectat. Deschid widgetul de comandă.")
            if self.on_wake:
                self.on_wake()
            else:
                self.listen()
        if self.wake_enabled.get() and not self.wake.enabled:
            self.wake_enabled.set(False)
            self.set_state("error", self.wake.error or "Ascultarea vocală s-a oprit.")
        if self.wake.enabled and self.state in ("ready", "armed"):
            self.set_state("armed", "Microfon local în așteptare: Hey Jarvis. Stop închide complet ascultarea.")
        self.phase += 0.12
        active = self.state in ("listening", "speaking", "loading", "armed")
        self.canvas.itemconfigure(self.arc, start=(self.phase * 40) % 360 if active else 90)
        radius = 28 + (3 * math.sin(self.phase * 2) if active else 0)
        self.canvas.coords(self.pulse, 56-radius, 56-radius, 56+radius, 56+radius)
        self.timer = self.root.after(90, self.tick)

    def settings(self):
        window = tk.Toplevel(self.root)
        window.title("JARVIS · Setări voce")
        window.geometry("640x470")
        window.configure(bg=PANEL, padx=22, pady=18)
        window.transient(self.root)
        def label(text):
            tk.Label(window, text=text, bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=580).pack(fill="x", pady=7)
        label("Voce locală — stil calm, viteză ușor redusă. Nu este vocea actorului din film.")
        selector = ttk.Combobox(window, state="readonly", values=[v["name"] for v in self.voices])
        selector.pack(fill="x")
        if self.voices:
            selector.current(next((i for i,v in enumerate(self.voices) if v["id"] == self.voice_id), 0))
        def select_voice(event=None):
            if selector.current() >= 0:
                self.voice_id = self.voices[selector.current()]["id"]
        selector.bind("<<ComboboxSelected>>", select_voice)
        label("Limba recunoașterii — vorbește în limba selectată")
        recognition = ttk.Combobox(window, state="readonly", values=[r["culture"] for r in self.recognizers])
        recognition.pack(fill="x")
        if self.recognizers:
            recognition.current(next((i for i,r in enumerate(self.recognizers) if r["id"] == self.recognizer_id), 0))
        def select_recognizer(event=None):
            if recognition.current() >= 0:
                self.recognizer_id = self.recognizers[recognition.current()]["id"]
        recognition.bind("<<ComboboxSelected>>", select_recognizer)
        label("Viteză (−4 lent / +4 rapid)")
        tk.Scale(window, from_=-4, to=4, orient="horizontal", variable=self.rate, bg=PANEL, fg=CYAN,
                 highlightthickness=0).pack(fill="x")
        label("Volum")
        tk.Scale(window, from_=0, to=100, orient="horizontal", variable=self.volume, bg=PANEL, fg=CYAN,
                 highlightthickness=0).pack(fill="x")
        row = tk.Frame(window, bg=PANEL)
        row.pack(fill="x", pady=10)
        self.button(row, "Test voce", lambda: self.speak("Good evening. Jarvis AFNICA online. Systems ready. How may I assist you?", sample=True)).pack(side="left")
        def reload():
            window.destroy()
            self.reload()
        self.button(row, "Reîncarcă vocile", reload).pack(side="left", padx=8)
        label("Natural British: Kokoro local. Calm / HUD: Piper anterior. Nu sunt clone. Vocile engleze nu oferă pronunție română naturală. Setările sunt valabile pentru sesiunea curentă.")

    def close(self):
        self.wake.disable()
        if self.timer:
            self.root.after_cancel(self.timer)
        self.controller.stop()
