/* AFNICA bridge: no external endpoints, no camera at startup, no automatic mutations. */
(() => {
  'use strict';
  document.title = 'JARVIS AFNICA · HOLO';
  const token = document.querySelector('meta[name="jarvis-session"]').content;
  const originalFetch = window.fetch.bind(window);
  window.fetch = (resource, options = {}) => {
    const url = new URL(typeof resource === 'string' ? resource : resource.url, location.href);
    if (url.origin !== location.origin) return Promise.reject(Error('Conexiunile externe sunt oprite.'));
    const headers = new Headers(options.headers || {});
    if (url.pathname.startsWith('/api/')) headers.set('X-Jarvis-Token', token);
    return originalFetch(resource, {...options, headers});
  };
  const $ = id => document.getElementById(id);
  let busy = false, lastHistory = '', transcriptId = 0, activation = 0, voiceState = {}, polling = false;
  let voiceLists = '', noticeTimer;
  function notify(text) { $('notice').textContent = text; $('notice').style.display = 'block'; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $('notice').style.display = 'none', 8000); }
  async function api(path, body) {
    const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Operație nereușită');
    return data;
  }
  async function voice(body) { try { return await api('/api/voice', body); } catch(error) { notify(error.message); return null; } }
  async function refresh() {
    if (polling) return; polling = true;
    try {
      const data = await api('/api/status');
      $('counts').textContent = `${data.tasks} task-uri deschise · ${data.notes} note salvate · AI: ${data.model || 'Command-only'}`;
      $('due-banner').textContent = data.due.length ? `${data.due.length} scadente · ${data.due[0].title}` : '';
      if (data.alerts && data.alerts.length) { notify(data.alerts.join(' ')); if (window.__jarvisSay) window.__jarvisSay(data.alerts.join(' ')); }   // fishroom routines: shown once and spoken once
      const signature = JSON.stringify(data.history);
      if (signature !== lastHistory) {
        lastHistory = signature; $('messages').replaceChildren();
        if (!data.history.length) $('messages').textContent = 'At your service, sir. You may write in Romanian; I shall reply in English. Enter help to begin.';
        for (const message of data.history) {
          const row = document.createElement('div'); row.className='message';
          const who = document.createElement('b'); who.textContent=(message.role==='user'?'TU':'JARVIS')+' / '+message.module;
          row.append(who, document.createTextNode(message.content)); $('messages').append(row);
        }
        $('messages').scrollTop=$('messages').scrollHeight;
      }
      voiceState = await api('/api/voice');
      $('voice-status').textContent=voiceState.detail || 'Voce indisponibilă';
      $('wake').textContent=voiceState.wake?'Hey Jarvis: activ':'Hey Jarvis: oprit';
      $('wake').setAttribute('aria-pressed', String(!!voiceState.wake));
      $('listen').disabled=voiceState.state==='disabled';
      if (voiceState.activation > activation) { activation=voiceState.activation; document.body.classList.remove('panel-hidden'); $('command').focus(); }
      if (voiceState.transcript_id > transcriptId) {
        transcriptId=voiceState.transcript_id; document.body.classList.remove('panel-hidden');
        $('command').value += ($('command').value.trim()?' ':'') + voiceState.transcript;
        $('command').focus();
      }
      const lists=JSON.stringify([voiceState.voices,voiceState.recognizers]);
      if (lists!==voiceLists) {
        voiceLists=lists;
        for (const [id,items,selected] of [['voice-choice',voiceState.voices||[],voiceState.voice_id],['recognizer-choice',voiceState.recognizers||[],voiceState.recognizer_id]]) {
          $(id).replaceChildren();
          for(const item of items){const option=document.createElement('option');option.value=item.id;option.textContent=item.name+' · '+item.culture;option.selected=item.id===selected;$(id).append(option);}
        }
      }
    } catch(error) { $('counts').textContent='Connexion întreruptă · redeschide pagina dacă ai repornit serverul.'; }
    finally { polling=false; }
  }
  async function send(text, module=$('module').value) {
    if (busy) throw Error('Așteaptă comanda în curs.');
    if (!text.trim()) throw Error('Scrie o comandă.');
    busy=true; $('send-command').disabled=true; $('send-command').textContent='Thinking locally…';
    try {
      const result=await api('/api/command',{text,module,request_id:crypto.randomUUID()});
      $('module').value=result.module;
      if (voiceState.state !== 'disabled') await voice({action:'reviewed'});
      if ($('speak-replies').checked) await voice({action:'speak',text:result.text});
      window.__holo?.reload(); await refresh(); return result;
    } catch(error) { notify(error.message); throw error; }
    finally { busy=false; $('send-command').disabled=false; $('send-command').textContent='Send →'; }
  }
  $('command-form').onsubmit=async event=>{event.preventDefault();try{await send($('command').value);$('command').value='';}catch(_){} };
  $('show-tasks').onclick=()=>send('task-uri').catch(()=>{});
  $('show-notes').onclick=()=>send('memorie').catch(()=>{});
  $('reload-cards').onclick=()=>{window.__holo?.reload();refresh();};
  $('panel-toggle').onclick=()=>document.body.classList.toggle('panel-hidden');
  $('listen').onclick=()=>voice({action:'listen'});
  $('voice-stop').onclick=()=>voice({action:'stop'});
  $('wake').onclick=()=>voice({action:'wake',enabled:!voiceState.wake});
  $('voice-choice').onchange=()=>voice({action:'select',voice_id:$('voice-choice').value});
  $('recognizer-choice').onchange=()=>voice({action:'select',recognizer_id:$('recognizer-choice').value});
  $('voice-test').onclick=()=>voice({action:'speak',text:'Jarvis AFNICA online. Local systems ready.'});
  $('reminder-form').onsubmit=async event=>{
    event.preventDefault();const date=new Date($('reminder-date').value);
    if (!Number.isFinite(date.getTime())) return notify('Alege o dată validă.');
    try {await send('reminder: '+date.toISOString()+' | '+$('reminder-title').value);$('reminder-title').value='';}catch(_){}
  };
  window.afnica={send,narrate:text=>{if($('speak-replies').checked)voice({action:'speak',text});}};
  refresh(); setInterval(refresh,1500);
})();

