"""Money — invoicing, follow-ups, and expense tracking.

Two of Connell's skills live here: "Invoicing & follow-ups" from the business
group and "Expense & receipt tracking" from the personal group. They share a
concern, so they share a file.

Nothing here moves money. CREA drafts an invoice and drafts a reminder; a human
sends both. That boundary is deliberate and is not a placeholder for a future
version.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .base import Skill, SkillResult
from ..clock import now as _now


class Invoicing(Skill):
    """Generate invoices from completed jobs and chase what's overdue."""

    name = "invoice"
    title = "Invoicing and follow-ups"
    schedule = "0 9 * * 1"          # Monday morning
    phrases = ("send the invoices", "who owes me", "what's overdue")

    def run(self, job: str | None = None, **kw) -> SkillResult:
        jobs = self.vault.jobs()
        ready = [j for j in jobs if j.get("status") == "Editing"]
        sent = [j for j in jobs if j.get("status") == "Invoiced"]

        if job:
            ready = [j for j in ready if job.lower() in j["_title"].lower()]

        drafted = []
        for j in ready:
            path = self._draft(j)
            drafted.append({"job": j["_title"], "invoice": str(path),
                            "amount": j.get("fee")})

        # Anything invoiced and still unpaid after the terms window needs chasing
        terms = int(self.cfg.get("money.payment_terms_days", 14))
        overdue = []
        for j in sent:
            d = datetime.fromisoformat(j["shoot_at"])
            age = (_now(self.cfg) - d).days
            if age > terms:
                overdue.append({"job": j["_title"], "client": j.get("client"),
                                "amount": j.get("fee"), "days": age})

        owed = sum(j.get("fee") or 0 for j in sent)
        bits = []
        if drafted:
            bits.append(f"{len(drafted)} invoice(s) drafted")
        if overdue:
            worst = max(overdue, key=lambda o: o["days"])
            bits.append(f"{len(overdue)} overdue, oldest is {worst['client']} "
                        f"at {worst['days']} days (${worst['amount']:,.0f})")
        if not bits:
            bits.append(f"Nothing to invoice. ${owed:,.0f} still out.")

        if drafted:
            self.vault.log("invoice", f"{len(drafted)} drafted")

        return SkillResult(ok=True, changed=bool(drafted), summary=". ".join(bits) + ".",
                           drafted=drafted, overdue=overdue, outstanding=owed)

    def _draft(self, j: dict) -> Path:
        """Write the invoice into the vault as a plain document he can send."""
        d = datetime.fromisoformat(j["shoot_at"])
        num = f"CF-{d:%Y%m}-{abs(hash(j['_title'])) % 1000:03d}"
        folder = self.vault.root / "Invoices"
        folder.mkdir(exist_ok=True)
        p = folder / f"{num}.md"
        if p.exists():
            return p
        fee = j.get("fee") or 0
        client = self.vault.client(j.get("client", "")) or {}
        due = (_now(self.cfg) + timedelta(
            days=int(self.cfg.get("money.payment_terms_days", 14)))).date()
        p.write_text("\n".join([
            "---", "type: invoice", f"number: {num}", f"client: {j.get('client')}",
            f"amount: {fee}", f"issued: {_now(self.cfg).date()}", f"due: {due}",
            "status: draft", "tags: [\"cfilms/invoice\"]", "---", "",
            f"# Invoice {num}", "",
            f"**To** {j.get('client')}" + (f", {client.get('agency')}" if client.get("agency") else ""),
            f"**Email** {client.get('email') or '—'}", "",
            f"**For** {j.get('job_type') or 'Photography'} at {j.get('address')}",
            f"**Shot** {d:%d %B %Y}", "", "| Item | Amount |", "|---|---|",
            f"| {j.get('job_type') or 'Photography'} | ${fee:,.2f} |",
            f"| **Total** | **${fee:,.2f}** |", "",
            f"Payment due {due:%d %B %Y}.", "",
            "---", f"Job: [[{j['_title']}]] · client [[{j.get('client')}]]",
        ]))
        self.vault.set_status(j["_path"], "Invoiced")
        return p


class Expenses(Skill):
    """Log fuel, gear and uni costs as they come in, so tax time isn't archaeology."""

    name = "expense"
    title = "Expense and receipt tracking"
    phrases = ("log an expense", "i spent", "add a receipt")

    CATEGORIES = ("fuel", "gear", "software", "uni", "insurance", "travel", "other")

    def run(self, amount: float | None = None, what: str = "",
            category: str = "", **kw) -> SkillResult:
        if amount is None:
            return self._summary()

        cat = (category or self._guess(what)).lower()
        if cat not in self.CATEGORIES:
            cat = "other"
        folder = self.vault.root / "Expenses"
        folder.mkdir(exist_ok=True)
        now = _now(self.cfg)
        p = folder / f"{now:%Y-%m}.md"
        if not p.exists():
            p.write_text("\n".join([
                "---", "type: expenses", f"month: {now:%Y-%m}",
                "tags: [\"cfilms/expenses\"]", "---", "",
                f"# Expenses — {now:%B %Y}", "",
                "| Date | What | Category | Amount |", "|---|---|---|---|", ""]))
        with p.open("a") as fh:
            fh.write(f"| {now:%d %b} | {what or 'unspecified'} | {cat} | ${amount:,.2f} |\n")
        self.vault.log("expense", f"${amount:,.2f} {cat} — {what}")
        return SkillResult(ok=True, changed=True,
                           summary=f"Logged ${amount:,.2f} for {what or cat} under {cat}.")

    def _summary(self) -> SkillResult:
        import re
        folder = self.vault.root / "Expenses"
        if not folder.exists():
            return SkillResult(ok=True, changed=False, summary="No expenses logged yet.")
        total, by_cat = 0.0, {}
        for p in folder.glob("*.md"):
            for line in p.read_text().splitlines():
                m = re.match(r"\|[^|]+\|([^|]+)\|([^|]+)\|\s*\$([\d,\.]+)", line)
                if m:
                    amt = float(m.group(3).replace(",", ""))
                    total += amt
                    by_cat[m.group(2).strip()] = by_cat.get(m.group(2).strip(), 0) + amt
        top = ", ".join(f"{k} ${v:,.0f}" for k, v in
                        sorted(by_cat.items(), key=lambda x: -x[1])[:4])
        return SkillResult(ok=True, changed=False,
                           summary=f"${total:,.0f} logged so far. {top}.",
                           total=total, by_category=by_cat)

    @staticmethod
    def _guess(what: str) -> str:
        w = what.lower()
        for cat, words in (
            ("fuel", ("fuel", "petrol", "diesel", "servo", "bp", "shell", "7-eleven")),
            ("gear", ("lens", "camera", "battery", "card", "tripod", "drone", "gimbal")),
            ("software", ("adobe", "subscription", "licence", "license", "app")),
            ("uni", ("textbook", "uni", "course", "tuition", "student")),
            ("travel", ("parking", "toll", "uber", "flight", "train")),
        ):
            if any(x in w for x in words):
                return cat
        return "other"
