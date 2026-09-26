# Arhitectură v1.3

## Activare vocală

`WakeGate` (`wake.py`) controlează un worker distinct pentru gramatica fixă Hey
Jarvis. Inițial dezactivat, este activat explicit pentru fiecare sesiune. Bucla
Tk a `VoicePanel` verifică eligibilitatea: fără redare, fără dictare și fără
transcriere în așteptare. O detecție cu încredere >=0,65 declanșează exclusiv
`WidgetManager.activate_from_wake`: afișarea widgetului și captură nouă, nu Core.

Detectarea și dictarea nu sunt active simultan. Stop invalidează evenimentele
întârziate și oprește ambele controllere. Reîncercarea după tăcere are o pauză
scurtă; după erori, detectarea se dezactivează. După suspendare se așteaptă 0,8s
pentru a reduce autoactivarea din ecoul sintezei. Ciclurile de proces au un timeout
de 25s. Nu este un serviciu Windows ori un detector continuu fără întreruperi.

Referință: [Microsoft GrammarBuilder](https://learn.microsoft.com/en-us/dotnet/api/system.speech.recognition.grammarbuilder?view=netframework-4.8.1).

## Widgeturi desktop

`widgets.py` conține `WidgetManager`, ferestrele `FloatingWidget`, selecția
datelor `widget_rows` și `WidgetPreferences`. Ferestrele Tk Toplevel nu sunt
transient ale ferestrei principale; astfel rămân vizibile când aceasta este
ascunsă. Managerul asigură o singură instanță per tip și revenirea la fereastra
principală după închiderea ultimului widget.

Datele provin din același Store/Core. Nu există duplicare a task-urilor sau
note salvate separat. `widgets.sqlite3`, lângă baza principală, conține numai
preferințe de poziție, fixare și vizibilitate. Conexiunile sunt închise explicit.
La ieșirea din aplicație se salvează widgeturile vizibile pentru restaurare;
închiderea individuală le marchează ascunse. Timer-ele sunt anulate la închidere.

Widgetul vocal reutilizează controllerul existent: nu creează un al doilea
microfon ori un al doilea proces de redare. Rezultatul dictării este introdus
în widget numai dacă acel widget a inițiat captura; trimiterea rămâne manuală.

## Extensia vocală

`voice_ui.py` este panoul desktop pentru audio și animație. `voice.py` rulează
operațiile într-un thread separat, prin proces PowerShell ascuns. Procesul
primește numai JSON prin stdin; scriptul fix `speech_bridge.ps1` nu include text
din chat interpolat ca sursă executabilă. SAPI sintetizează text literal (nu SSML),
iar System.Speech recunoaște o singură propoziție în limba motorului instalat.

Flux: apăsare Vorbește → microfon → transcriere → verificare manuală → Core →
chat + TTS. Răspunsurile lungi sunt limitate la 650 de caractere în audio;
conținutul complet rămâne în chat. Nu se vorbește peste o captură activă.

Thread-urile publică evenimente într-o coadă; numai thread-ul Tk modifică UI-ul.
La Stop, procesul activ este închis și răspunsurile întârziate sunt ignorate
prin ID-ul generației. La închiderea ferestrei se opresc timer-ele și procesele.
Nu există acces la rețea, înregistrare permanentă sau fișiere audio brute salvate.

## Structura

```text
JARVIS-AFNICA/
  Start-Jarvis.cmd         pornire Windows
  jarvis/
    __main__.py           composition root; selectează desktop sau CLI
    desktop.py            interfață Tk; nu conține logică de rutare
    core.py               validare, router de intenții, răspunsuri, istoric
    storage.py            repository SQLite; schema v1
    reminders.py          normalizare UTC și serviciu de reminder reutilizabil
    integrations.py       contracte provider + implementări dezactivate
    modules/
      base.py             contract modul
      fishroom.py         AFNICA Fishroom
      youtube.py          YouTube
      jobs.py             Job search
      game.py             AFNICA Game
      __init__.py         registru, inclusiv modulul general
  tests/                  teste cu stocare temporară
  docs/                   arhitectură, extensii, validare
  data/                   generat la prima pornire; exclus din surse
```

## Flux

```text
Desktop + voce / CLI / [adapter viitor: Telegram]
                       |
                  Core.handle
          validare + rutare pe modul
             /         |          \
        memorie      task-uri      integrări read-only
             \         |          (disabled implicit)
               Store / SQLite
                       |
                ReminderService
                       |
             banner + sunet desktop
```

V1 folosește un protocol restrâns de comenzi în locul unui LLM obligatoriu:
pornește offline și nu necesită conturi sau chei. Un model AI poate fi injectat
prin `Integrations.llm` pentru răspunsuri text. Răspunsurile modelului nu sunt
executate ca instrucțiuni. Arhitectura nu depinde de un framework de agenți.

## Responsabilități

- **Core**: identifică prefixul de modul, normalizează doar partea de comandă,
  păstrează conținutul original, validează înainte de mutații și produce `Reply`.
- **Modules**: module independente declarative, cu descriere și exemplu. În v1
  reutilizează operațiile note/task-uri; nu pretind automatizări de domeniu.
- **Store**: SQL parametrizat, tranzacție per operație, conexiuni scurte,
  schemă versionată cu `PRAGMA user_version`, WAL și indexuri după accesări.
- **Reminders**: task-uri deschise cu termen UTC <= momentul curent. Deduplicare
  a alertei pe sesiune; nu marchează task-ul ca rezolvat când este afișat.
- **Integrations**: separă serviciile externe de Core. Hook-urile Google sunt
  read-only; scrierea în conturi nu este disponibilă în MVP.
- **Desktop**: navigare, formulare, confirmare la ștergere, istoric comun cu
  eticheta modulului, polling periodic.

## Model de date

| Tabel | Câmpuri principale |
|---|---|
| memories | id, module, content, created_at |
| tasks | id, module, title, due_at UTC nullable, status open/done, created_at |
| messages | id, role, content, module, created_at |

ID-urile sunt globale pe tabel, nu pe modul. Comenzile `gata: ID` și `uită: ID`
pot acționa asupra acelui ID indiferent de modulul selectat. Desktopul permite
selecția doar dintre elementele modulului curent. Nu există utilizatori sau
control de acces între module: acestea reprezintă categorii, nu bariere de securitate.

Istoricul arată ultimele 100 de mesaje, în ordine cronologică, din toate modulele;
toate mesajele rămân în DB. Notele și task-urile nu sunt paginate încă.
Mutația și scrierea răspunsului în istoric sunt tranzacții separate: la oprire
bruscă poate exista o acțiune fără răspuns salvat. Înainte de retry după eroare,
verifică listele. Idempotency keys sunt necesare înainte de adaptoare cu retries.

## Limite de securitate și operare

- Fără server HTTP, porturi deschise sau acces implicit la conturi. Adapterul
  vocal execută exclusiv scriptul PowerShell fix, fără comenzi generate de utilizator.
- Fără chei, credențiale ori date private în codul distribuit.
- Conținutul rezultat din integrări este afișat ca date; nu este reintrodus în router.
- Local single-user; accesul la fișiere echivalează cu acces la toate datele.
- Pentru viitoare apeluri de rețea: worker separat de bucla UI, timeout, anulare,
  erori redactate și confirmare pentru mutații externe. V1 nu face astfel de apeluri.
- Schemele viitoare trebuie migrate înainte de utilizare, cu backup și teste.
  Versiunile de DB mai noi decât schema suportată sunt refuzate.

## Pași ulteriori sugerați, neimplementați

1. Clarificarea cerințelor specifice fiecărui domeniu și formulare dedicate.
2. Model AI opțional, cu buget, memorie selectată și preview al acțiunilor.
3. OAuth read-only Gmail/Calendar și provider real de căutare web.
4. Serviciu de reminder persistent cu outbox și idempotency.
5. Voce multilingvă mai naturală și Telegram cu allowlist, autentificare și audit.
