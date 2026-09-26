# Local conversational AI

## Start

Close an older JARVIS session, then run Start-Jarvis-HOLO.cmd from this complete
folder. Start-Jarvis.cmd opens the native desktop; Start-Jarvis.cmd --cli uses the
terminal. Both now enable the model. Use --no-llm for command-only diagnostics.
The existing Python launcher and local Daniel voice remain unchanged.

Ask an ordinary question in Romanian or English. The system prompt requests English
answers, formal British-style phrasing and "sir". The first question loads the model;
subsequent questions reuse it. HOLO shows the model state and Thinking locally.
Desktop conversation runs in a worker thread so widgets and reminders stay responsive.

## What it is

An existing pretrained Qwen2.5-1.5B-Instruct model, not a model trained from scratch.
Q4_K_M GGUF with llama.cpp b10786, Windows x64 CPU. Files, provenance hashes and
upstream licences are under llm/. Keep that directory with the application.
The runtime binds only to 127.0.0.1 on a private port and requires a random session
API key. Offline mode is enabled; its web UI, agent mode and MCP proxy are disabled.
No prompts or voice recordings are uploaded by this adapter.

## Memory and control

SQLite retains messages. Each model request includes up to six recent messages
from the selected module (among the latest 100 overall), four saved notes and four
open tasks from that module. Entries are shortened to bound context. This is limited
context retrieval, not training or unlimited recall; choose the appropriate module.
Use remember: for durable notes. Deleting a note does not erase conversation history.

Only explicit commands change data: task:, reminder:, done:, remember:, forget:.
Model output is displayed and optionally spoken, never dispatched as a command.
It cannot run code, improve itself, synchronise accounts or execute plans.
Google, Gmail, YouTube, ChatGPT account history and Telegram remain unconnected.

## Limits and troubleshooting

The compact 1.5B model was selected for the RAM available on this PC. It may make
factual mistakes, occasionally miss style/language instructions, and is substantially
less capable than large online assistants. Verify consequential advice.
It uses four CPU threads, a 4096-token context and a 320-token reply limit.
Conversational inputs are limited to 3500 characters; long context can still exceed
the model limit. Ask a shorter question if that occurs.
Generation has a 120-second timeout; loading has a 90-second timeout.
Close unused applications if loading fails. Explicit commands continue working.
Closing the HOLO browser does not stop its Python server: use Ctrl+C in the server
window to unload the model. Normal desktop exit also unloads it.

No microphone hardware or wake-word accuracy is guaranteed by automated tests.
Voice input still requires review before submission; enable spoken replies to hear Daniel.
Old ZIP packages do not contain this update; use the complete folder on this PC.

## Verified on this PC

66 automated tests pass. A live Romanian question received an English two-step
answer (18.2 seconds including initial load); a follow-up recalled a saved aquarium
name (2.1 seconds). Generated advice created no tasks. Unauthenticated access to
the model API was rejected. These timings are examples, not a speed guarantee.
An earlier live test ignored the language preference; the application now repeats
the English-only instruction on each turn. Small-model compliance is still imperfect.

## Architecture

UI → Core → explicit command handlers OR LocalModel → private llama.cpp server.
Core persists the user input and returned text. LocalModel reads bounded module
context and the personality profile. No generated text is recursively routed.
The LanguageModel protocol remains replaceable for future larger local models.
