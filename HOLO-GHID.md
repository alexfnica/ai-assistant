# JARVIS AFNICA HOLO — ghid v1.4

## Pornire

Deschide Start-Jarvis-HOLO.cmd din folderul complet JARVIS-AFNICA.
Launcherul caută Python-ul existent pe acest PC înaintea scurtăturii Microsoft Store.
Interfața se deschide în browser, local, pe portul 4891; necesită un browser modern
cu WebGL. Dacă portul e ocupat, închide sesiunea veche sau pornește cu `--port 4892`.
Python 3.11+ este necesar; launcherul comun verifică și existența modulului Tk.

Nu deschide direct holo.html. Nu este instalat un serviciu permanent și nu pornește
automat odată cu Windows. Fereastra serverului trebuie păstrată deschisă.

## Ce poți folosi

- Click simplu pe un modul plutitor: afișează cardurile cu task-uri și notițe.
- Trage cardurile cu mouse-ul; click pe un card deschide conținutul.
- Finalizarea unui task cere două apăsări: Marchează, apoi Confirmă finalizarea.
- Comenzi: `task: Verifică filtrul`, `memorează: Acvariul A are 60 litri`,
  `task-uri`, `memorie`. Selectează contextul sau folosește `/fishroom`, `/youtube`,
  `/jobs`, `/game` înaintea comenzii.
- Formularul Reminder transformă ora locală a PC-ului în UTC pentru stocare.
  Task-urile scadente apar într-un banner cât timp pagina și serverul sunt active.
  HOLO nu trimite notificări când aplicația este închisă și nu trezește PC-ul.
- Actualizează cardurile reîncarcă lista din baza locală. Panoul își actualizează
  automat contoarele, conversația și termenele. Maximum 30 task-uri și 30 note
  pe modul sunt desenate; comenzile de listare oferă acces separat la date.

Datele sunt în `data/jarvis.sqlite3`, aceeași bază ca în varianta desktop.
Modulele YouTube și Job search sunt deocamdată spații locale de organizare,
nu sincronizări de cont. Aruncarea unui card în afara scenei nu șterge datele.

## Voce și Hey Jarvis

Camera și microfonul sunt oprite implicit. Activează butonul **Hey Jarvis: oprit**
pentru a arma detectorul local Windows. Spune **Hey, Jarvis**, așteaptă ASCULT,
apoi dictează. Panoul apare dacă era ascuns, iar textul ajunge în câmpul de comandă.
Verifică textul și apasă Trimite; transcrierea nu execută singură modificări.
Butonul Vorbește pornește dictarea fără expresia de activare.

La Voce și limbă poți selecta vocile/limbile instalate în Windows. Citește
răspunsurile activează redarea opțională. Este o voce Windows configurabilă,
nu o clonă a actorului din film. Pe PC-ul inspectat au fost detectate vocile
David/Zira en-US și recunoaștere en-US; nu presupune dictare română disponibilă.
Pentru detectarea Hey Jarvis este necesară recunoaștere în engleză.

Stop audio oprește dictarea, redarea și detectorul. Detectorul se suspendă când
Jarvis vorbește sau ai o transcriere de verificat. În lipsa cererilor din browser
timp de 10 secunde, serviciul oprește operațiile audio. Limitarea paginilor de fundal
de către browser poate produce această oprire; reactivează explicit când revii.
Nu activa simultan microfonul în varianta desktop și HOLO. Folosește o singură
filă HOLO pentru voce: sesiunea vocală este comună tuturor filelor acestui server.
Hey Jarvis nu poate lansa aplicația dacă serverul este închis și nu aduce garantat
browserul deasupra altor aplicații. Pentru widgeturi Windows separate folosește
varianta desktop existentă.

## Camera și gesturile

Apasă Pornește camera și acordă permisiunea browserului doar dacă dorești.
Modelele MediaPipe, fișierele WebAssembly și grafica three.js sunt incluse local;
nu există fallback la CDN. Imaginea camerei nu este salvată sau trimisă în cloud.
Oprește camera închide fluxul; închiderea paginii îl oprește de asemenea.

Gesturile adaptate din HOLO includ pinch pentru prindere, atingere pentru deschidere,
două mâini pentru redimensionare/rotire și peace pentru resetarea scenei.
Modelele 3D sunt elemente demonstrative, nu date AFNICA. Rezumatul scurt din gesturi
este un extras din text, nu un răspuns generat de un model AI.

## Arhitectură și limite

Browser HOLO → API local autentificat → Jarvis Core → SQLite.
Adaptorul `holo_server.py` servește numai resursele permise, ascultă pe 127.0.0.1,
verifică Host/Origin și folosește un token nou la fiecare pornire. Nu îl expune în rețea.
Comenzile repetate cu același ID sunt deduplicate în sesiune (ultimele 256 cereri).
`holo_voice.py` coordonează vocea Windows și detectorul. Gesturile `/api/state`
sunt doar feedback vizual și nu sunt interpretate drept comenzi.

Gmail, Google Calendar, contul YouTube și conversațiile ChatGPT nu sunt conectate.
Hook-urile existente sunt extensibile; autentificarea și sincronizarea sunt lucrări
separate. Nu există în această versiune auto-modificare a codului, executare de
comenzi în ChatGPT sau un model conversațional conectat. Nu introduce parole
sau chei API în chat pentru a încerca să activezi aceste funcții.

## Proveniență

Interfața, motorul de gesturi și modelele 3D provin din pachetul local furnizat
de utilizator, holo-gestures-free. Licența originală MIT este păstrată în holo/LICENSE,
cu atribuirea Zubair Trabzada / AI Workshop Studio LLC. Pachetul declară three.js
MIT și MediaPipe Apache-2.0; antetele și fișierele vendor au fost păstrate.
Serverul original, notițele demonstrative și jurnalele autorului nu au fost reutilizate.
Folderul original din Downloads nu a fost modificat.
