"""Optional cloud voice. Without a key, the console uses the device's own voices (free, uneven quality).

  TTS_PROVIDER=openai        OPENAI_API_KEY     TTS_VOICE (default: nova)    TTS_MODEL (default: gpt-4o-mini-tts)
  TTS_PROVIDER=elevenlabs    ELEVENLABS_API_KEY TTS_VOICE (voice id; default: Rachel)  TTS_MODEL (default: eleven_multilingual_v2)

Cost is per character, so answers are capped at TTS_MAX_CHARS and identical texts are served from a small cache.
"""
from __future__ import annotations

import hashlib
import os
import re
from collections import OrderedDict

import httpx

MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "900"))
_cache: "OrderedDict[str, bytes]" = OrderedDict()
_CACHE_N = 64


def provider() -> str | None:
    p = os.environ.get("TTS_PROVIDER", "").lower()
    if p == "openai" and os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if p == "elevenlabs" and os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    return None


def status() -> dict | None:
    p = provider()
    if not p:
        return None
    return {"provider": p, "voice": os.environ.get("TTS_VOICE") or ("nova" if p == "openai" else "Rachel"), "max_chars": MAX_CHARS}


def clean(text: str) -> str:
    """What gets read: the answer, not the markup, not the ledger note, not the degraded banner."""
    t = re.sub(r"\*\*|__|(?<!\w)_|_(?!\w)", "", text or "")
    t = re.sub(r"^[->]\s?", "", t, flags=re.M)
    t = re.sub(r"This advice is recorded in your Vagus Ledger\.", "", t)
    t = re.sub(r"Reasoning engine unavailable[^\n]*", "", t)
    t = re.sub(r"\$(\d+(?:\.\d+)?)k\b", r"\1 thousand dollars", t)
    t = re.sub(r"\$(\d+(?:\.\d+)?)M\b", r"\1 million dollars", t)
    t = re.sub(r"\$(\d[\d,]*)\b", r"\1 dollars", t)
    t = re.sub(r"\n+", ". ", t)
    t = re.sub(r"\.\s*\.", ".", t)
    return re.sub(r"\s+", " ", t).strip()[:MAX_CHARS]


def synthesize(text: str, lang: str = "en") -> tuple[bytes, str]:
    """Returns (audio bytes, mime). Raises on any failure; the caller falls back to the device voice."""
    p = provider()
    if not p:
        raise RuntimeError("no TTS provider configured")
    t = clean(text)
    if not t:
        raise ValueError("nothing to say")
    key = hashlib.sha256(f"{p}|{lang}|{os.environ.get('TTS_VOICE', '')}|{t}".encode()).hexdigest()
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key], "audio/mpeg"
    if p == "openai":
        r = httpx.post("https://api.openai.com/v1/audio/speech", timeout=40,
                       headers={"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                       json={"model": os.environ.get("TTS_MODEL", "gpt-4o-mini-tts"), "voice": os.environ.get("TTS_VOICE", "nova"),
                             "input": t, "response_format": "mp3",
                             "instructions": "Warm, calm, unhurried; a trusted advisor speaking plainly. Pause briefly between sentences."})
    else:
        voice = os.environ.get("TTS_VOICE", "21m00Tcm4TlvDq8ikWAM")   # Rachel
        r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}", timeout=40,
                       headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "accept": "audio/mpeg"},
                       json={"text": t, "model_id": os.environ.get("TTS_MODEL", "eleven_multilingual_v2"),
                             "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2}})
    r.raise_for_status()
    audio = r.content
    _cache[key] = audio
    while len(_cache) > _CACHE_N:
        _cache.popitem(last=False)
    return audio, "audio/mpeg"
