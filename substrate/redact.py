"""PII redaction before anything leaves the ledger for training.

Always on: a deterministic regex pass (emails, phones, IBANs, card numbers with a Luhn check, account-like
digit runs, URLs) plus the genome's own known names. Optional: Microsoft Presidio (MIT) for NER-based
redaction of names and places, enabled with SUBSTRATE_REDACT=presidio when presidio-analyzer and
presidio-anonymizer are installed. Money amounts are kept: they are the signal, not the identity.
"""
from __future__ import annotations

import os
import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL = re.compile(r"https?://\S+")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PHONE = re.compile(r"(?<![\w$])(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}(?![\w%])")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LONGNUM = re.compile(r"\b\d{9,}\b")


def _luhn(digits: str) -> bool:
    s, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        s, alt = s + d, not alt
    return s % 10 == 0


def _cards(text: str, counts: dict) -> str:
    def sub(m):
        d = re.sub(r"\D", "", m.group(0))
        if 13 <= len(d) <= 19 and _luhn(d):
            counts["card"] = counts.get("card", 0) + 1
            return "[CARD]"
        return m.group(0)
    return _CARD.sub(sub, text)


def _presidio():
    global _ENGINES
    try:
        return _ENGINES
    except NameError:
        pass
    try:
        from presidio_analyzer import AnalyzerEngine  # type: ignore
        from presidio_anonymizer import AnonymizerEngine  # type: ignore
        _ENGINES = (AnalyzerEngine(), AnonymizerEngine())
    except Exception:
        _ENGINES = None
    return _ENGINES


def redact(text: str, names: list[str] | None = None, counts: dict | None = None) -> str:
    """Redact PII. `names` are known identities (full names, contacts) from the genome."""
    if not text:
        return text
    counts = counts if counts is not None else {}

    def rep(rx, tag):
        nonlocal text
        text, n = rx.subn(f"[{tag}]", text)
        if n:
            counts[tag.lower()] = counts.get(tag.lower(), 0) + n

    rep(_EMAIL, "EMAIL")
    rep(_URL, "URL")
    rep(_IBAN, "IBAN")
    text = _cards(text, counts)
    def phone(m):
        raw = m.group(0)
        if _DATE.match(raw.strip()) or len(re.sub(r"\D", "", raw)) < 9:
            return raw
        counts["phone"] = counts.get("phone", 0) + 1
        return "[PHONE]"
    text = _PHONE.sub(phone, text)
    rep(_LONGNUM, "NUMBER")
    for n in sorted({x for x in (names or []) if x and len(x) > 1}, key=len, reverse=True):
        text, k = re.subn(rf"\b{re.escape(n)}\b", "[PERSON]", text, flags=re.I)
        if k:
            counts["person"] = counts.get("person", 0) + k
    if os.environ.get("SUBSTRATE_REDACT") == "presidio" and (eng := _presidio()):
        analyzer, anonymizer = eng
        res = [r for r in analyzer.analyze(text=text, language="en")
               if r.entity_type in ("PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS", "IBAN_CODE",
                                    "CREDIT_CARD", "US_SSN", "IP_ADDRESS")]
        if res:
            counts["presidio"] = counts.get("presidio", 0) + len(res)
            text = anonymizer.anonymize(text=text, analyzer_results=res).text
    return text


def backend() -> str:
    return "presidio" if os.environ.get("SUBSTRATE_REDACT") == "presidio" and _presidio() else "regex"
