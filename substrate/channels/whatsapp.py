"""WhatsApp channel (Meta WhatsApp Business Cloud API).

Setup (Meta Business > WhatsApp > API Setup), then set on the server:
  WHATSAPP_VERIFY_TOKEN   any string; paste the same into Meta's webhook config
  WHATSAPP_APP_SECRET     app secret, used to verify X-Hub-Signature-256 on every delivery
  WHATSAPP_TOKEN          permanent access token
  WHATSAPP_PHONE_ID       the phone number id
  WHATSAPP_TISSUE         default tissue for new senders (wealth)
  WHATSAPP_GRAPH_VERSION  Graph API version (default v23.0)
Webhook URL: https://YOUR-HOST/v1/channels/whatsapp/webhook

Each sender's number is hashed into a private genome (wa-...). Replies use WhatsApp formatting; after a hard
stop the person gets buttons: "Hold me to it", "I'll wait", "Doing it anyway" (pact / followed / ignored).
"tissue markets" (or wealth, trading, venture, founder, wellbeing) switches tissue. Crisis messages get the
Safety Protocol and are never stored. Without WHATSAPP_TOKEN the channel runs dry: replies are returned, not sent.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

import httpx

from .. import domains
from ..schemas import AdviseRequest, OutcomeRequest, Person

TISSUE_CMD = re.compile(r"^\s*/?(tissue|mode)\s+(wealth|venture|founder|wellbeing|markets|trading)\s*$", re.I)
HELP = ("*Substrate* here: the honest advisor with a heart.\n\nTell me what you're about to do with money, a bet, a trade "
        "or a heated message, and I'll tell you the truth, kindly.\n\nSwitch focus: _tissue wealth_, _tissue markets_, "
        "_tissue trading_, _tissue wellbeing_, _tissue venture_, _tissue founder_.")


def verify_signature(raw: bytes, header: str | None) -> bool:
    secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not secret:
        return True   # dry-run / development
    if not header or not header.startswith("sha256="):
        return False
    good = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, header[7:])


def user_id(phone: str) -> str:
    return "wa-" + hashlib.sha256(("wa:" + re.sub(r"\D", "", phone)).encode()).hexdigest()[:16]


def to_whatsapp(md: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"*\1*", md)
    t = re.sub(r"^- ", "• ", t, flags=re.M)
    t = re.sub(r"^> ?", "▏", t, flags=re.M)
    return t[:4000]


def send(to: str, payload: dict) -> dict:
    token, phone_id = os.environ.get("WHATSAPP_TOKEN"), os.environ.get("WHATSAPP_PHONE_ID")
    msg = {"messaging_product": "whatsapp", "to": to, **payload}
    if not token or not phone_id:
        return {"dry_run": True, "message": msg}
    ver = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0")
    r = httpx.post(f"https://graph.facebook.com/{ver}/{phone_id}/messages", json=msg, timeout=10,
                   headers={"authorization": f"Bearer {token}"})
    return {"status": r.status_code}


def _text(body: str) -> dict:
    return {"type": "text", "text": {"body": body, "preview_url": False}}


def _buttons(body: str, buttons: list[tuple[str, str]]) -> dict:
    return {"type": "interactive", "interactive": {"type": "button", "body": {"text": body[:1024]},
            "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t[:20]}} for i, t in buttons[:3]]}}}


def handle(store, engine, phone: str, text: str | None = None, button_id: str | None = None) -> list[dict]:
    """One inbound message -> the payloads to send back."""
    from .. import pacts
    uid = user_id(phone)
    person = store.get_person(uid)
    if not person:
        person = store.put_person(Person(user_id=uid, name="WhatsApp member",
                                         domain=os.environ.get("WHATSAPP_TISSUE", "wealth")))
        if not text or text.strip().lower() in ("hi", "hello", "start", "help", "مرحبا"):
            return [_text(HELP)]
    if button_id:
        kind, _, ledger_id = button_id.partition(":")
        ev = store.get_event(ledger_id)
        if not ev or ev["user_id"] != uid:   # a button can only act on the sender's own advice
            return []
        if kind == "pact":
            p = pacts.make(store, person, ledger_id, person.domain)
            return [_text(f"⚓ Pact made: *{p.text}*. If you come back before then, I'll remind you of your own words.")]
        if kind in ("follow", "ignore"):
            engine.record_outcome(OutcomeRequest(ledger_id=ledger_id, action="followed" if kind == "follow" else "ignored"))
            return [_text("Good call. Waiting is a decision too." if kind == "follow"
                          else "Noted, without judgment. Tell me how it goes, so I get better for you.")]
        return []
    text = (text or "").strip()
    if not text:
        return []
    if text.lower() in ("help", "/help", "start"):
        return [_text(HELP)]
    m = TISSUE_CMD.match(text)
    if m:
        person.domain = m.group(2).lower()
        store.put_person(person)
        return [_text(f"Focus set to *{domains.get(person.domain).name}*: {domains.get(person.domain).tagline}.")]
    r = engine.advise(AdviseRequest(user_id=uid, message=text))
    body = to_whatsapp(r.message)
    if r.pact_offer and not r.safety:
        return [_text(body), _buttons(f"Want me to hold you to it? {r.pact_offer['text']}.",
                                       [(f"pact:{r.ledger_id}", "Hold me to it"), (f"follow:{r.ledger_id}", "I'll wait"),
                                        (f"ignore:{r.ledger_id}", "Doing it anyway")])]
    return [_text(body)]


def parse(payload: dict) -> list[tuple[str, str | None, str | None]]:
    """Meta webhook payload -> [(from, text, button_id)]."""
    out = []
    for entry in payload.get("entry", []):
        for ch in entry.get("changes", []):
            for msg in (ch.get("value") or {}).get("messages", []) or []:
                frm = msg.get("from")
                if msg.get("type") == "text":
                    out.append((frm, (msg.get("text") or {}).get("body"), None))
                elif msg.get("type") == "interactive":
                    br = (msg.get("interactive") or {}).get("button_reply") or {}
                    out.append((frm, None, br.get("id")))
                elif msg.get("type") == "button":
                    out.append((frm, (msg.get("button") or {}).get("text"), None))
    return out
