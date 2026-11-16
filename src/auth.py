"""SQLite accounts and opaque, server-owned session identities."""

from dataclasses import dataclass, field
from contextlib import contextmanager
from hashlib import pbkdf2_hmac
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from i18n import LocalizedError

PASSWORD_ITERATIONS = 600_000
NAME_PATTERN = re.compile(r"[\w-]{3,24}\Z", re.UNICODE)


@dataclass(frozen=True)
class Identity:
    name: str
    guest: bool = True
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)


class AuthError(LocalizedError):
    pass


class AuthStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._attempts: dict[str, list[float]] = {}

    @staticmethod
    def _name(name):
        name = name.strip()
        if not NAME_PATTERN.fullmatch(name):
            raise AuthError("error_name")
        return name

    @staticmethod
    def guest(name=""):
        name = name.strip() or f"Гость-{secrets.randbelow(9000) + 1000}"
        if len(name) > 24 or any(not c.isprintable() for c in name):
            raise AuthError("error_guest_name")
        return Identity(name)

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS users ("
                    "name_key TEXT PRIMARY KEY, name TEXT NOT NULL, "
                    "salt BLOB NOT NULL, password_hash BLOB NOT NULL)"
                )
                yield connection
        finally:
            connection.close()

    def _check_rate(self, key):
        now = time.monotonic()
        self._attempts = {name: [t for t in times if now - t < 60]
                          for name, times in self._attempts.items()
                          if times and now - times[-1] < 60}
        # Bound both one-account attacks and random-username attempts.
        if sum(map(len, self._attempts.values())) >= 200:
            raise AuthError("error_rate")
        attempts = self._attempts.setdefault(key, [])
        if len(attempts) >= 5:
            raise AuthError("error_rate")
        attempts.append(now)

    def register(self, name, password):
        name = self._name(name)
        if not 10 <= len(password) <= 128:
            raise AuthError("error_password")
        with self._lock:
            self._check_rate(name.casefold())
            salt = secrets.token_bytes(16)
            digest = pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
            try:
                with self._connect() as connection:
                    connection.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                                       (name.casefold(), name, salt, digest))
            except sqlite3.IntegrityError:
                raise AuthError("error_name_taken") from None
        return Identity(name, guest=False)

    def login(self, name, password):
        name = self._name(name)
        if len(password) > 128:
            raise AuthError("error_credentials")
        with self._lock:
            self._check_rate(name.casefold())
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT name, salt, password_hash FROM users WHERE name_key = ?",
                    (name.casefold(),),
                ).fetchone()
            salt = row[1] if row else bytes(16)
            digest = pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
            if row is None or not hmac.compare_digest(digest, row[2]):
                raise AuthError("error_credentials")
            self._attempts.pop(name.casefold(), None)
        return Identity(row[0], guest=False)