/* ===== Reactor scene v3: dense particle bands, mesh sphere, mic mode, bottom bar (original design) ===== */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const cv = document.createElement('canvas'); cv.id = 'reactor'; document.body.prepend(cv);
  const ctx = cv.getContext('2d');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W = 0, H = 0, cx = 0, cy = 0, R = 0, dpr = 1, speak = 0, listen = 0, lvl = 0, voiceHold = 0, t0 = performance.now();
  const CY = '80,230,195', TAU = 6.2832, N = 2200;
  // two touching bands of particles with a radial thickness
  const bands = [{k: 1, th: .1, ph: 1, sp: .5, amp: .05}, {k: .9, th: .08, ph: 4, sp: .8, amp: .04}].map(b =>
    Object.assign(b, {pts: Array.from({length: N}, () => ({a: Math.random() * TAU, o: (Math.random() + Math.random() - 1), b: Math.random()}))}));
  // sphere of points joined by short lines (triangle-mesh look)
  const sph = Array.from({length: 150}, (_, i) => {
    const y = 1 - 2 * (i + .5) / 150, r = Math.sqrt(1 - y * y), a = i * 2.39996;
    return [Math.cos(a) * r, y, Math.sin(a) * r];
  });
  function resize() {
    dpr = Math.min(devicePixelRatio || 1, 2); W = innerWidth; H = innerHeight;
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cx = W * .7; cy = H * .44; R = Math.max(120, Math.min(H * .295, W * .2));
  }
  const wob = (a, t, b) => Math.sin(a * 3 + t * b.sp + b.ph) * .5 + Math.sin(a * 5 - t * b.sp * 1.3 + b.ph * 2) * .3 + Math.sin(a * 2 + t * .6 + b.ph * 3) * .4;
  const arc = (r, w, al, a0, len) => { ctx.strokeStyle = `rgba(${CY},${al})`; ctx.lineWidth = w; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + len); ctx.stroke(); };
  function sphere(t, r) {
    const c = Math.cos(t * .35), s = Math.sin(t * .35), P = [];
    for (const [x, y, z] of sph) { const X = x * c + z * s, Z = -x * s + z * c; P.push([cx + X * r, cy + y * r, Z]); }
    ctx.lineWidth = .7;
    for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
      const dx = P[i][0] - P[j][0], dy = P[i][1] - P[j][1];
      if (dx * dx + dy * dy < (r * .3) ** 2 && (P[i][2] + P[j][2]) > -.3) { ctx.strokeStyle = `rgba(${CY},${.18 + .25 * (P[i][2] + 1) / 2})`; ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); ctx.stroke(); }
    }
    ctx.fillStyle = 'rgba(200,255,245,.9)';
    for (const p of P) if (p[2] > 0) ctx.fillRect(p[0] - 1, p[1] - 1, 2, 2);
  }
  function mic(a) {
    const u = R * .22; ctx.save(); ctx.globalAlpha = a; ctx.translate(cx, cy);
    ctx.strokeStyle = 'rgba(120,255,225,.95)'; ctx.fillStyle = 'rgba(40,150,135,.55)'; ctx.lineWidth = 3; ctx.shadowColor = `rgba(${CY},1)`; ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(0, 0, R * .42, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(-u * .42, -u * 1.15, u * .84, u * 1.55, u * .42); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, -u * .05, u * .78, .15 * Math.PI, .85 * Math.PI); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, u * .73); ctx.lineTo(0, u * 1.05); ctx.moveTo(-u * .4, u * 1.05); ctx.lineTo(u * .4, u * 1.05); ctx.stroke();
    ctx.restore();
  }
  function clock(t, a) {
    const d = new Date(), p = n => String(n).padStart(2, '0'), fs = Math.round(R * .22);
    ctx.save(); ctx.globalAlpha = a; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.shadowColor = `rgba(${CY},.9)`; ctx.shadowBlur = 12; ctx.fillStyle = 'rgba(200,255,245,.95)';
    ctx.font = `300 ${fs}px Consolas,"Courier New",monospace`; ctx.fillText(`${p(d.getHours())}:${p(d.getMinutes())}`, cx - fs * .2, cy + R * .46);
    ctx.font = `300 ${fs * .4}px Consolas,monospace`; ctx.textAlign = 'left'; ctx.fillText(`:${p(d.getSeconds())}`, cx + fs * 1.05, cy + R * .46 + fs * .15);
    ctx.textAlign = 'center'; ctx.font = `italic 600 ${fs * .42}px "Segoe UI",Arial,sans-serif`; ctx.fillStyle = `rgba(${CY},.9)`;
    ctx.fillText('J . A . R . V . I . S', cx, cy - R * 1.22);
    ctx.font = `${fs * .28}px "Segoe UI",Arial,sans-serif`; ctx.fillStyle = 'rgba(150,230,215,.7)';
    ctx.fillText(d.toLocaleDateString('en-GB', {weekday: 'long', day: 'numeric', month: 'long'}).toUpperCase(), cx, cy + R * .72);
    ctx.restore();
  }
  function frame(now) {
    const t = reduce ? 0 : (now - t0) / 1000, B = document.body.classList;
    speak += ((B.contains('speaking') ? 1 : 0) - speak) * .07; lvl += ((window.__micLevel || 0) - lvl) * .4;
    if (lvl > .16) voiceHold = now + 900;
    listen += (((B.contains('listening') || (B.contains('blistening') && now < voiceHold)) ? 1 : 0) - listen) * .12;
    const act = Math.max(speak * .5, Math.min(1, lvl * 4));
    ctx.clearRect(0, 0, W, H);
    const g = ctx.createRadialGradient(cx, cy, R * .1, cx, cy, R * 1.7);
    g.addColorStop(0, `rgba(${CY},${.09 + act * .08})`); g.addColorStop(.6, `rgba(${CY},.04)`); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = `rgb(${CY})`;
    for (const b of bands) for (const p of b.pts) {
      const w = wob(p.a, t, b) * (b.amp + act * .06) + Math.sin(t * 9 + p.a * 11) * act * .014;
      const r = R * (b.k + w + p.o * b.th);
      ctx.globalAlpha = .25 + .6 * p.b; ctx.fillRect(cx + Math.cos(p.a) * r, cy + Math.sin(p.a) * r, 1.7, 1.7);
    }
    ctx.globalAlpha = 1;
    ctx.shadowColor = `rgba(${CY},.8)`; ctx.shadowBlur = 8;
    for (const [k, al] of [[.72, .18], [.66, .14], [.6, .12]]) arc(R * k, 1, al + act * .1, 0, TAU);
    ctx.shadowBlur = 0;
    sphere(t, R * .3 * (1 + Math.sin(t * 2) * .012 + act * Math.sin(t * 10) * .03));
    arc(R * .33, 2, .7, 0, TAU);
    if (listen > .02) { ctx.globalAlpha = listen; mic(listen); ctx.globalAlpha = listen; ctx.shadowColor = `rgba(${CY},1)`; ctx.shadowBlur = 14; arc(R * .47 + lvl * R * .25, 3, .25 + Math.min(.7, lvl * 2), 0, TAU); ctx.shadowBlur = 0; }
    ctx.globalAlpha = 1;
    clock(t, 1 - listen);
    requestAnimationFrame(frame);
  }
  // ---- bottom bar: real controls, wired to the existing panel ----
  const bar = document.createElement('nav'); bar.id = 'holobar';
  const icon = {
    brief: '<circle cx="24" cy="24" r="17"/><path d="M24 12v13l9 5"/>',
    docs: '<path d="M14 8h14l8 8v24H14z"/><path d="M28 8v8h8M19 26h12M19 32h12"/>',
    mic: '<rect x="19" y="6" width="10" height="21" rx="5"/><path d="M12 22a12 12 0 0 0 24 0M24 34v8M17 42h14"/>',
    tasks: '<path d="M10 14l4 4 7-8M10 28l4 4 7-8M27 16h13M27 30h13"/>',
    notes: '<path d="M12 8h24v32H12zM18 17h12M18 24h12M18 31h7"/>'};
  const items = [['brief', 'Briefing', () => window.afnica.send('briefing')], ['docs', 'Documents', () => window.afnica.send('documente')],
    ['mic', 'Mute', () => $('listen').click()], ['tasks', 'Tasks', () => window.afnica.send('task-uri')], ['notes', 'Notes', () => window.afnica.send('memorie')]];
  for (const [k, label, fn] of items) {
    const b = document.createElement('button'); b.type = 'button'; b.title = label; b.setAttribute('aria-label', label); if (k === 'mic') b.className = 'mic';
    b.innerHTML = `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icon[k]}</svg><span>${label}</span>`;
    b.onclick = () => { try { const r = (k === 'mic' && window.__micToggle && window.__micToggle()) ? null : fn(); r && r.catch && r.catch(() => {}); } catch (_) {} }; bar.append(b);
  }
  document.body.append(bar);
  addEventListener('resize', resize); resize(); requestAnimationFrame(frame);
  // voice on by default; mirror voice state onto <body> for the animation
  const box = $('speak-replies'); if (box && !box.dataset.touched) box.checked = true;
  box?.addEventListener('change', () => box.dataset.touched = '1');
  setInterval(() => fetch('/api/voice').then(r => r.json()).then(v => {
    document.body.classList.toggle('speaking', v.state === 'speaking' || !!window.__spk);
    document.body.classList.toggle('listening', v.state === 'listening');
  }).catch(() => {}), 500);
})();
addEventListener('keydown', e => { if (e.key === '?' && !/INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || '')) document.body.classList.toggle('show-legend'); });
(() => { const l = document.getElementById('legend'); if (l) l.style.setProperty('display', 'none', 'important');
  addEventListener('keydown', e => { if (e.key === '?' && l) { const on = document.body.classList.contains('show-legend'); l.style.setProperty('display', on ? 'block' : 'none', 'important'); } }); })();
