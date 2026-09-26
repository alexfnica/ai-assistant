# Ghid de extensie

## Modul nou

1. Adaugă un fișier în `jarvis/modules/` cu un obiect `Module`.
2. Înregistrează obiectul în `MODULES` din `jarvis/modules/__init__.py`.
3. Adaugă teste de izolare. Meniul desktop și prefixul `/id` îl vor recunoaște.
4. Pentru operații specifice (de exemplu măsurători acvariu), adaugă un serviciu
   în acel modul, validare și o migrare a schemei; nu încărca UI-ul cu SQL.

Exemplu declarativ:

```python
from .base import Module
MODULE = Module("studio", "Studio", "Note de producție", "task: Pregătește camera")
```

## Provider web sau Google

Contractele sunt în `jarvis/integrations.py`. Injectează un provider în
composition root (`jarvis/__main__.py`), fără modificarea Store sau Desktop:

```python
from jarvis.integrations import Integrations
from jarvis.core import Core

class MyWebProvider:
    def search(self, query: str) -> list[dict]:
        # Implementare reală: API, timeout, limită de rezultate și URL-uri sursă.
        raise NotImplementedError("Configurează providerul ales")

core = Core(store, Integrations(web=MyWebProvider()))
```

Comenzile `caută web: ...`, `gmail` și `calendar` apelează hook-urile aferente.
Calendar cere evenimente pentru următoarele 7 zile. Gmail cere lista importantă.
Contractele nu oferă trimitere de email sau creare de evenimente.

Înainte de activarea unei integrări reale:

- Alege furnizorul împreună cu utilizatorul și documentează ce date părăsesc PC-ul.
- Implementează OAuth cu cele mai restrânse scope-uri și revocare; nu cere parola contului.
- Stochează tokenurile în credential store-ul sistemului, nu în chat, Git sau SQLite.
- Mută apelurile de rețea într-un worker pentru a evita blocarea interfeței și pollingului.
- Adaugă timeout, retry limitat, redactare și teste pentru erori/rate limits.
- Dacă adaugi mutații, cere confirmare explicită pentru conținut și destinație.
- Datele de pe web/email sunt neîncredere: nu executa instrucțiuni din ele.

## Model lingvistic

`LanguageModel.reply(text, module)` este un hook pentru conversație liberă.
Nu este activ implicit și nu primește automat întreaga memorie. Înainte de
conectare implementează alegerea furnizorului, limite de cost, istoricul relevant,
consimțământ pentru transmiterea datelor și tratarea sigură a răspunsurilor.
Nu parsa automat răspunsurile LLM ca mesaje noi pentru `Core.handle`.

## Voce (implementare locală în v1.1)

Adapterul real desktop este în `voice.py`, `speech_bridge.ps1` și `voice_ui.py`.
Folosește SAPI pentru redare și System.Speech pentru dictare. Contractele generice
de mai jos rămân puncte de extensie pentru un motor alternativ, nu sunt adapterul
folosit acum. Orice motor cloud viitor trebuie să facă explicit costul și ce audio
se transmite înainte de activare.

`VoiceInput.transcribe(audio)` → text → confirmare în UI → `Core.handle`.
`Reply.text` → `VoiceOutput.synthesize(text)` → redare audio.
În v1.3, pe lângă dictarea la apăsare există detectarea opțională Hey Jarvis în
`wake.py`. Este o gramatică Windows Speech fixă; un motor wake-word dedicat poate
înlocui controllerul păstrând suspendarea în timpul TTS și controlul de oprire.
Păstrează vizibil starea microfonului și permite anularea înainte de acțiuni.

## Telegram

Un viitor adapter primește mesaje numai de la chat/user IDs autorizați și
apelează `Core.handle`. Trimite răspunsul prin `OutboundChannel.send`.
Contractul de ieșire este disponibil, botul/transportul nu sunt implementate.

Înainte de expunere: validează identitatea, deduplică update IDs, persistă un
outbox pentru retry, separă datele utilizatorilor și nu expune această bază
single-user direct pe internet. Pentru remindere fără desktop trebuie un
scheduler separat; `ReminderService` actual deduplică numai în memorie.
