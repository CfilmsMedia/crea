# CREA — Build Manual

**Cfilms Real Estate Adviser.** Prepared for Connell Saputra.
Supersedes the plan of 17 August 2026.

A presentation copy of this document lives at
<https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6>.
**This file is the source of truth** — it sits beside `install.sh`, so it cannot
drift from what the installer actually does.

---

## 1. Setup — one line

Take the Mac Mini out of the box, plug it in, and go through Apple's normal
first-time setup. Then open **Terminal** (press `⌘ Space`, type "terminal",
press Enter) and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/skw-fuj/crea/main/install.sh | bash
```

Walk away for about twenty minutes. It installs:

| It installs | Which gives you |
|---|---|
| Homebrew, Node, uv, ffmpeg, ExifTool | The groundwork everything sits on |
| CREA itself, from GitHub | The assistant. Re-run the line to update it. |
| whisper.cpp + speech model | CREA hearing you, on-device |
| Pocket TTS + voice model | CREA talking back, on-device |
| Hermes, routed to a free model tier | The thinking, at no cost |
| n8n | Connections to Acuity, Google and WhatsApp |
| Obsidian + your job vault | The memory, readable by you directly |
| Background services | CREA starting itself on boot, forever |
| The `crea` command | Everything controllable in one word |

Near the end it asks about three accounts — WhatsApp, Acuity, Google. Each is a
yes/no and each is optional; `crea connect` adds them later. Say no to all three
and CREA still installs and still talks to you.

**Safe to re-run.** Anything already installed is left alone, and your settings
file is never overwritten.

## 2. The moment it finishes

CREA is already listening and already restarts on reboot. Try:

```bash
# say it out loud
"Hey CREA — what have I got on this week?"

# or type it
crea ask "how much am I owed?"
crea status          # honest health of every component
crea connect         # add an account you skipped
```

Open Obsidian and your job vault is there — every shoot, client and note as a
plain document you can read and edit. Change something and CREA knows immediately.

## 3. The screens

Seven panels, mapping onto the four skill groups in your plan:

| Screen | Covers |
|---|---|
| **Home** | Voice, today's shoot, live status |
| **Jobs** | Booking & client management — pipeline, Acuity sync, invoicing |
| **Media** | The media pipeline — card → Drive → Higgsfield → editor |
| **Clients** | Growth — client check-ins, lead tracking |
| **Calendar** | Bookings from Acuity, calls and WhatsApp in one place |
| **Board** | The daily agent board — growth and strategy |
| **Personal** | Daily briefing, reminders, expenses, uni notes |

Live mockup with the real voice:
<https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e>

## 4. What runs, measured

Benchmarked on an Apple M1 / 8 GB — deliberately the worst machine this will
ever run on. Your Mac Mini will be faster.

| | |
|---|---|
| Voice generation | **2.4× realtime** (warm median) |
| Thinking response | **8.6s** on the free tier |
| Voice cost | **$0** — runs offline on the machine |
| Running cost | **$0–15/mo** (vs $25–100 originally quoted) |

## 5. Hardware

**16 GB of memory is the floor.** This is the one specification that decides
whether CREA feels instant or frustrating — 8 GB genuinely is not enough to hold
the voice model and everything else at once. The installer warns you if it finds
less than 16 GB.

- Refurbished M1 Mac Mini — fine, *if* it's 16 GB
- New base M4 Mac Mini — the safer buy

## 6. WhatsApp

`hermes whatsapp` pairs by QR code, like WhatsApp Web. **Your number stays a
normal WhatsApp number** — no migration, no lost chat history.

The alternative (Meta's official Business API) would mean that number could no
longer use the normal WhatsApp app, local history is deleted, and messages can be
held up to a month. Not worth it for a business whose bookings arrive by WhatsApp.

*Honest caveat:* the QR method uses an unofficial connection library. Meta's terms
don't formally permit it and there's a small risk of a number being restricted.
Widely used, rarely a problem — but if you'd rather not, use a second SIM for CREA.

## 7. Call recording — the one legal condition

NSW requires **all parties** to consent. The Surveillance Devices Act 2007 has a
narrow "lawful interests" exception, but *"so I get the booking details right"* is
convenience, not protection — so that exception is not available. It also fails
where a recording is passed to non-parties, which is what any transcription
pipeline does.

That leaves consent, which is workable. CREA plays a spoken disclosure before
retaining any audio:

```jsonc
"require_disclosure": true,
"disclosure_text": "Just so you know, I record calls so I get the booking details right.",
"retain_audio": false,          // transcribe, then discard the recording
"abort_if_disclosure_fails": true
```

`retain_audio: false` means CREA keeps the date, time and address — not a library
of your clients' voices. `abort_if_disclosure_fails` means if the disclosure
doesn't play, nothing is recorded.

**This is not legal advice.** Have the wording checked by someone qualified before
switching it on. Every other capability you can enable at your own discretion.

## 8. The card pipeline

Detect the card, copy everything, split into shoots on a time gap, upload each to
Drive, push to Higgsfield, tell Narendra.

```jsonc
"shoot_gap_minutes": 90,     // a longer break = a new shoot
"verify_copies": true,
"format_card": "never"       // never | ask | auto
```

**CREA never formats a card.** Until Drive confirms, that card is the only copy of
a paid shoot. Every other failure costs an inconvenience; this one costs a job, a
client and a reputation. CREA verifies every copy and then *tells you* it's safe.
Once you've watched it get that right a dozen times, move it to `"ask"` — your
call to make later, not a default to inherit now.

## 9. Build order

| # | Phase | Time | Status |
|---|---|---|---|
| 1 | Core loop — voice, vault, brain | — | **Done** |
| 2 | "Hey CREA" wake word | ½ day | Built, untested |
| 3 | Acuity + calendar | ½ day | |
| 4 | Calls + WhatsApp | 2 days | |
| 5 | Card → Drive → Higgsfield | 2–4 days | |
| 6 | Job dashboard + invoicing | 1–2 days | |
| 7 | Phone access (iPhone Shortcut + Tailscale) | 2–3 days | |
| 8 | Daily briefing | ½ day | |
| 9 | Reminders + expenses | 1 day | |
| 10 | Uni notes | 1 day | |
| 11 | The daily board | 2–3 days | |

Full system, built steadily: **3–6 weeks part-time.**

## 10. Moving machines

Every setting specific to you lives in `crea.config.json`. Moving CREA to a
different Mac is copying that one file across.

---

*Status labels reflect what was verified at time of writing, not what is intended.
Performance figures measured on Apple M1 / 8 GB.*
