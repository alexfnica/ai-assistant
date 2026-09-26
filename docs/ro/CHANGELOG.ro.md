# JARVIS AFNICA — local conversational edition

## Conversational AI

Normal startup now enables **Qwen2.5-1.5B-Instruct Q4_K_M**, running locally through
llama.cpp on the CPU. No API key, subscription or internet connection is required
after installation. Daniel remains the local voice. See [setup and limits](CONVERSATIONAL-AI.md).

## J.A.R.V.I.S. personality

The application now loads `personality/JARVIS.md`: composed, formal, concise,
British-style phrasing, addressing the user as sir. Built-in command replies are
English even for Romanian input; original notes and task titles are preserved.
Daniel remains the default local voice. Enter `personality` or `personalitate`
to check the active mode. Restart the application after changing the profile.

The profile is passed as `system_prompt` to the local conversational adapter.
Explicit commands still use the deterministic router; other questions go to the model.
The profile does not enable account access or self-modification.
Some interface labels and older chat history remain Romanian.
66 automated tests pass, including bilingual commands, prompt forwarding and
verification that generated model text cannot execute data-changing commands.

## Actualizare: Natural British (Kokoro)

Pe acest PC, vocea implicită este acum **Natural British Daniel**. În selector apar
și **Natural British George** / **Natural British Blend**. Sunt generate complet
local, fără ecou, modulație sau pauzele artificiale din profilul Piper anterior.
Vezi [ghidul Kokoro](VOCE-NATURALA.md). Vocile vechi rămân opțiuni alternative.

## Voce nouă: British Calm / HUD

Pachetul de pe acest PC include acum o voce AI masculină britanică locală, aleasă
ca alternativă. În Setări voce / Voce și limbă poți alege British Calm sau
British HUD (efect electronic discret). Vezi [detalii și analiza audio](VOCE-AFNICA.md).
Necesită Python 3.12 pe Windows x64 pentru runtime-ul inclus. Nu este vocea actorului.

## Nou: interfața holografică

Pornește **Start-Jarvis-HOLO.cmd** din folderul complet. Se deschide în browser
la http://127.0.0.1:4891. Păstrează fereastra serverului deschisă; Ctrl+C îl oprește.
Pe acest PC există și scurtătura `Porneste-JARVIS-HOLO-pe-acest-PC.cmd`, lângă proiect.
Nu muta fișierele individual și nu porni din arhiva ZIP.

Vezi [ghidul HOLO](HOLO-GHID.md) pentru gesturi, voce, limite și verificări.
Varianta desktop cu widgeturi separate rămâne disponibilă prin **Start-Jarvis.cmd**.

## Varianta desktop: Hey Jarvis

## Activare vocală a widgetului

1. Pornește aplicația. În Conversație bifează **Activează „Hey, Jarvis”**, sau
   folosește butonul echivalent din widgetul Comandă. Este dezactivat la fiecare
   pornire până îl activezi tu explicit.
2. Când apare **HEY JARVIS · MICROFON ÎN AȘTEPTARE**, spune **Hey, Jarvis**.
3. Widgetul Comandă se deschide sau revine în față. Așteaptă indicatorul
   **ASCULT**, apoi spune o propoziție în limba recunoașterii (en-US pe PC-ul verificat).
4. Verifică transcrierea și apasă **Trimite**. Comenzile care modifică date nu
   sunt executate doar pentru că s-a auzit o voce.
5. Folosește butoanele rapide din widget pentru Task-uri, Notițe și Remindere.

Poți ascunde fereastra principală cu **Doar widgeturi** sau minimiza widgetul;
detectarea continuă cât timp aplicația rulează și revine la widget la activare.
**Stop** oprește atât dictarea/redarea, cât și detectarea Hey Jarvis. Debifarea
Hey Jarvis oprește numai detectarea expresiei; pentru oprirea tuturor operațiilor
audio folosește Stop. La închiderea aplicației se oprește microfonul.

### Confidențialitate și limite

- Cât timp este activat, microfonul este folosit local pentru detectarea expresiei.
  Nu se salvează înregistrări și nu se trimite audio la servicii cloud.
- Detectarea se suspendă cât timp Jarvis vorbește, dictezi sau ai o transcriere
  de verificat. Dacă există deja un mesaj netrimis în widget, acesta este păstrat
  și o nouă captură nu pornește peste el.
