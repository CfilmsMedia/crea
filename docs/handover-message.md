# Draft message to Connell

Updated after the full build. Email is the main version; the WhatsApp one is for
sending the links and letting the manual do the talking.

---

## Email / long version

**Subject:** CREA is built

Hey Connell,

CREA's done. Not the core — the whole thing. Every skill in the plan you sent me
in August exists and works.

It talks and it listens. Ask it what you've got on this week, or how much you're
owed, and it tells you out loud. Say "the card's in" and it copies the card,
splits it into separate shoots by working out where the gaps between shots are,
and checks every single file copied properly before it'll tell you the card is
safe to wipe. Say "I spent ninety-two on fuel" and it files it under fuel without
being told. Ask it what you should focus on and it gives you three things, most
urgent first.

Nineteen skills all up. Fourteen of them work the moment it's installed, with no
accounts connected at all. Ten of them run on their own schedule — the briefing
before you're up at half six, Acuity checked every fifteen minutes, WhatsApp
every ten, tomorrow's shoots confirmed at five, invoicing Monday mornings.

Two things changed from the August plan, both in your favour.

**It costs almost nothing to run.** The original plan budgeted $25–100 a month
for the voice and the AI. Neither turned out to be necessary. The voice runs
entirely on the machine, no account and no per-word cost, and the thinking goes
through free model tiers. Realistically **$0–15 a month**. I measured that on a
2020 MacBook, deliberately a slower machine than the one you'll use.

**Your WhatsApp number stays your number.** The obvious way to read WhatsApp
would have meant that number could no longer use the normal app and your chat
history gets wiped. Not worth it for a business that books over WhatsApp. There's
a second way that pairs by QR code like WhatsApp Web, and everything stays as it
is. One caveat on it in the manual worth reading.

Here's everything:

**The manual** — what it does, what it costs, how to set it up
https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6

**The interface** — click the orange circle and it talks to you
https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e

**The code** — everything, open, yours
https://github.com/skw-fuj/crea

Two things before you look at that middle link. The **voice you hear is real** —
that's CREA, generated on the machine, no subscription. But **every job, client
and dollar figure on those screens is made up.** Aisha Rahman doesn't exist, the
$7,170 isn't real. It's test data so the thing has something to run against
before your accounts are plugged in. And the layout is a proposal, not a
decision. If a screen is missing something you'd use, or something on it is
useless to you, now is the cheap time to say so.

**Setting it up is one line.** You plug the Mac Mini in, open Terminal, paste one
command, and walk away for twenty minutes. It installs everything itself — the
speech models, the voice, the scheduler, the lot. Then it asks about five
accounts: Acuity, Google, WhatsApp, Higgsfield and Apify. For each one it opens
the right page in your browser, you paste the key, and it checks the key actually
works before saving it. You can skip any of them and do it later. Nothing to
gather beforehand.

Your keys go into one locked file on your own Mac. Not in the settings file,
never uploaded, and I never see them.

**What I need from you:**

1. **Order the Mac Mini, and get 16GB of memory.** This is the only spec that
   matters. 8GB genuinely isn't enough and it'll feel sluggish in a way you'll
   notice every day. Refurbished M1 is fine if it's 16GB, otherwise the base M4.
2. **Have a listen to the voice** and tell me if it suits you. There's a paid
   voice that sounds better if you want it later, but I'd start free and see if
   you ever miss it.
3. **Have a look at the screens** and tell me what you'd change.
4. **Decide on WhatsApp** — your existing number, or a second SIM just for CREA.
   Section 9 of the manual has what you need to choose.

One last thing: it's pronounced **kree-ah**, not "cray". That matters more than
it sounds like it should, because the speech recognition is tuned for it.

Once the Mini turns up it's about twenty minutes to a working system.

Tris

---

## WhatsApp / short version

> Hey mate, CREA's done — not just the core, the whole thing. Nineteen skills,
> all of it working.
>
> It listens and talks back. Plug an SD card in and it sorts the shoot, splits it
> by the gaps between shots, and checks every file before it'll say the card's
> safe to wipe. Tell it what you spent and it files it. Ask what to focus on and
> it tells you.
>
> Two bits of good news: it's about **$0–15/month** instead of the $25–100 we
> planned, and your **WhatsApp number stays exactly as it is** — no migration, no
> losing your chats.
>
> Manual: https://claude.ai/code/artifact/6d9a6d2f-3a0f-4358-b866-e2141be5bdb6
> Interface (tap the orange circle, it talks): https://claude.ai/code/artifact/c36157f1-2dba-4de3-84b1-9f005d70653e
> Code: https://github.com/skw-fuj/crea
>
> The voice on that second link is real. All the jobs and dollar figures on it are
> made-up test data, and the layout's a proposal — tell me what you'd change.
>
> Setup is one line in Terminal and twenty minutes. It opens each account page for
> you and checks the keys work.
>
> Main thing I need: **order the Mac Mini with 16GB.** Not 8. It's the one spec
> that matters.
>
> (It's pronounced kree-ah, not cray 😄)

---

## Before sending

- [x] Both artifact links set to anyone-with-the-link — verified in an
      unauthenticated browser, both render.
- [x] GitHub repo public — verified unauthenticated.
- [ ] Decide whether to raise pricing for the build. This draft deliberately
      does not.
