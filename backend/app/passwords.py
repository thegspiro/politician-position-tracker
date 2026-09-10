"""Password hashing.

Uses scrypt from the standard library (RFC 7914) rather than bcrypt or argon2,
both of which need a compiled extension. This application is meant to run
unchanged on Unraid, Docker, plain Linux hosts and AWS, including on ARM, and a
pure-stdlib KDF removes a class of build and portability failures.

Hashes are stored as a self-describing string, so the cost parameters can be
raised later without invalidating existing passwords: an old hash still
verifies against the parameters recorded in it.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "scrypt"

# Roughly 16 MB and ~100ms per hash on current hardware. n must be a power of 2.
DEFAULT_N = 2**14
DEFAULT_R = 8
DEFAULT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32

# scrypt needs a memory budget of at least 128 * n * r bytes.
_MAX_MEMORY = 132 * DEFAULT_N * DEFAULT_R

MIN_PASSWORD_LENGTH = 12


class InvalidHash(ValueError):
    """Raised when a stored hash cannot be parsed."""


def hash_password(password: str) -> str:
    """Hash a password into a self-describing string."""
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=DEFAULT_N,
        r=DEFAULT_R,
        p=DEFAULT_P,
        dklen=KEY_BYTES,
        maxmem=_MAX_MEMORY,
    )
    return "$".join(
        (
            ALGORITHM,
            str(DEFAULT_N),
            str(DEFAULT_R),
            str(DEFAULT_P),
            salt.hex(),
            derived.hex(),
        )
    )


def verify_password(password: str, stored: str | None) -> bool:
    """Check a password against a stored hash, in constant time."""
    if not stored:
        return False
    try:
        algorithm, n, r, p, salt_hex, expected_hex = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        n_value, r_value, p_value = int(n), int(r), int(p)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, AttributeError):
        # A malformed hash is a failed login, not a crash.
        return False

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_value,
        r=r_value,
        p=p_value,
        dklen=len(expected),
        maxmem=132 * n_value * r_value,
    )
    return hmac.compare_digest(derived, expected)


def validate_password_strength(password: str) -> None:
    """Raise ValueError if a password is too weak to accept."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