- Este un detector bazat pe gramatica Windows Speech, nu un motor wake-word
  dedicat: pot exista activări false, ratări și scurte pauze între cicluri.
  Pragul de încredere este 0,65. Nu garantează funcționarea în zgomot sau peste TV.
- Nu spune expresia și comanda într-o singură propoziție: așteaptă starea ASCULT.
- Detectarea Hey Jarvis necesită recunoaștere Windows în engleză. Comanda
  ulterioară folosește limba selectată la Setări voce.
- JARVIS trebuie să fie pornit și PC-ul activ. Nu pornește prin voce dintr-o
  stare complet închisă, nu funcționează în repaus și nu se instalează în startup.
- Logica a fost testată automat, dar detectarea pe microfon real și ferestrele
  nu au fost verificate end-to-end în mediul restricționat al agentului.

### Corecție de pornire v1.2.1

Dezarhivează **întregul ZIP** înainte de lansare. În același folder trebuie să
existe `Start-Jarvis.cmd`, `run_jarvis.py` și subfolderul `jarvis`. Nu deschide
launcherul direct din arhivă și nu-l muta separat pe Desktop; poți crea o
scurtătură către el. Noul launcher folosește o cale absolută și configurează
explicit importul aplicației, inclusiv pentru Python izolat. Dacă lipsesc
fișiere, afișează instrucțiuni în loc de `No module named jarvis`.

La actualizare închide JARVIS, înlocuiește fișierele programului și păstrează
folderul `data` existent. Arhiva nu conține și nu înlocuiește datele tale.

## Nou: widgeturi pe desktop

Pornește **Start-Jarvis.cmd → Widgeturi** și apasă **Deschide** lângă panoul dorit:

- **Comandă**: control vocal, Stop, câmp de comandă și ultimul răspuns scurt.
- **Task-uri**: task-uri deschise, filtru pe modul și finalizare direct din widget.
- **Remindere**: toate task-urile cu termen, inclusiv restantele, în ordine cronologică.
- **Notițe**: notele salvate, cu filtru pe modul și detalii la dublu-clic.
- **Ceas**: ora și data PC-ului.

Sunt ferestre independente, nu carduri în interiorul aplicației. Mută-le din
bara de titlu Windows sau din titlul cyan JARVIS. Bifează **Deasupra** pentru
a le păstra peste celelalte ferestre; debifează pentru comportament normal.
Datele se actualizează la fiecare secundă din aceeași bază locală.

**Doar widgeturi** ascunde fereastra mare, fără oprirea JARVIS. Dacă nu există
widgeturi deschise, deschide Comandă și Task-uri. Butonul **Deschide JARVIS**
din orice widget readuce fereastra principală. Dacă închizi ultimul widget
cât timp fereastra mare e ascunsă, aceasta reapare automat.

Pozițiile, starea „Deasupra” și widgeturile deschise se păstrează între porniri
în `data/widgets.sqlite3`; baza cu notele și task-urile nu se schimbă. La
restaurare, pozițiile sunt aduse în limitele monitorului principal pentru a
evita pierderea ferestrelor după deconectarea unui monitor. Dimensiunile și
filtrele nu se păstrează încă. Închiderea unui widget nu șterge datele.

Widgetul Comandă folosește modulul selectat în aplicația principală sau prefixul
explicit `/fishroom`, `/youtube`, `/jobs`, `/game`. Transcrierea se verifică și
se trimite manual din widget. Butonul **+ Adaugă** din panourile de date deschide
formularul corespunzător în aplicația principală.

Widgeturile funcționează cât timp aplicația rulează; nu pornesc automat cu
Windows și nu sunt integrate în panoul nativ Windows Widgets. Pentru ieșire
completă: **Deschide JARVIS**, apoi închide fereastra principală.

**Testare v1.2:** 30 de teste de logică; verificarea vizuală a ferestrelor rămâne
de făcut pe desktop, deoarece inițializarea Tk este blocată în mediul agentului.

## Nou: interacțiune vocală

Interfață cu panou vocal animat, **Vorbește**, **Stop**, **Repetă** și **Setări
voce**. Răspunsurile pot fi rostite folosind vocile Windows disponibile, fără
API sau abonament. Viteza și volumul sunt reglabile. Vocea preferată este masculină
britanică dacă există; altfel se alege o voce masculină disponibilă. Nu se clonează
vocea actorului și vocile Windows standard nu au calitatea cinematografică.