/* No 3D demo props (triceratops, Apollo 11): the props list is served empty. Move .glb files back/edit here to re-enable. */
(() => { const f = window.fetch; window.fetch = (r, o) => {
  const u = typeof r === 'string' ? r : (r && r.url) || '';
  return u.includes('/api/props') ? Promise.resolve(new Response('[]', {status: 200, headers: {'Content-Type': 'application/json'}})) : f(r, o); }; })();

/* ===== Microphone: always on from the start (browser recognition), mute button + M key, live level meter ===== */
(() => {
  'use strict';
  const B = document.body, $ = id => document.getElementById(id);
  let stream = null, ctxA = null, an = null, buf = null, raf = 0, idleSince = 0, starting = false;
  const toast = m => { const n = $('notice'); if (!n) return; n.textContent = m; n.style.display = 'block'; setTimeout(() => n.style.display = 'none', 7000); };
  const store = { get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (_) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} } };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let muted = store.get('jarvisMuted', '0') === '1';
  let needWake = store.get('jarvisNeedWake', '0') === '1';
  window.__alwaysOn = !!SR;
  function tick() {
    an.getByteTimeDomainData(buf); let sum = 0;
    for (const v of buf) { const x = (v - 128) / 128; sum += x * x; }
    window.__micLevel = Math.min(1, Math.sqrt(sum / buf.length) * 9);
    raf = requestAnimationFrame(tick);
  }
  async function startMeter() {
    if (stream || starting) return; starting = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}});
      ctxA = new (window.AudioContext || window.webkitAudioContext)(); an = ctxA.createAnalyser(); an.fftSize = 1024; buf = new Uint8Array(an.fftSize);
      ctxA.createMediaStreamSource(stream).connect(an); tick();
    } catch (e) { muted = true; paint(); toast('Microfonul e blocat. Apasă lacătul/camera din bara ferestrei → Microfon → Permite, apoi apasă Unmute.'); }
    starting = false;
  }
  function stopMeter() { if (!stream) return; cancelAnimationFrame(raf); stream.getTracks().forEach(t => t.stop()); ctxA && ctxA.close(); stream = ctxA = an = null; window.__micLevel = 0; }
  // ---- continuous recognition ----
  let recStart = 0, barged = false, wasSp = false, rec = null, lastSpoke = 0, pending = '', acc = '', pendTimer = 0;
  const PAUSE_MS = 1100, FINAL_MS = 350;   // sent 1.1 s after the last word, or 0.35 s after the recognizer marks the phrase as finished
  const words = x => String(x).toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean);
  const isEcho = x => { const w = words(x); if (w.length < 3) return false; const said = new Set(words(window.__lastSaid || '')); return w.filter(v => said.has(v)).length / w.length >= .7; };   // his own voice heard back
  const flush = () => { clearTimeout(pendTimer); const x = pending; pending = ''; acc = ''; if (!x.trim()) return; if (isEcho(x) || Date.now() - lastSpoke < 1500) { $('command').value = ''; return; } $('command').value = x.trim(); handle(x); if (rec) { try { rec.abort(); } catch (_) {} rec = null; B.classList.remove('blistening'); } };   // fresh recogniser session after every sent command, so his reply is never glued to your next phrase
  const speaking = () => !!window.__spk || B.classList.contains('speaking');
  async function handle(text) {
    let t = text.trim(); if (!t) return;
    const key = t.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim(), nowT = Date.now();   // the same phrase twice within a few seconds is one command
    if (key && key === handle.k && nowT - handle.t < 6000) return; handle.k = key; handle.t = nowT;
    const wake = /^(?:hey |ok |okay )?jarvis\b[\s,.:!?-]*/i;
    const musicOk = /^(?:please\s+)?(?:play|stop|pause|resume|next|skip|previous|open|launch|start|go to|show|check|read|search|tell|what|what's|how|list|briefing|connect|remind|add|send|deschide|porneste|volume|turn (?:it |the volume )?(?:up|down)|louder|quieter)\b/i;
    if (window.__musicPlaying && !needWake) {   // the mic also hears the song: take only what follows the last "Jarvis", or a music command at the very end
      const all = [...t.matchAll(/\b(?:hey |ok |okay )?jarvis\b[\s,.:!?-]*/gi)];
      const tail = t.match(/(?:^|[\s,.!?])((?:please\s+)?(?:stop(?: the)?(?: music| song)?|pause|resume|next(?: song)?|skip|louder|quieter|volume (?:up|down)|turn (?:it |the volume )?(?:up|down))[\s.!?]*)$/i);
      if (all.length) { const m = all[all.length - 1]; t = t.slice(m.index + m[0].length).trim(); if (!t) { window.__jarvisSay && window.__jarvisSay('Yes, sir?'); return; } t = 'jarvis ' + t; }
      else if (tail) t = tail[1].trim();
      else if (!musicOk.test(t) || words(t).length > 10) { $('command').value = ''; return; }
    } else if (needWake && !wake.test(t)) { /* handled below */ }
    if (needWake) { if (!wake.test(t)) { toast('Am auzit: "' + t + '" — spune „Jarvis” înainte, sau apasă Say "Jarvis" ca să scrie NOT NEEDED.'); $('command').value = ''; return; } }
    t = t.replace(wake, '').trim();
    if (!t) { window.__jarvisSay && window.__jarvisSay('Yes, sir?'); return; }
    $('command').value = t;
    try { await window.afnica.send(t); $('command').value = ''; } catch (_) {}
  }
  const musicCut = x => {
    const all = [...x.matchAll(/\b(?:hey |ok |okay )?jarvis\b[\s,.:!?-]*/gi)];
    if (all.length) { const m = all[all.length - 1], rest = x.slice(m.index + m[0].length).trim(); return rest ? 'jarvis ' + rest : null; }
    const tail = x.match(/(?:^|[\s,.!?])((?:please\s+)?(?:stop(?: the)?(?: music| song)?|pause|resume|next(?: song)?|skip|louder|quieter|volume (?:up|down)|turn (?:it |the volume )?(?:up|down))[\s.!?]*)$/i);
    if (tail) return tail[1].trim();
    const w = words(x); return w.length <= 10 && /^(?:please\s+)?(?:play|stop|pause|resume|next|skip|previous|volume|louder|quieter|open|launch|start|go to|show|check|read|search|tell|what|what's|how|list|briefing|connect|remind|add|send|deschide|porneste)\b/i.test(x) ? x : null;
  };
  function startRec() {
    if (!SR || muted || rec) return;
    recStart = Date.now(); const me = rec = new SR(); rec.lang = 'en-GB'; rec.continuous = true; rec.interimResults = true;
    rec.onstart = () => { if (rec === me) B.classList.add('blistening'); };
    rec.onresult = e => {
      if (rec !== me) return;   // a session that was aborted must not feed results
      const STOP = /(?:^|[\s,.!?])(?:please[\s,]+)?(?:stop|be quiet|quiet|silence|enough|that'?s enough|shut up|cancel)(?:[\s,]+(?:talking|speaking|please|now|jarvis))*[\s.!?]*$/i;   // a stop phrase at the end of what was heard, even if his own voice leaks into the start
      if (speaking() || Date.now() - lastSpoke < 1500) {   // while Jarvis talks: a stop phrase, or you speaking over him, cuts him off; his own voice is ignored
        let cut = false;
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const tx = e.results[i][0].transcript.trim();
          if (STOP.test(tx) && window.__jarvisStop) { window.__jarvisStop(); pending = ''; acc = ''; clearTimeout(pendTimer); $('command').value = ''; return; }
          const w = words(tx), said = new Set(words(window.__lastSaid || ''));
          if (speaking() && w.length >= 2 && w.filter(v => said.has(v)).length / w.length < .5) cut = true;   // words that are not his own: you are talking
        }
        if (!cut) return;
        if (window.__jarvisStop) window.__jarvisStop();
        lastSpoke = 0; acc = ''; pending = ''; barged = true;   // and keep what you are saying as the next command
      }
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i], t = r[0].transcript;
        if (r.isFinal) acc = (acc + ' ' + t).trim();
        const next = r.isFinal ? acc : (acc + ' ' + t).trim();
        if (window.__musicPlaying) {   // the song is in the mic too: only "Jarvis ..." or a music command counts, and the lyrics must not keep the send-timer from firing
          const cutM = musicCut(t.trim()) || musicCut(next);   // this result alone first: earlier lyrics are not part of it
          if (!cutM) { if (!pending) $('command').value = t.trim().slice(-80); continue; }   // shown, not sent
          if (cutM === pending && pendTimer) continue;
          pending = cutM; $('command').value = pending; clearTimeout(pendTimer); pendTimer = setTimeout(flush, 900); continue;
        }
        if (next === pending && pendTimer && !r.isFinal) continue;   // same words again: do not restart the timer
        pending = next; $('command').value = pending;
        clearTimeout(pendTimer); pendTimer = setTimeout(flush, r.isFinal ? FINAL_MS : PAUSE_MS);
      }
    };
    rec.onerror = e => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { muted = true; paint(); toast('Microfon blocat sau recunoașterea vocală e oprită. Permite microfonul și apasă Unmute.'); }
      else if (e.error === 'network') toast('Recunoașterea vocală are nevoie de internet.');
    };
    rec.onend = () => { if (rec !== me) return; B.classList.remove('blistening'); rec = null; flush(); };   // an old aborted session must not clear the new one
    try { rec.start(); } catch (_) { rec = null; }
  }
  function stopRec() { clearTimeout(pendTimer); pending = ''; acc = ''; if (rec) { try { rec.abort(); } catch (_) {} rec = null; } B.classList.remove('blistening'); }
  setInterval(() => {
    const sp = speaking(); if (sp) lastSpoke = Date.now();   // keep listening while he talks, so "please stop" can interrupt
    if (sp && !wasSp && rec) { try { rec.abort(); } catch (_) {} rec = null; pending = ''; acc = ''; clearTimeout(pendTimer); B.classList.remove('blistening'); }   // new session when he starts talking
    if (wasSp && !sp) { if (barged) barged = false; else { stopRec(); $('command').value = ''; } }   // his voice may still be in the recogniser: start from a clean session
    wasSp = sp;
    if (window.__musicPlaying && rec && !pending && !sp && Date.now() - recStart > 10000) { try { rec.abort(); } catch (_) {} rec = null; B.classList.remove('blistening'); }   // long song sessions fill up with lyrics: start fresh every 10 s
    if (SR && !muted && !rec && (sp || Date.now() - lastSpoke > 1200)) startRec();
    const wantMeter = !muted && (SR ? true : (B.classList.contains('listening') || B.classList.contains('blistening')));
    if (wantMeter) { idleSince = 0; startMeter(); } else if (stream) { idleSince = idleSince || Date.now(); if (Date.now() - idleSince > 500) stopMeter(); }
  }, 250);
  // ---- mute control ----
  let btn = null;
  function paint() {
    B.classList.toggle('muted', muted);
    if (btn) { btn.querySelector('span').textContent = muted ? 'Unmute' : 'Mute'; btn.setAttribute('aria-pressed', String(muted)); btn.title = muted ? 'Microphone is off. Click to turn it on (M)' : 'Microphone is on. Click to mute (M)'; }
  }
  function toggle() {
    muted = !muted; store.set('jarvisMuted', muted ? '1' : '0'); paint();
    if (muted) { stopRec(); stopMeter(); } else { startMeter(); startRec(); }
  }
  window.__micToggle = () => { if (!SR) return false; toggle(); return true; };
  addEventListener('keydown', e => { if ((e.key === 'm' || e.key === 'M') && !/INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || '')) { if (SR) toggle(); } });
  const bar = $('holobar'); if (bar) {
    btn = bar.querySelector('button.mic');
    const w = document.createElement('button'); w.type = 'button'; w.className = 'tog';
    const paintW = () => { w.innerHTML = '<span>Say "Jarvis"</span><b>' + (needWake ? 'REQUIRED' : 'not needed') + '</b>'; w.setAttribute('aria-pressed', String(needWake)); };
    w.onclick = () => { needWake = !needWake; store.set('jarvisNeedWake', needWake ? '1' : '0'); paintW(); }; paintW(); bar.append(w);
  }
  paint();
  if (SR && !muted) { startMeter(); }
})();

