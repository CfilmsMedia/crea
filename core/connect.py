"""`crea connect` — link the outside services, one at a time.

Everything here is designed for someone who is not a developer. Each service
asks the fewest questions it can, verifies the answer against the real API
before saving it, and says plainly what went wrong when it fails.

Secrets go to ~/crea/var/env with 0600 permissions and are loaded into the
environment by the CLI. They are never written into crea.config.json, so that
file stays safe to share, commit or paste.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

SERVICES = ("acuity", "google", "whatsapp", "higgsfield", "apify", "editor", "calls")


# ------------------------------------------------------------------ env file

def env_path(cfg) -> Path:
    return Path(cfg.get("paths.root")) / "var/env"


def load_env(cfg) -> None:
    p = env_path(cfg)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def set_env(cfg, key: str, value: str) -> None:
    p = env_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [l for l in (p.read_text().splitlines() if p.exists() else [])
             if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    p.write_text("\n".join(lines) + "\n")
    p.chmod(0o600)
    os.environ[key] = value


def set_config(cfg, dotted: str, value) -> None:
    path = Path(cfg.get("paths.root")) / "crea.config.json"
    data = json.loads(path.read_text())
    node = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    path.write_text(json.dumps(data, indent=2))


# ------------------------------------------------------------------- prompts

def ask(label: str, secret: bool = False) -> str:
    if secret:
        import getpass
        return getpass.getpass(f"  {label}: ").strip()
    return input(f"  {label}: ").strip()


def head(title: str, blurb: str = "") -> None:
    print(f"\n\033[1m{title}\033[0m")
    if blurb:
        print(f"  {blurb}")


# ------------------------------------------------------------------ services

def connect_acuity(cfg) -> bool:
    head("Acuity Scheduling",
         "In Acuity: Integrations -> API. You need the User ID and the API Key.")
    uid = ask("User ID")
    key = ask("API Key", secret=True)
    if not (uid and key):
        print("  skipped.")
        return False
    set_env(cfg, "ACUITY_USER_ID", uid)
    set_env(cfg, "ACUITY_API_KEY", key)
    from .connectors.acuity import Acuity
    try:
        me = Acuity(cfg).verify()
        print(f"  connected to {me.get('business') or me.get('email')}.")
        return True
    except Exception as e:
        print(f"  that didn't work: {e}")
        print("  Double-check you copied the API Key and not the Client ID.")
        return False


def connect_google(cfg) -> bool:
    head("Google (Calendar, Drive, Docs)",
         "This opens a browser once so you can approve access.")
    print("  You need a Google Cloud OAuth client (Desktop app).")
    print("  If Tris set one up for you, paste those two values here.")
    cid = ask("Client ID")
    csec = ask("Client secret", secret=True)
    if not (cid and csec):
        print("  skipped.")
        return False

    from .connectors.google import SCOPES, TOKEN_URL
    q = urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent"})
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{q}"
    print("\n  Opening your browser. Approve access, then paste the code back here.")
    subprocess.run(["open", url], capture_output=True)
    print(f"  If it didn't open: {url}\n")
    code = ask("Paste the code")
    if not code:
        print("  skipped.")
        return False

    import urllib.request
    data = urllib.parse.urlencode({
        "code": code, "client_id": cid, "client_secret": csec,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data),
                                    timeout=30) as r:
            tok = json.loads(r.read())
    except Exception as e:
        print(f"  that didn't work: {e}")
        return False
    if "refresh_token" not in tok:
        print("  Google didn't return a refresh token. Try again and make sure you "
              "approve rather than reuse a previous approval.")
        return False

    import time
    tok.update({"client_id": cid, "client_secret": csec,
                "expires_at": time.time() + int(tok.get("expires_in", 3600))})
    p = Path(cfg.get("paths.root")) / "var/google-token.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(tok, indent=2))
    p.chmod(0o600)

    from .connectors.google import Google
    try:
        n = len(Google(cfg).events(days=7))
        print(f"  connected. {n} event(s) in your next week.")
        return True
    except Exception as e:
        print(f"  saved, but a test call failed: {e}")
        return False


def connect_whatsapp(cfg) -> bool:
    head("WhatsApp",
         "A QR code will appear. On your phone: WhatsApp -> Settings -> "
         "Linked Devices -> Link a Device, and scan it.")
    print("  Your number stays a normal WhatsApp number. Nothing is migrated.")
    from .connectors.whatsapp import WhatsApp
    w = WhatsApp(cfg)
    try:
        w.pair()
    except Exception as e:
        print(f"  couldn't start pairing: {e}")
        return False
    if w.ready():
        print("  paired.")
        return True
    print("  pairing didn't complete. Run this again when you're ready.")
    return False


def connect_higgsfield(cfg) -> bool:
    head("Higgsfield", "Paste the API key from your Higgsfield account.")
    key = ask("API key", secret=True)
    if not key:
        print("  skipped.")
        return False
    set_env(cfg, "HIGGSFIELD_API_KEY", key)
    from .connectors.higgsfield import Higgsfield
    try:
        Higgsfield(cfg).verify()
        print("  connected.")
        return True
    except Exception as e:
        print(f"  saved, but the test call failed: {e}")
        print("  CREA will still upload to Drive; it just won't hand off to Higgsfield.")
        return False


def connect_apify(cfg) -> bool:
    head("Apify", "Paste your Apify API token (Settings -> Integrations).")
    tok = ask("API token", secret=True)
    if not tok:
        print("  skipped.")
        return False
    set_env(cfg, "APIFY_TOKEN", tok)
    ds = ask("Dataset ID of your listings scraper (Enter to skip)")
    if ds:
        set_config(cfg, "integrations.apify.dataset_id", ds)
    from .connectors.apify import Apify
    try:
        me = Apify(cfg).verify()
        print(f"  connected as {me.get('username') or 'ok'}.")
        return True
    except Exception as e:
        print(f"  that didn't work: {e}")
        return False


def connect_editor(cfg) -> bool:
    head("Your editor", "The number CREA messages when a shoot is ready.")
    name = ask("Editor's name") or "Editor"
    num = ask("WhatsApp number, with country code (e.g. +61412345678)")
    if not num:
        print("  skipped.")
        return False
    set_config(cfg, "integrations.whatsapp.editor_handle", num)
    set_config(cfg, "integrations.whatsapp.editor_name", name)
    print(f"  {name} will be told when a shoot lands.")
    return True


def connect_calls(cfg) -> bool:
    head("Call recording",
         "NSW requires every party to a call to consent to being recorded.")
    print("  CREA plays a disclosure before it keeps any audio, and deletes the")
    print("  recording once it has read the booking out of it.\n")
    current = cfg.get("call_recording.disclosure_text", "")
    print(f"  Current wording: \"{current}\"\n")
    print("  Have this checked by someone qualified before switching it on.")
    ans = ask("Has the wording been checked, and do you want this on? (yes/no)")
    if ans.lower() not in ("y", "yes"):
        set_config(cfg, "call_recording.enabled", False)
        print("  left off. Nothing will be recorded.")
        return False
    new = ask("Disclosure wording (Enter to keep the current one)")
    if new:
        set_config(cfg, "call_recording.disclosure_text", new)
    set_config(cfg, "call_recording.enabled", True)
    print("  on. CREA will not record a call where the disclosure fails to play.")
    return True


HANDLERS = {
    "acuity": connect_acuity, "google": connect_google, "whatsapp": connect_whatsapp,
    "higgsfield": connect_higgsfield, "apify": connect_apify,
    "editor": connect_editor, "calls": connect_calls,
}


def run(cfg, which: str | None = None) -> int:
    load_env(cfg)
    if which:
        if which not in HANDLERS:
            print(f"unknown service '{which}'. Try: {', '.join(HANDLERS)}")
            return 1
        return 0 if HANDLERS[which](cfg) else 1

    from .connectors import status_all
    st = status_all(cfg)
    print("\nWhat's connected:\n")
    for name in ("acuity", "google", "whatsapp", "higgsfield", "apify"):
        s = st.get(name, {})
        print(f"  {'yes' if s.get('ready') else 'no ':<4} {name}")
    print()

    if not sys.stdin.isatty():
        print("Run this from a Terminal window to connect anything.")
        return 0

    todo = [n for n in ("acuity", "google", "whatsapp", "higgsfield", "apify")
            if not st.get(n, {}).get("ready")]
    if not todo:
        print("Everything's connected.")
        return 0

    print("Let's connect what's missing. Press Enter to skip any of them.\n")
    for name in todo:
        HANDLERS[name](cfg)
    if not cfg.get("integrations.whatsapp.editor_handle", None):
        connect_editor(cfg)
    return 0