Pe acest PC au fost detectate **David / Zira (en-US)** și recunoaștere **en-US**.
Nu a fost detectată o voce britanică sau română. Detectorul listează doar vocile
compatibile cu SAPI, nu toate vocile disponibile în alte aplicații Windows.

1. Pornește `Start-Jarvis.cmd`, apoi deschide **Setări voce → Test voce**.
2. Apasă **Vorbește**, spune în engleză „Show my tasks” sau „Add task Check the
   filter”. Microfonul folosește dispozitivul implicit Windows.
3. Textul recunoscut apare în câmpul mesajului. Verifică-l și apasă **Trimite**.
   Nu se execută automat o comandă auzită.
4. **Stop** anulează ascultarea sau răspunsul audio. Debifează **Răspunsuri
   vocale** pentru modul silențios. **Repetă** citește ultimul răspuns dacă vocea
   este activată.

Cu Hey Jarvis dezactivat, microfonul pornește numai la apăsare. Dictarea are o
limită de 25 secunde; lipsa vorbirii închide sesiunea mai devreme. Nu se salvează
audio brut. Numai transcrierea trimisă manual intră în istoricul obișnuit.
Animația reprezintă starea aplicației, nu amplitudinea reală a vocii.
Setările vocale sunt păstrate numai în sesiunea curentă.

Poți scrie și „Jarvis, ce am de făcut?”, „Ține minte: o idee” sau „Adaugă un
task Verifică filtrul”. Acestea sunt expresii suportate explicit, nu conversație
liberă cu un LLM. Răspunsurile rămân în română; o voce engleză le poate pronunța
nefiresc. Pentru română vocală naturală și dialog flexibil este necesar un
motor multilingv plus un model conversațional, încă neconectate.

**Verificare:** 23 teste de logică trecute; inventarul vocal real funcționează.
Sinteza audio și noua fereastră nu au putut fi validate complet în sandbox
(eroare audio Windows și inițializare Tk restricționată). Folosește Test voce
pentru verificarea efectivă pe desktop. Nu este declarată o validare end-to-end.

## Baza aplicației

Asistent personal modular, local, în română. MVP desktop cu chat de comenzi,
memorie persistentă, task-uri și remindere. Nu necesită abonament, chei API
sau conexiune la internet pentru funcțiile locale.

## Pornire pe Windows

1. Păstrează întregul folder `JARVIS-AFNICA`, nu doar launcherul.
2. Dublu-clic pe **Start-Jarvis.cmd**.
3. Selectează un modul și scrie **ajutor**, sau folosește butoanele **+ Notă**,
   **+ Task** și **+ Reminder**.

Launcherul încearcă mai întâi runtime-ul inclus cu Codex pe acest PC, apoi
instalările Python disponibile. Verifică executarea efectivă, versiunea și
modulul Tk; scurtătura Windows către Microsoft Store nu este acceptată ca Python.
Pe un alt PC ai nevoie de **Python 3.11+ cu Tcl/Tk**. Aplicația folosește exclusiv
biblioteca standard Python; nu este necesar `pip install`.

Alternativ, deschide un terminal în folderul proiectului:

```powershell
py -3 -m jarvis
```

Linux/macOS cu Python și Tk disponibile: `python3 -m jarvis`.
La eroarea `No module named tkinter`, instalează suportul Tk pentru distribuția
Python folosită. MVP-ul nu este împachetat într-un executabil `.exe`.

## Ce funcționează

| Componentă | V1 local |
|---|---|
| Chat | Comenzi explicite, istoric persistent, context de modul |
| Jarvis Core | Router în română, acceptă diacritice sau text fără diacritice |
| Memorie | Creare, listare, ștergere; separare pe module |
| Task-uri | Creare, listare deschise, finalizare; păstrează cele finalizate în DB |
| Remindere | Termene cu fus orar, banner și sunet de sistem la scadență |
| Fishroom | Jurnal de observații și întreținere; note și task-uri locale |
| YouTube | Idei, note și task-uri de producție |
| Job search | Preferințe și jurnal de candidaturi; fără joburi live |
| AFNICA Game | Backlog și note manuale de build |
| Web/Gmail/Calendar | Contracte și hooks apelabile, implementări dezactivate implicit |
| Voce | Adapter Windows SAPI/System.Speech, selecție și control audio; vezi limitele de mai sus |
| Model AI / Telegram | Contracte pentru extensii; nu sunt implementări active |