/* ===== Voice output: natural local Kokoro (streamed sentence by sentence) with instant browser voice as fallback ===== */
(() => {
  'use strict';
  const synth = window.speechSynthesis;
  const kind = () => 'jarvis3';   // the one voice: Jarvis III, with the instant browser voice only as a fallback
  let gen = 0, audio = null, voices = [];
  if (synth) { const load = () => { voices = synth.getVoices(); }; load(); synth.onvoiceschanged = load; }
  const B = document.body;
  const spokenList = t => { const s = String(t), n = (s.match(/^\d{1,2}\. /gm) || []).length; return n >= 3 ? 'Here are ' + n + ' items, numbered on screen. ' + s.replace(/^\d{1,2}\. .*$/gm, ' ') : s; };
  const clean = t => spokenList(t).replace(/\([^)]*\)/g, ' ').replace(/\b[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+\b/g, ' ').replace(/\bon [A-Z]{5,}\b/g, '').replace(/AC\/DC/g, 'A C D C').replace(/^Sir,\s*/i, '').replace(/J\.?A\.?R\.?V\.?I\.?S\.?/g, 'Jarvis').replace(/\bAFNICA\b/g, 'Afnica')
    .replace(/\.(xlsx|xls|csv|md|txt)\b/gi, '').replace(/#(\d+)/g, 'number $1').replace(/(\d)\s*%/g, '$1 percent').replace(/[\u2013\u2014]/g, ', ')
    .replace(/https?:\/\/\S+/g, '').replace(/[#*_`>|•·]/g, ' ').replace(/\s+-\s+/g, ', ').replace(/\s+/g, ' ').trim().slice(0, 1200);
  const chunks = t => { const out = []; for (const p of (t.match(/[^.!?\n]+[.!?]*/g) || [t])) { const q = p.trim(); if (!q) continue;
    if (out.length && (out[out.length - 1].length < 40)) out[out.length - 1] += ' ' + q; else out.push(q); } return out; };
  function stopAll() { gen++; if (synth) synth.cancel(); if (audio) { try { audio.pause(); } catch (_) {} audio = null; } (window.__spk = false, B.classList.remove('speaking')); }
  function basic(text) {
    if (!synth) return; const g = ++gen; synth.cancel();
    const pick = () => voices.find(v => /en-GB/i.test(v.lang) && /george|ryan|daniel|thomas|male/i.test(v.name) && !/female|sonia|libby|maisie/i.test(v.name)) || voices.find(v => /en-GB/i.test(v.lang)) || voices.find(v => /^en/i.test(v.lang));
    for (const part of chunks(text)) { const u = new SpeechSynthesisUtterance(part), v = pick(); if (v) u.voice = v; u.lang = v ? v.lang : 'en-GB'; u.rate = 1; u.pitch = .95;
      u.onstart = () => (window.__spk = true, B.classList.add('speaking')); u.onend = u.onerror = () => { if (g === gen && !synth.speaking && !synth.pending) (window.__spk = false, B.classList.remove('speaking')); }; synth.speak(u); }
  }
  async function wav(text, v) {
    const r = await fetch('/api/tts', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(v ? {text, voice: v} : {text})});
    if (!r.ok) { let m = 'tts ' + r.status; try { m = (await r.json()).error || m; } catch (_) {} throw Error(m); }
    return URL.createObjectURL(await r.blob());
  }
  function toast(msg) {
    let d = document.getElementById('voicetoast');
    if (!d) { d = document.createElement('div'); d.id = 'voicetoast'; d.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:99;background:#04161bee;color:#bff;border:1px solid #2bd;padding:8px 14px;border-radius:8px;font:13px system-ui;max-width:80vw'; document.body.append(d); }
    d.textContent = 'Voice: ' + msg; d.style.display = 'block'; clearTimeout(d._t); d._t = setTimeout(() => { d.style.display = 'none'; }, 9000);
  }
  async function natural(text, v) {
    const g = ++gen; if (synth) synth.cancel(); if (audio) { try { audio.pause(); } catch (_) {} }
    const parts = chunks(text); if (!parts.length) return;
    let prev = Promise.resolve(); const jobs = parts.map(p => (prev = prev.catch(() => {}).then(() => g === gen ? wav(p, v) : null)));
    let first;
    try { first = await Promise.race([jobs[0], new Promise((_, rej) => setTimeout(() => rej(Error('slow')), 9000))]); }
    catch (e) {
      if (g !== gen) return;
      basic(text); return;   // model still loading or unavailable: speak with the instant voice this time
    }
    (window.__spk = true, B.classList.add('speaking'));
    for (let i = 0; i < jobs.length; i++) {
      let url; try { url = i === 0 ? first : await jobs[i]; } catch (_) { break; }
      if (g !== gen || !url) break;
      await new Promise(res => { audio = new Audio(url); audio.onended = audio.onerror = res; audio.play().catch(res); });
      URL.revokeObjectURL(url);
    }
    if (g === gen) (window.__spk = false, B.classList.remove('speaking'));
  }
  window.__jarvisSay = t => say(t);
  window.__jarvisStop = () => stopAll();
  const say = t => { const c = clean(t); if (!c) return; window.__lastSaid = c; const k = kind(); (k === 'basic' ? basic(c) : natural(c, k)); };
  const orig = window.fetch;
  window.fetch = (r, o) => {
    const u = typeof r === 'string' ? r : (r && r.url) || '';
    if (o && o.method === 'POST' && u.includes('/api/voice') && typeof o.body === 'string') {
      try { const b = JSON.parse(o.body);
        if (b.action === 'speak') { say(b.text); return Promise.resolve(new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}})); }
        if (b.action === 'stop') stopAll();
      } catch (_) {}
    }
    return orig(r, o);
  };
  const bar = document.getElementById('holobar'); if (bar) {
    const t = document.createElement('div'); t.className = 'tog'; t.innerHTML = '<span>Voice</span><b>Jarvis III</b>'; bar.append(t);
  }
})();

