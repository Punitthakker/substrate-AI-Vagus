"""Accounts: people who use Substrate directly sign in, and own their genome.

  passwords   scrypt (n=2^14, r=8, p=1) with a per-account random salt; never stored or logged in clear
  sessions    signed tokens (HMAC-SHA256) carrying user, expiry and a version; "sign out everywhere" bumps the
              version, which invalidates every token at once. The signing secret is SUBSTRATE_SESSION_SECRET or a
              random secret generated once and kept in the database.
  lockout     5 failed attempts lock the account for 15 minutes; failures don't reveal whether an email exists
  ownership   an account's genome (u-...) is readable only with that account's session or an admin/master key

Platforms that embed Substrate keep using their own logins (publishable key + their user id).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid

from .ledger import Store, _lock, now

EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,24}$", re.I)
MAX_FAILS, LOCK_SECONDS, TTL = 5, 15 * 60, 30 * 24 * 3600


class AuthError(Exception):
    pass


def init(store: Store) -> None:
    store.db.execute("""create table if not exists accounts (email text primary key, user_id text not null,
        pw text not null, created text not null, failed integer not null default 0, locked_until integer not null default 0,
        ver integer not null default 0)""")
    store.db.execute("create table if not exists kv (k text primary key, v text not null)")
    store.db.commit()


def _secret(store: Store) -> bytes:
    env = os.environ.get("SUBSTRATE_SESSION_SECRET")
    if env:
        return env.encode()
    init(store)
    r = store.db.execute("select v from kv where k='session_secret'").fetchone()
    if r:
        return r[0].encode()
    s = secrets.token_urlsafe(48)
    try:
        store.db.execute("insert into kv (k, v) values (?, ?)", ("session_secret", s))
        store.db.commit()
    except Exception:
        pass
    return store.db.execute("select v from kv where k='session_secret'").fetchone()[0].encode()


def hash_pw(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${h.hex()}"


def check_pw(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got.hex(), h)
    except (ValueError, TypeError):
        return False


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(store: Store, email: str, user_id: str, ver: int) -> str:
    body = _b64(json.dumps({"u": user_id, "e": email, "v": ver, "x": int(time.time()) + TTL}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(store), body.encode(), hashlib.sha256).digest())
    return f"sess_{body}.{sig}"


def verify(store: Store, token: str | None) -> dict | None:
    if not token or not token.startswith("sess_") or "." not in token:
        return None
    body, sig = token[5:].rsplit(".", 1)
    good = _b64(hmac.new(_secret(store), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        return None
    try:
        d = json.loads(_unb64(body))
    except ValueError:
        return None
    if d.get("x", 0) < time.time():
        return None
    init(store)
    r = store.db.execute("select user_id, ver from accounts where email=?", (d["e"],)).fetchone()
    if not r or r[0] != d["u"] or int(r[1]) != int(d["v"]):
        return None
    return {"user_id": d["u"], "email": d["e"]}


def signup(store: Store, email: str, password: str, name: str, tissue: str) -> dict:
    from .schemas import Person
    init(store)
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise AuthError("Enter a valid email address.")
    if len(password) < 10:
        raise AuthError("Use at least 10 characters for your password.")
    if store.db.execute("select 1 from accounts where email=?", (email,)).fetchone():
        raise AuthError("An account with that email already exists. Sign in instead.")
    uid = f"u-{uuid.uuid4().hex[:16]}"
    store.put_person(Person(user_id=uid, name=(name or "Member").strip()[:60] or "Member", domain=tissue))
    with _lock:
        store.db.execute("insert into accounts (email,user_id,pw,created,failed,locked_until,ver) values (?,?,?,?,0,0,0)",
                         (email, uid, hash_pw(password), now()))
        store.db.commit()
    return {"user_id": uid, "email": email, "token": issue(store, email, uid, 0)}


def login(store: Store, email: str, password: str) -> dict:
    init(store)
    email = email.strip().lower()
    r = store.db.execute("select user_id, pw, failed, locked_until, ver from accounts where email=?", (email,)).fetchone()
    generic = AuthError("Email or password is incorrect.")
    if not r:
        hash_pw(password)   # same work either way: timing doesn't reveal whether the email exists
        raise generic
    uid, pw, failed, locked_until, ver = r
    if int(locked_until) > time.time():
        raise AuthError("Too many attempts. Try again in a few minutes.")
    if not check_pw(password, pw):
        failed = int(failed) + 1
        lock = int(time.time()) + LOCK_SECONDS if failed >= MAX_FAILS else 0
        with _lock:
            store.db.execute("update accounts set failed=?, locked_until=? where email=?",
                             (0 if lock else failed, lock, email))
            store.db.commit()
        raise generic
    with _lock:
        store.db.execute("update accounts set failed=0, locked_until=0 where email=?", (email,))
        store.db.commit()
    return {"user_id": uid, "email": email, "token": issue(store, email, uid, int(ver))}


def user_of(store: Store, email: str) -> str | None:
    init(store)
    r = store.db.execute("select user_id from accounts where email=?", (email.strip().lower(),)).fetchone()
    return r[0] if r else None


def delete_account(store: Store, email: str, user_id: str) -> None:
    """Right to erasure: the genome, its ledger, its pacts, letters to and from it, and the account itself."""
    from . import legacy
    store.delete_person(user_id)
    legacy.init(store)
    with _lock:
        store.db.execute("delete from letters where to_user=? or from_user=?", (user_id, user_id))
        store.db.execute("delete from accounts where email=?", (email,))
        store.db.commit()


def email_of(store: Store, user_id: str) -> str | None:
    init(store)
    r = store.db.execute("select email from accounts where user_id=?", (user_id,)).fetchone()
    return r[0] if r else None


def is_heir(store: Store, heirs: list[str], heir_id: str) -> bool:
    """Heirs are named by genome id or, for people with accounts, as 'email:someone@example.com'."""
    if heir_id in (heirs or []):
        return True
    em = email_of(store, heir_id)
    return bool(em) and any(h.replace("email:", "").strip().lower() == em.lower() for h in (heirs or []))


def logout_everywhere(store: Store, email: str) -> None:
    init(store)
    with _lock:
        store.db.execute("update accounts set ver = ver + 1 where email=?", (email,))
        store.db.commit()


def change_password(store: Store, email: str, old: str, new: str) -> dict:
    r = store.db.execute("select user_id, pw, ver from accounts where email=?", (email,)).fetchone()
    if not r or not check_pw(old, r[1]):
        raise AuthError("Current password is incorrect.")
    if len(new) < 10:
        raise AuthError("Use at least 10 characters for your password.")
    with _lock:
        store.db.execute("update accounts set pw=?, ver=ver+1 where email=?", (hash_pw(new), email))
        store.db.commit()
    return {"user_id": r[0], "email": email, "token": issue(store, email, r[0], int(r[2]) + 1)}