Chatul este un **router determinist**, nu un model lingvistic. Nu înțelege liber
orice întrebare, nu execută cod, nu citește repo-uri, nu trimite emailuri și nu
publică pe YouTube. Notele salvate nu sunt încă o memorie semantică/vectorială.

## Primii pași

În modulul Fishroom:

```text
memorează: Acvariul A — schimb de apă efectuat
task: Verifică filtrul acvariului A
memorie
task-uri
gata: 1
```

ID-urile sunt atribuite automat; înlocuiește `1` cu ID-ul task-ului real.
Poți ruta fără să schimbi modulul din meniu:

```text
/youtube memorează: Idee video — turul fishroom-ului
/jobs task: Actualizează CV-ul
/game memorează: Următorul build trebuie să testeze salvarea
memorie toate
task-uri toate
```

Pentru reminder este recomandat formularul **Task-uri → + Reminder**. Exemplu
de comandă (înlocuiește data cu una potrivită):

```text
/fishroom reminder: 2026-09-03T10:00+03:00 | Schimb de apă
```

V1 cere o dată ISO cu offset explicit. În România `+03:00` corespunde orei de
vară, `+02:00` orei de iarnă. Formularul propune ora de peste o oră cu offsetul
actual al PC-ului. Dacă alegi o dată din alt sezon, verifică și offsetul.
Stocarea este în UTC; afișarea folosește fusul orar al sistemului.

### Limitele reminderelor

- Verificare la fiecare 5 secunde cât timp aplicația desktop rulează.
- Banner persistent cu numărul total scadent și primul task; listele detaliate
  sunt accesibile din fiecare modul sau prin `task-uri toate`.
- Un sunet de sistem pentru un reminder nou detectat, o dată pe sesiune
  (sunetul poate fi dezactivat de sistemul de operare).
- Dacă PC-ul este închis sau în repaus, **nu se trimit notificări**. Task-urile
  restante sunt detectate la repornirea aplicației sau revenirea din repaus.
- Nu există serviciu de fundal, notificări push, repetiții sau snooze în v1.
- Un reminder trecut este acceptat și devine imediat scadent.

## Date, confidențialitate și backup

Baza implicită: `data/jarvis.sqlite3`, lângă codul proiectului. Datele supraviețuiesc
închiderii, repornirii și actualizării codului dacă păstrezi folderul `data`.
Poți alege un alt director:

```powershell
py -3 -m jarvis --data-dir "D:\JarvisData"
```

Pentru backup, **închide toate instanțele JARVIS**, apoi copiază întregul folder
`data` într-un loc sigur. Pentru restaurare, cu aplicația închisă, păstrează
mai întâi o copie a datelor curente, apoi restaurează folderul din backup.
Nu copia doar fișierul `.sqlite3` în timpul funcționării: SQLite poate utiliza
și fișierele auxiliare `-wal` și `-shm`.

Datele nu sunt criptate și aplicația nu are autentificare: este un MVP pentru
un singur utilizator local. Oricine are acces la fișiere poate citi datele.
Nu salva parole sau tokenuri în chat. **Ștergerea unei note nu șterge textul
din istoricul conversației**. Pentru eliminarea tuturor datelor, închide aplicația
și elimină directorul de date ales, numai după verificarea țintei și backup dacă
este necesar. Nu există încă ștergere selectivă din istoricul chatului.

## Mod terminal

```powershell
py -3 -m jarvis --cli
```

`exit` închide sesiunea. Folosește aceeași bază de date ca desktopul, dar nu
are alerte automate; termenele pot fi consultate prin `task-uri toate`.

## Testare

Din directorul proiectului:

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q jarvis tests
```

Testele folosesc baze temporare și nu modifică datele personale. Testul desktop
explicit de mai jos necesită un mediu cu interfață grafică și Tk:

```powershell
py -3 -m unittest tests.desktop_smoke -v
```

Detaliile arhitecturii și extensiilor sunt în **docs/ARCHITECTURE.md** și
**docs/EXTENDING.md**. Rezultatul verificării livrării este în **docs/VALIDATION.md**.