/* ===== Greeting when the app opens (once per launch), after the natural voice has loaded ===== */
(() => {
  'use strict';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function greet() {
    try { if (sessionStorage.getItem('jarvisGreeted')) return; sessionStorage.setItem('jarvisGreeted', '1'); } catch (_) {}
    await sleep(1500);
    for (let i = 0; i < 80; i++) {          // wait up to ~40 s for Kokoro to finish loading, so the greeting uses the natural voice
      try { const r = await fetch('/api/tts_status'); const s = await r.json(); if (!s.possible || s.ready) break; } catch (_) { break; }
      await sleep(500);
    }
    try { await window.afnica.send('briefing'); } catch (_) {}
  }
  addEventListener('load', greet);
})();

/* ===== Iron Man HUD layer: rotating tick rings, radar sweep, target brackets and live readouts around the reactor ===== */
(() => {
  'use strict';
  const cv = document.createElement('canvas'); cv.id = 'ironhud'; document.body.prepend(cv);
  const ctx = cv.getContext('2d'), TAU = Math.PI * 2, C = '95,233,255', O = '255,157,60';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W = 0, H = 0, cx = 0, cy = 0, R = 0, dpr = 1, act = 0;
  const t0 = performance.now();
  function resize() {
    dpr = Math.min(devicePixelRatio || 1, 2); W = innerWidth; H = innerHeight;
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cx = W * .7; cy = H * .44; R = Math.max(120, Math.min(H * .295, W * .2));
  }
  const arc = (r, a0, a1, w, col, al) => { ctx.strokeStyle = `rgba(${col},${al})`; ctx.lineWidth = w; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1); ctx.stroke(); };
  function ticks(r, n, len, rot, al, every) {
    ctx.strokeStyle = `rgba(${C},${al})`; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i < n; i++) { const a = rot + i * TAU / n, l = (i % every === 0) ? len * 1.9 : len;
      ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.lineTo(cx + Math.cos(a) * (r + l), cy + Math.sin(a) * (r + l)); }
    ctx.stroke();
  }
  function bracket(x, y, s, dx, dy) { ctx.beginPath(); ctx.moveTo(x, y + dy * s); ctx.lineTo(x, y); ctx.lineTo(x + dx * s, y); ctx.stroke(); }
  function frame(now) {
    const t = reduce ? 0 : (now - t0) / 1000, B = document.body.classList;
    act += (((B.contains('speaking') || B.contains('listening')) ? 1 : 0) - act) * .08;
    ctx.clearRect(0, 0, W, H);
    ctx.save(); ctx.shadowColor = `rgba(${C},.9)`; ctx.shadowBlur = 8;
    // outer tick ring, slow clockwise
    ticks(R * 1.36, 120, 5, t * .05, .45, 10);
    // segmented arcs, counter-rotating
    for (let i = 0; i < 4; i++) { const a = -t * .18 + i * TAU / 4; arc(R * 1.3, a, a + .9, 2, C, .55 + act * .3); }
    for (let i = 0; i < 6; i++) { const a = t * .3 + i * TAU / 6; arc(R * 1.22, a, a + .32, 3, C, .35); }
    // orange accent segments (the Iron Man warm accent)
    arc(R * 1.3, t * .4, t * .4 + .22, 3, O, .9); arc(R * 1.3, t * .4 + Math.PI, t * .4 + Math.PI + .22, 3, O, .9);
    // inner tick ring
    ticks(R * .8, 90, 3, -t * .12, .3, 9);
    // radar sweep
    const sw = t * .9, g = ctx.createConicGradient ? ctx.createConicGradient(sw, cx, cy) : null;
    if (g) { g.addColorStop(0, `rgba(${C},${.16 + act * .12})`); g.addColorStop(.09, `rgba(${C},0)`); g.addColorStop(1, `rgba(${C},0)`); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 1.18, 0, TAU); ctx.fill(); }
    ctx.shadowBlur = 0;
    // target brackets around the reactor
    ctx.strokeStyle = `rgba(${C},.7)`; ctx.lineWidth = 2; const b = R * 1.45, s = 26;
    bracket(cx - b, cy - b, s, 1, 1); bracket(cx + b, cy - b, s, -1, 1); bracket(cx - b, cy + b, s, 1, -1); bracket(cx + b, cy + b, s, -1, -1);
    // readouts
    ctx.font = `10px Consolas,"Courier New",monospace`; ctx.fillStyle = `rgba(${C},.75)`; ctx.textBaseline = 'middle';
    const wob = (a, f) => (a + Math.sin(t * f) * .5 + .5 * Math.sin(t * f * 2.3)).toFixed(1);
    ctx.textAlign = 'right'; const lx = cx - b - 14, ly = cy - R * .6;
    [['CORE', wob(98, .7) + ' %'], ['POWER', wob(87, .5) + ' %'], ['LINK', 'SECURE'], ['LATENCY', wob(12, 1.1) + ' MS']].forEach((r, i) => {
      ctx.fillStyle = `rgba(${C},.5)`; ctx.fillText(r[0], lx - 64, ly + i * 20); ctx.fillStyle = `rgba(${O},.95)`; ctx.fillText(r[1], lx, ly + i * 20); });
    [['SYS', 'ONLINE'], ['MIC', B.contains('muted') ? 'MUTED' : 'ACTIVE'], ['VOICE', 'JARVIS III'], ['AFNICA', 'LOCAL']].forEach((r, i) => {
      ctx.fillStyle = `rgba(${C},.5)`; ctx.fillText(r[0], lx - 64, ly + 100 + i * 20); ctx.fillStyle = `rgba(${C},.95)`; ctx.fillText(r[1], lx, ly + 100 + i * 20); });
    ctx.restore();
    requestAnimationFrame(frame);
  }
  addEventListener('resize', resize); resize(); requestAnimationFrame(frame);
})();


