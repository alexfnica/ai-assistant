# Voce AFNICA — British Calm și British HUD

## Folosire

Închide sesiunea Jarvis veche și pornește din nou Start-Jarvis-HOLO.cmd sau
Start-Jarvis.cmd. Vocea AFNICA · British Calm este selectată implicit când
runtime-ul local este disponibil. În HOLO bifează Citește răspunsurile, apoi
deschide Voce și limbă → Test voce. Poți selecta British HUD pentru efect discret.
În varianta desktop opțiunile sunt în Setări voce. Stop întrerupe și generarea.

Este o voce masculină britanică, cu accent nord-englez; nu este accentul și vocea
identică a lui JARVIS / Paul Bettany. Nu am clonat vocea din MP3-uri. Pronunția
naturală este în engleză; textele românești nu sunt traduse automat și vor avea
pronunție engleză. Chatul și recunoașterea vocală nu au fost schimbate.

British Calm folosește Piper local, durată 1,20× la viteza implicită −1,
pauze suplimentare de 180 ms între segmente, variație redusă și volum 85%.
British HUD adaugă un ecou de 14 ms la 7% și o modulație foarte mică.
Acestea sunt alegeri de stil pentru o primă aproximare, nu parametri extrași exact
din vocea unui actor. Pentru alegerea finală trebuie ascultate mostrele.

Nu există cheie API, abonament sau upload audio. Motorul și modelul au fost
descărcate o singură dată; generarea ulterioară este locală, cu telemetria ONNX
dezactivată. Redarea obișnuită este generată în memorie, nu într-un jurnal audio.
Microfonul rămâne opt-in; acest update nu îl activează.

## Analiza înregistrărilor furnizate

Analiză locală a întregului semnal, fără ascultare directă sau separarea vorbitorului.
Estimarea frecvenței fundamentale folosește autocorelație pe cadre de 40 ms,
interval 70–300 Hz, prag de periodicitate 0,65 și filtrare după energie.

| Fișier | Durată | Format | Nivel RMS | Mediană F0 candidat |
|---|---:|---|---:|---:|
| JARVIS (1).mp3 | 480,70 s | stereo, 48 kHz | −19,5 dBFS | 160,0 Hz |
| JARVIS II.mp3 | 16,87 s | stereo, 48 kHz | −26,7 dBFS | 166,7 Hz |

F0 se referă doar la cadrele acceptate de estimator: 2452, respectiv 111 cadre.
Muzica, efectele, alți vorbitori și erorile de octavă pot influența aceste cifre.
Ele NU sunt o amprentă a lui JARVIS și nu permit deducerea accentului ori a
numărului de cuvinte/minut. Fișierele originale nu au fost schimbate sau copiate
în aplicație. Nu s-a antrenat un model pe ele.

## Verificare

- 51 teste automate trecute, inclusiv preferința vocii britanice și limitele vitezei.
- Generare reală locală a două mostre WAV mono, 22.050 Hz, 7,91 secunde fiecare.
- Generare prin adaptorul folosit de aplicație verificată separat; fără SAPI TTS.
- Mostra Calm: nivel RMS −20,0 dBFS, vârf −2,3 dBFS, fără depășirea nivelului PCM.
- Nu am putut asculta mostrele. Asemănarea perceptivă și redarea la difuzoarele
  utilizatorului nu sunt confirmate. Generarea fișierelor audio este confirmată.

## Componente și proveniență

- [Piper, motor local](https://github.com/OHF-Voice/piper1-gpl), piper-tts 1.7.0,
  GPL-3.0. Runtime Python 3.12 Windows x64 în voice-runtime, licențe păstrate.
- [Model northern_english_male, medium](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/northern_english_male/medium),
  model card păstrat în voice-models/MODEL_CARD; dataset indicat CC-BY-SA 4.0,
  [OpenSLR 83](https://www.openslr.org/83/). Modelul nu a fost modificat.
- [API de sinteză și parametri](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md).

Nu elimina licențele și verifică obligațiile componentelor înainte de redistribuire.
Runtime-ul inclus nu este universal: pe alt Python / sistem trebuie instalate
dependențe compatibile. Pe acest PC launcherul folosește Python-ul existent 3.12.
