"""Password hashing helpers built on werkzeug.security."""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

_HASH_PREFIXES = ("pbkdf2:", "scrypt:")


def hash_password(password):
    return generate_password_hash(password)


def is_password_hash(stored):
    """True if `stored` looks like a werkzeug password hash."""
    return (
        isinstance(stored, str)
        and stored.startswith(_HASH_PREFIXES)
        and stored.count("$") == 2
    )


def verify_password(stored, candidate):
    """Check `candidate` against the stored value.

    Returns (matches, needs_rehash). `needs_rehash` is True when the stored
    value is a legacy plaintext password that matched and should be replaced
    by a hash (lazy migration).
    """
    if not isinstance(stored, str) or not isinstance(candidate, str) or stored == "":
        return False, False
    if is_password_hash(stored):
        return check_password_hash(stored, candidate), False
    matches = hmac.compare_digest(stored.encode("utf-8"), candidate.encode("utf-8"))
    return matches, matches
