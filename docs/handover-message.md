# Draft message to Connell

Two versions. The email is the main one; the WhatsApp version is for sending the
links first and letting the document do the talking.

---

## Email / long version

**Subject:** CREA — it's working, and it's a lot cheaper than we thought

Hey Connell,

I've built the core of CREA and it's running. You can talk to it and it talks
back, it holds your whole job pipeline, and it answers real questions about it.
Ask it "what have I got on this week and how much am I owed" and it tells you,
out loud.

Two things changed from the August plan, both in your favour.

**It costs almost nothing to run.** The original plan budgeted $25–100 a month
for the voice and the AI. Neither turned out to be necessary. The voice runs
entirely on the machine, no account and no per-word cost, and the thinking is
routed through free model tiers. Realistically **$0–15 a month** instead. I
measured all of this on a 2020 MacBook rather than estimating it, and
deliberately on a slower machine than the one you'll actually use.

**Your WhatsApp number stays your number.** The obvious way to read WhatsApp
would have meant that number could no longer use the normal app and your chat
history gets wiped. Not worth it for a business that books over WhatsApp. There's
a second way that pairs by QR code like WhatsApp Web, and everything stays as it
is. There's one caveat on it in the manual worth reading.

Here's everything:

**The manual** — the whole build, what it costs, what it does, and how to set it up
https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6

**The interface** — click the orange circle and it talks to you
https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e

**The code** — everything, open, yours
https://github.com/skw-fuj/crea

Two things to know before you look at that middle link. The **voice you hear is
real** — that's CREA, generated on the machine, no subscription. But **every job,
client and dollar figure on those screens is made up.** Aisha Rahman doesn't
exist, the $7,170 isn't real. It's test data so the thing has something to run
against before your accounts are plugged in. And the layout itself is a proposal,
not a decision. If a screen is missing something you'd actually use, or something
on it is useless to you, now is the cheap time to say so.

Setup is one line. You plug the Mac Mini in, open Terminal, paste one command,
and walk away for twenty minutes. It installs everything itself and asks you
three yes/no questions near the end. There's nothing to gather beforehand.

**What I need from you:**

1. **Order the Mac Mini, and get 16GB of memory.** This is the only spec that
   matters. 8GB genuinely isn't enough and it'll feel sluggish in a way you'll
   notice every day. Refurbished M1 is fine if it's 16GB, otherwise the base M4.
2. **Have a listen to the voice** and tell me if it suits you. There's a paid
   voice that sounds better if you want it later, but I'd start free and see if
   you ever miss it.
3. **Have a look at the screens** and tell me what you'd change.
4. **Decide on WhatsApp** — your existing number, or a second SIM just for CREA.
   Section 4 of the manual has what you need to choose.

One last thing: it's pronounced **kree-ah**, not "cray". That matters more than
it sounds like it should, because the speech recognition is tuned for it.

Once the Mini turns up, everything I've built moves onto it as-is and we can have
your bookings flowing in the same week.

Tris

---

## WhatsApp / short version

> Hey mate, CREA's core is built and running. You can talk to it and it answers
> out loud about your jobs.
>
> Two bits of good news: it's about **$0–15/month** to run instead of the $25–100
> we planned, and your **WhatsApp number stays exactly as it is** (no migration,
> no losing your chats).
>
> Manual: https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6
> Interface (tap the orange circle, it talks): https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e
> Code: https://github.com/skw-fuj/crea
>
> The voice on that second link is real. All the jobs and dollar figures on it are
> made up test data, and the layout's a proposal — tell me what you'd change.
>
> Main thing I need: **order the Mac Mini with 16GB.** Not 8. It's the one spec
> that matters. Everything else waits on that.
>
> (It's pronounced kree-ah, not cray 😄)

---

## Before sending

- [ ] Open **each** artifact link → Share → enable link sharing. They are private
      by default and he will hit a permission wall otherwise.
- [ ] Check both links in a private/incognito window to confirm they open.
- [ ] Decide whether to mention pricing for the build itself — this draft
      deliberately does not.