/* ===== Spotify player inside this window (Web Playback SDK): the Jarvis window itself becomes a Spotify player, so playback never depends on the desktop app ===== */
(() => {
  'use strict';
  const B = document.body, note = m => { const n = document.getElementById('notice'); if (!n) return; n.textContent = m; n.style.display = 'block'; setTimeout(() => n.style.display = 'none', 9000); };
  let player = null, tried = false;
  async function token() { const r = await fetch('/api/spotify_token'); if (!r.ok) throw Error('no token'); return (await r.json()).token; }
  async function start() {
    if (tried) return; tried = true;
    try { await token(); } catch (_) { tried = false; return; }      // Spotify not connected yet: nothing to do
    window.onSpotifyWebPlaybackSDKReady = () => {
      player = new Spotify.Player({name: 'Jarvis AFNICA', volume: .8, getOAuthToken: cb => token().then(cb).catch(() => {})});
      player.addListener('ready', ({device_id}) => fetch('/api/spotify_device', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({device_id})}).catch(() => {}));
      let lastId = '', kick = 0;
      player.addListener('player_state_changed', st => {
        window.__musicPlaying = !!st && !st.paused; B.classList.toggle('music', window.__musicPlaying);
        const id = st && st.track_window && st.track_window.current_track && st.track_window.current_track.id;
        if (id && id !== lastId) { lastId = id; clearTimeout(kick); kick = setTimeout(() => { player.getCurrentState().then(cur => { if (cur && cur.paused && cur.position < 1500) player.resume().catch(() => {}); }); }, 1200); }   // a new song loaded but the browser held it paused: press play for it
      });
      player.addListener('playback_error', e => note('Spotify: ' + ((e && e.message) || 'redarea a eșuat') + '. Dacă se repetă, Chrome nu poate reda audio protejat (Widevine).'));
      addEventListener('pointerdown', () => { try { player.activateElement(); } catch (_) {} }, {once: true});
      player.addListener('authentication_error', () => note('Spotify: permisiunile s-au schimbat. Spune „connect spotify” și autorizează din nou.'));
      player.addListener('account_error', () => note('Spotify: contul are nevoie de Premium pentru redare.'));
      player.addListener('initialization_error', () => note('Spotify: playerul nu poate porni în această fereastră (Widevine lipsește).'));
      player.connect();
    };
    const sc = document.createElement('script'); sc.src = 'https://sdk.scdn.co/spotify-player.js'; sc.async = true; document.head.append(sc);
  }
  addEventListener('load', () => setTimeout(start, 1500));
  setInterval(() => { if (!tried) start(); }, 20000);   // picks it up after "connect spotify" without reopening the app
  window.__spotifyPlayer = () => player;
})();


