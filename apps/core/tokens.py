import hashlib
import secrets


def new_token():
    """Return (raw_token, digest). Only the digest is ever stored."""
    raw = secrets.token_urlsafe(32)
    return raw, digest(raw)


def digest(raw):
    return hashlib.sha256((raw or "").encode()).hexdigest()
