# Verificarea livrării

## Hey Jarvis v1.3

- **42/42 teste trecute**: inclusiv opt-in, gramatica acceptată și pragul de
  încredere, lipsa motorului în engleză, pauza la dictare/TTS, rearmare după
  tăcere, erori, anulare, afișarea widgetului și păstrarea mesajului netrimis.
- Sintaxa scriptului Windows Speech validată cu parserul PowerShell, fără
  accesarea microfonului. Compilarea Python verificată separat.
- Nu s-a testat recunoașterea cu o voce reală, rata de activări false, revenirea
  ferestrei minimizate sau arbitrarea fizică a microfonului. Testele sunt de
  logică și nu reprezintă validare audio/desktop end-to-end.

Acceptanță: activează Hey Jarvis, minimizează widgetul Comandă, spune expresia,
așteaptă ASCULT, spune „show my tasks”, verifică textul și trimite. Verifică Stop,
dezactivarea indicatorului, lipsa activării în timpul redării și închiderea
microfonului după închiderea aplicației. În caz de eroare copiază mesajul exact.

## Corecție launcher v1.2.1

- 32/32 teste de logică trecute, inclusiv pornire din alt director cu Python
  izolat (`-I`) și diagnostic pentru pachet incomplet.
- Launcherul CMD verificat din afara folderului aplicației cu `--help`:
  cod de ieșire 0, fără eroarea de import `jarvis`.
- Acest test validează găsirea și importul proiectului, nu redarea audio sau
  afișarea ferestrelor. Limitele verificării grafice rămân cele de mai jos.

## Actualizare Desktop Widgets v1.2

- 30 teste de logică: suita anterioară plus stocarea pozițiilor, actualizarea
  preferințelor, recuperarea pozițiilor în afara ecranului, filtrele pe modul,
  sursa comună a datelor și transcrierea către widget fără executare automată.
- Testele au identificat conexiuni SQLite rămase deschise în preferințe;
  închiderea explicită a fost adăugată înainte de livrare.
- Testul desktop explicit a fost extins pentru toate cele cinci widgeturi,
  deschidere fără duplicate, ascunderea aplicației și revenire după ultimul
  widget închis. Nu este declarat trecut pentru v1.2: mediul curent are blocajul
  Tk documentat la v1.1, fără posibilitatea aprobării rulării în afara sandboxului.
- Nu a fost făcută verificarea vizuală a pozițiilor, ferestrelor deasupra altor
  aplicații sau a comportamentului pe mai multe monitoare.

Acceptanță manuală: deschide fiecare widget din secțiunea Widgeturi; mută-l;
comută Deasupra; creează un task, verifică actualizarea și finalizează-l din
widget. Testează Doar widgeturi → închide ultimul widget → revenire la JARVIS.
Închide aplicația cu widgeturi active și redeschide pentru verificarea restaurării.

## Actualizare Voice Edition v1.1

- **23/23 teste unitare trecute**, inclusiv selecția vocii, comenzi mai naturale,
  lucrul asincron, anularea și ignorarea evenimentelor vechi, erorile de worker.
- Inventarul real prin adapter detectează David și Zira (en-US), plus motorul
  de recunoaștere MS-1033-80-DESK (en-US).
- Testul de sinteză într-un fișier WAV a eșuat cu HRESULT 0x80045040 în sandbox.
  Nu se livrează un preview audio invalid și nu se afirmă că sunetul a fost verificat.
- Testul UI actualizat s-a oprit la inițializarea Tk (`init.tcl` indisponibil în
  mediul restricționat). Testul UI trecut mai jos se referă numai la versiunea
  anterioară, nu la noul panou vocal. Nu este disponibilă autorizare pentru
  repetarea testului în afara sandboxului în această etapă.
- Microfonul utilizatorului nu a fost activat în testele agentului. Dictarea și
  redarea efectivă trebuie verificate din aplicație, în sesiunea desktop normală.

Acceptanță vocală: Setări voce → Test voce; Vorbește → „Show my tasks” → verifică
transcrierea → Trimite; apoi Stop în timpul unei redări și în timpul unei capturi.
Verifică dacă aplicația rămâne receptivă și nu execută transcrieri fără confirmare.

Referințe implementare:

- [Microsoft: SpeechRecognitionEngine](https://learn.microsoft.com/en-us/dotnet/api/system.speech.recognition.speechrecognitionengine)
- [Microsoft: SAPI text literal și flag-uri de vorbire](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms717252(v=vs.85))

## Rezultate istorice v1.0 / v1.0.1

Data: 2 septembrie 2026. Mediu: Windows, Python inclus în runtime-ul Codex.

## Rezultate

- **16/16 teste unitare trecute**: rutare pe toate modulele, separarea datelor,
  note, ștergere explicită, păstrarea istoricului, finalizare task, persistență
  după redeschiderea DB, normalizarea fusului orar, scadențe, deduplicare pe
  sesiune, recuperarea reminderelor la repornire, validare, SQL parametrizat,
  hooks dezactivate, injectarea unui provider și redactarea erorilor.
- **1/1 test desktop trecut**: inițializarea ferestrei Tk, toate modulele și
  secțiunile, salvarea unei note, crearea și finalizarea unui task, inițializarea
  formularelor de task/reminder/notă. Fereastra testului este ascunsă.
- **Compilarea tuturor fișierelor Python a trecut** (`compileall`).

Prima încercare de test Tk în sandbox a raportat `init.tcl` indisponibil.
Fișierele Tcl/Tk există; același test a trecut la rularea autorizată în afara
sandboxului. Nu a fost necesară instalarea ori modificarea runtime-ului.

## Ce nu este demonstrat prin aceste teste

- Nu a fost efectuată o inspecție vizuală prin captură de ecran.
- Nu au fost testate API-uri reale, OAuth, microfon, sinteză vocală sau Telegram:
  acestea nu sunt implementate în v1.
- Sunetul și experiența după suspendarea PC-ului nu au fost testate manual.
- Nu există teste de volum mare, criptare sau multi-user.
- Launcherul Windows corectat a fost verificat cu `Start-Jarvis.cmd --help`:
  selectează runtime-ul Codex disponibil, afișează ajutorul și returnează cod 0.
  Pornirea verifică interpretoarele efectiv, nu doar prezența scurtăturii Windows.
  UTF-8 este activat pentru afișarea diacriticelor în terminal.

Toate testele folosesc date temporare. Pachetul livrat nu conține note sau
task-uri demonstrative în baza utilizatorului; DB apare la prima pornire.

## Acceptanță manuală recomandată

1. Deschide `Start-Jarvis.cmd`, selectează Fishroom și salvează o notă.
2. Creează un reminder pentru peste 1 minut, cu offsetul corect.
3. Verifică bannerul la scadență și finalizează task-ul.
4. Închide și redeschide aplicația; nota trebuie păstrată.
5. Scrie `gmail`, `calendar` și `caută web: test`; trebuie afișată lipsa conexiunii,
   fără rezultate fabricate sau solicitări de credențiale.