// ---- AFNICA Aquarium development card: version, changes, commits and backlog, all read locally ----
(() => {
  const token = document.querySelector('meta[name="jarvis-session"]').content, $ = id => document.getElementById(id);
  const card = $('aqcard'), sel = $('module'); if (!card || !sel) return;
  const put = (id, text) => { $(id).textContent = text; };
  const ago = t => { const a = Math.max(0, Math.round(Date.now() / 1000 - t)); return a < 90 ? 'just now' : a < 5400 ? Math.round(a / 60) + ' min ago' : a < 172800 ? Math.round(a / 3600) + ' h ago' : Math.round(a / 86400) + ' days ago'; };
  const fill = (id, rows) => { const ul = $(id); ul.textContent = ''; (rows.length ? rows : ['—']).forEach(r => { const li = document.createElement('li'); li.textContent = r; ul.append(li); }); };
  async function refresh() {
    const on = sel.value === 'game'; card.hidden = !on; if (!on) return;
    try {
      const d = await (await fetch('/api/aquarium', { headers: { 'X-Jarvis-Token': token } })).json();
      $('aq-empty').hidden = !!d.game_found; $('aq-body').hidden = !d.game_found; if (!d.game_found) return;
      put('aq-level', d.version || ''); put('aq-ver', d.version_name || '');
      $('aq-xp').style.width = (d.percent || 0) + '%'; put('aq-xptext', d.percent == null ? 'Backlog empty. In this context say: task: <title>' : 'BACKLOG ' + d.percent + '% complete');
      const git = d.git || { count: 0, recent: [] }, grid = $('aq-grid'); grid.textContent = '';
      [['VERSIONS', d.version_count], ['COMMITS', git.count], ['LAST EDIT', ago(d.edited)], ['OPEN', d.counts.open], ['DONE', d.counts.done], ['LAST COMMIT', git.recent[0] ? ago(git.recent[0].time) : '—']].forEach(([k, v]) => {
        const cell = document.createElement('div'), b = document.createElement('b'); b.textContent = v ?? 0; cell.append(b, k); grid.append(cell); });
      fill('aq-log', (d.milestones || []).map(m => m.v + ' — ' + m.text));
      fill('aq-git', git.recent.map(c => ago(c.time) + ' — ' + c.text));
      fill('aq-todo', d.tasks_open.map(t => '#' + t.id + ' ' + t.title));
      put('aq-age', 'Read locally from the game folder · refreshes every 10 s');
    } catch (_) {}
  }
  sel.addEventListener('change', refresh); refresh(); setInterval(refresh, 10000);
})();


