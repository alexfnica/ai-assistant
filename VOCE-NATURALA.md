# Natural British — voce complet locală

## Cum o activezi

Închide serverul/fereastra Jarvis veche și repornește cu launcherul existent.
Natural British Daniel este selectată implicit când pachetul Kokoro este prezent.
În HOLO: Voce și limbă → selectează Natural British George, Daniel sau Blend.
Bifează Citește răspunsurile și apasă Test voce. În desktop: Setări voce.

Nu trebuie instalat un serviciu cloud, creat cont sau adăugată o cheie API.
Pachetul este pentru Windows x64 și Python 3.12, ca runtime-ul existent pe acest PC.
Modelele și bibliotecile sunt în voice-models/kokoro și voice-natural-runtime.
Nu muta separat aceste directoare. Prima generare încarcă modelul în memorie.

## Ce s-a schimbat

Motorul Kokoro înlocuiește Piper ca alegere implicită. Preseturile sunt:

- George: vocea britanică bm_george, viteză 0,96.
- Daniel: vocea britanică bm_daniel, aceeași viteză pentru comparație.
- Blend: 70% stil George + 30% stil Daniel, amestec de stiluri preexistente.

Nu se adaugă ecou, efect robotic, schimbare artificială a tonalității sau pauze
fixe între propoziții. Intonația și temporizarea provin din model; punctuația
textului rămâne relevantă. Volumul implicit este 85%, cu limitare pentru PCM.
Viteza din desktop rămâne reglabilă. Butonul Stop anulează procesul de generare
sau redare, iar microfonul rămâne suspendat cât timp Jarvis vorbește.

Acestea sunt voci britanice sintetice, NU vocea lui Paul Bettany și NU clone
antrenate pe MP3-urile tale. Alegerea care sună cel mai apropiat se face prin
ascultarea mostrelor. Nu pretind o evaluare auditivă pe care nu o pot efectua.
Modelul folosește engleză britanică; răspunsurile românești nu sunt traduse automat.

## Confidențialitate

Instalarea a descărcat biblioteci și un model public. Înregistrările furnizate
și textul conversațiilor nu au fost încărcate. Sinteza folosește numai fișiere
locale, CPU și ieșirea audio Windows. Telemetria ONNX este dezactivată.
Redarea curentă este generată în memorie. Doar mostrele cerute sunt salvate în WAV.
Nu s-au modificat permisiunile camerei sau microfonului.

## Verificare pe acest PC

- 55/55 teste automate trecute.
- Cele trei mostre au fost sintetizate real: George 8,36 s, Daniel 7,04 s,
  Blend 7,81 s, PCM mono 24 kHz / 16 biți, fără clipping și fără fișiere mute.
- Generarea mostrelor a blocat socket.create_connection, socket.connect și
  rezolvarea DNS în procesul Python. A reușit folosind fișierele locale;
  acesta este un test al traseului Python, nu o captură completă de trafic OS.
- Generarea prin adaptorul aplicației a trecut; alegerea implicită a fost ulterior
  schimbată la Daniel, conform preferinței utilizatorului.
- Anularea unei generări în curs a trecut, fără rezultat audio tardiv.
- Timpii măsurați pentru mostre au fost aproximativ 6,5–11,2 secunde, inclusiv
  încărcarea modelului. Nu este o conversație audio instantanee.
- Nu am ascultat mostrele și nu am confirmat sunetul la difuzoare. Calitatea
  percepută și asemănarea cu JARVIS trebuie evaluate de utilizator.

## Surse și licențe

- [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx), versiunea 0.6.1;
  codul adaptorului upstream este MIT.
- [Kokoro-82M și vocile](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md),
  model Apache-2.0.
- [Fișierele ONNX distribuite de FastRTC](https://huggingface.co/fastrtc/kokoro-onnx/tree/main),
  folosite deoarece descărcarea assetului GitHub s-a blocat.
- Modelul și stilurile sunt păstrate nemodificate; sursele, dimensiunile și
  hash-urile descărcărilor se găsesc în voice-models/kokoro/sources.json.
- Licențele modelului și adaptorului sunt păstrate în același director.
  Bibliotecile incluse au licențele proprii, păstrate în runtime; inclusiv
  fonemizarea eSpeak/phonemizer. Nu elimina licențele la redistribuire.

Vechea arhivă HOLO-Voice conține Piper, nu această actualizare Kokoro. Folosește
folderul actual de pe acest PC și launcherul existent.
