# Handover message to Connell — v1.1 (final)

Email version below; short version after.

---

## Email

**Subject:** CREA is ready — here's everything to run it

Hey Connell,

CREA's finished. Every skill from the plan you sent me in August is built and
working. Here's everything you need.

---

**THE THREE LINKS**

Manual — what it does, what it costs, how to set it up
https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6

Interface — click the orange circle and it talks to you
https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e

Code — all of it, open, yours
https://github.com/skw-fuj/crea

---

**TO INSTALL — one line**

Plug the Mac Mini in, finish Apple's normal setup, open **Terminal**
(press ⌘ Space, type "terminal", hit Enter), and paste this:

```
curl -fsSL https://raw.githubusercontent.com/skw-fuj/crea/main/install.sh | bash
```

Then walk away for about twenty minutes. It installs everything itself. Safe to
run again any time — it leaves alone whatever's already there.

---

**THE FIVE ACCOUNTS**

Near the end it asks about these. It opens each page in your browser for you, you
paste the key, and it checks the key actually works before saving it. Skip any of
them and add them later with `crea connect`.

| Account | Where exactly | What you copy |
|---|---|---|
| Acuity | Left sidebar → Business Settings → Integrations → API → view credentials | User ID (the numeric one) and API Key |
| Google | console.cloud.google.com → APIs & Services → Credentials → Create credentials → OAuth client ID → Desktop app | Client ID + secret, then click Allow |
| WhatsApp | Your phone: WhatsApp → Settings → Linked Devices → Link a Device | Nothing — you scan a QR code |
| Higgsfield | Your account settings | API key |
| Apify | console.apify.com → Settings → Integrations | Personal API token |

Your keys go into one locked file on your own Mac. Not in the settings file,
never uploaded, and I never see them.

---

**COMMANDS YOU'LL ACTUALLY USE**

```
crea skills                     everything it can do, and what each needs
crea status                     honest health of every part
crea connect                    add an account you skipped

crea ask "how much am I owed?"  ask by typing instead of talking
crea card                       import a plugged-in SD card
crea jobs                       the pipeline
crea board                      what deserves attention today
crea brief                      today's briefing, spoken

crea enrol                      teach it your voice
crea voice-check on             then it only answers you
```

Or just talk to it: **"Hey CREA, what have I got on today?"**

---

**WHAT'S RUNNING UNDERNEATH**

All installed for you. Listed so nothing's a mystery.

- **hermes** — runs the skills and the schedule
- **n8n** — the visual connections out to Acuity, Google and WhatsApp
- **whisper.cpp** — turns your speech into text, on the machine
- **Pocket TTS** — CREA's voice, on the machine, 26 voices to pick from
- **ffmpeg / exiftool** — Reels, and reading shot times off your files
- **Obsidian** — where you read and edit your own job vault
- **crea** — the command that drives all of it

Acuity, Google, Higgsfield and Apify are reached over their normal web APIs.
WhatsApp connects the way WhatsApp Web does. Nothing exotic, nothing you're
locked into.

---

**A FEW THINGS THAT CAME OUT OF TESTING**

These are in version 1.1 because they only turn up once something actually runs
on a machine that has to stay up for months.

**It can learn your voice.** By default CREA answers anyone who says its name.
`crea enrol` takes about a minute and after that it only answers you. It's off
unless you turn it on — worth leaving off if an assistant or your editor should
be able to ask it things too.

**It keeps the Mac awake.** An always-on assistant that goes to sleep isn't
always on. It handles that itself without changing your own power settings.

**The clock follows daylight saving.** Everything runs on Sydney time properly,
rather than trusting whatever timezone got picked during first-time setup. If
that were wrong your morning brief would fire at the wrong hour and invoices
would be dated a day out — and it wouldn't look like a clock problem.

**Section 13 covers using it from your phone** — three ways, two of them free,
and an honest answer on whether the paid option is worth it. Don't decide on day
one; give it a fortnight first.

**Section 14 covers what to do when something breaks** — the five things that
catch every setup like this, and which ones are already handled.

---

**TWO THINGS BEFORE YOU LOOK**

The **voice is real** — that's CREA, generated on the machine, no subscription.

But **every job, client and dollar figure on those screens is made up.** Aisha
Rahman doesn't exist, the $7,170 isn't real. It's test data so the thing has
something to run against before your accounts are connected. The layout is a
proposal too — if a screen's missing something you'd use, or something on it is
useless to you, now's the cheap time to say so.

---

**WHAT IT COSTS**

$0–15 a month, against the $25–100 the original plan budgeted. The voice runs on
the machine and the thinking goes through free tiers. I measured that on a 2020
MacBook, deliberately slower than what you'll be using.

---

**WHAT I NEED FROM YOU**

1. **Order the Mac Mini — 16GB of memory.** This is the only spec that matters.
   8GB genuinely isn't enough and you'd notice it daily. Refurbished M1 is fine
   if it's 16GB, otherwise the base M4.
2. **Listen to the voice** and tell me if it suits you. There are 26 built in, so
   if that one grates we just change it.
3. **Look at the screens** and tell me what you'd change.
4. **Decide on WhatsApp** — your existing number, or a second SIM for CREA. The
   manual has what you need to choose.

One last thing: it's pronounced **kree-ah**, not "cray". Matters more than it
sounds like, because the speech recognition is tuned for it.

Once the Mini turns up it's about twenty minutes to a working system.

Tris

---

## WhatsApp / short version

> Hey mate, CREA's done — everything from the August plan, built and working.
>
> Manual: https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6
> Interface (tap the orange circle, it talks): https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e
> Code: https://github.com/skw-fuj/crea
>
> To install: plug the Mini in, open Terminal, paste this one line, walk away for
> twenty minutes —
>
> `curl -fsSL https://raw.githubusercontent.com/skw-fuj/crea/main/install.sh | bash`
>
> It installs the lot, then asks about five accounts (Acuity, Google, WhatsApp,
> Higgsfield, Apify). It opens each page for you and checks the keys work. Skip
> any and add them later.
>
> Then just talk to it: "Hey CREA, what have I got on today?"
>
> It can also learn your voice so it only answers you, it keeps the Mac from
> sleeping, and there are 26 voices if the default one grates.
>
> About $0–15/month instead of the $25–100 we planned, and your WhatsApp number
> stays exactly as it is.
>
> Heads up: the voice on that second link is real, but all the jobs and dollar
> figures are made-up test data, and the layout's a proposal — tell me what you'd
> change.
>
> Main thing: **order the Mini with 16GB.** Not 8. It's the one spec that matters.
>
> (Pronounced kree-ah, not cray 😄)

---

## Before sending

- [x] Both artifact links set to anyone-with-the-link — verified unauthenticated
- [x] GitHub repo public — verified unauthenticated
- [x] Manual and shell both stamped v1.1
- [ ] Decide whether to raise pricing for the build. This draft deliberately does not.