// ---- YouTube channel card (context: YouTube). The server caches the API answer for five minutes. ----
(() => {
  const token = document.querySelector('meta[name="jarvis-session"]').content, $ = id => document.getElementById(id);
  const card = $('ytcard'), sel = $('module'); if (!card || !sel) return;
  const put = (id, t) => { $(id).textContent = t; };
  const n = v => Number(v || 0).toLocaleString('en-US');
  async function refresh() {
    const on = sel.value === 'youtube'; card.hidden = !on; if (!on) return;
    try {
      const d = await (await fetch('/api/youtube', { headers: { 'X-Jarvis-Token': token } })).json();
      $('yt-empty').hidden = !!d.connected; $('yt-body').hidden = !d.connected;
      if (!d.connected) { put('yt-empty', d.message || 'YouTube is not connected.'); return; }
      put('yt-title', d.title); put('yt-sub', d.subs_hidden ? 'subscribers hidden' : n(d.subscribers) + ' subscribers');
      const l = d.last28, grid = $('yt-grid'); grid.textContent = '';
      [['SUBSCRIBERS', d.subs_hidden ? '—' : n(d.subscribers)], ['TOTAL VIEWS', n(d.views)], ['VIDEOS', n(d.videos)],
       ['VIEWS · 28D', l ? n(l.views) : '—'], ['HOURS · 28D', l ? n(l.hours) : '—'], ['SUBS · 28D', l ? '+' + l.gained + ' / -' + l.lost : '—']].forEach(([k, v]) => {
        const cell = document.createElement('div'), b = document.createElement('b'); b.textContent = v; cell.append(b, k); grid.append(cell); });
      put('yt-28', l ? 'Average view ' + Math.floor(l.avg_seconds / 60) + ':' + String(l.avg_seconds % 60).padStart(2, '0') : 'Last-28-days analytics not available');
      const ul = $('yt-videos'); ul.textContent = '';
      (d.recent.length ? d.recent : [{ title: '—', published: '', views: 0 }]).forEach(v => { const li = document.createElement('li'); li.textContent = v.published + ' · ' + v.title + ' — ' + n(v.views) + ' views, ' + n(v.likes) + ' likes'; ul.append(li); });
      const a = Math.max(0, Math.round(Date.now() / 1000 - d.updated)); put('yt-age', 'Updated ' + (a < 90 ? 'just now' : Math.round(a / 60) + ' min ago') + ' · refreshes every 5 min');
    } catch (_) { put('yt-empty', 'Could not read YouTube status.'); $('yt-empty').hidden = false; }
  }
  sel.addEventListener('change', refresh); refresh(); setInterval(refresh, 60000);
})();
