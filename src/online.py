"""Authoritative rooms shared by sessions of ONE dynamic Flet server.

Only the service mutates a room. Readers receive copies; revision checks
reject duplicate/stale clicks. Accounts and guests have equal game access.
"""

from dataclasses import dataclass, field
import secrets
import threading
import time

from auth import Identity
from i18n import LocalizedError
from logic import BugaGame, BULL, BOY

ROOM_TTL = 6 * 60 * 60
MAX_ROOMS = 200
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class RoomError(LocalizedError):
    pass


@dataclass
class _Room:
    code: str
    players: dict[int, Identity]
    game: BugaGame = field(default_factory=BugaGame)
    revision: int = 0
    touched: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class RoomView:
    code: str
    side: int
    names: dict[int, str]
    game: BugaGame
    revision: int

    @property
    def ready(self):
        return len(self.names) == 2


class RoomService:
    def __init__(self):
        self._rooms: dict[str, _Room] = {}
        self._lock = threading.RLock()

    def _cleanup(self):
        now = time.monotonic()
        self._rooms = {code: room for code, room in self._rooms.items()
                       if now - room.touched < ROOM_TTL}

    def _get(self, code):
        self._cleanup()
        room = self._rooms.get(code.strip().upper())
        if room is None:
            raise RoomError("error_room_missing")
        return room

    @staticmethod
    def _side(room, identity):
        for side, player in room.players.items():
            if secrets.compare_digest(player.session_id, identity.session_id):
                return side
        raise RoomError("error_membership")

    def _view(self, room, identity):
        side = self._side(room, identity)
        room.touched = time.monotonic()
        return RoomView(room.code, side, {s: p.name for s, p in room.players.items()},
                        room.game.clone(), room.revision)

    def _ensure_available(self, identity):
        if any(any(p.session_id == identity.session_id for p in r.players.values())
               for r in self._rooms.values()):
            raise RoomError("error_existing_room")

    def create(self, identity, side=BULL):
        if side not in (BULL, BOY):
            raise RoomError("error_side")
        with self._lock:
            self._cleanup()
            self._ensure_available(identity)
            if len(self._rooms) >= MAX_ROOMS:
                raise RoomError("error_server_full")
            while True:
                code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
                if code not in self._rooms:
                    break
            room = _Room(code, {side: identity})
            self._rooms[code] = room
            return self._view(room, identity)

    def join(self, code, identity):
        with self._lock:
            room = self._get(code)
            if any(p.session_id == identity.session_id for p in room.players.values()):
                return self._view(room, identity)
            self._ensure_available(identity)
            if len(room.players) == 2:
                raise RoomError("error_room_full")
            room.players[-next(iter(room.players))] = identity
            room.revision += 1
            return self._view(room, identity)

    def read(self, code, identity):
        with self._lock:
            return self._view(self._get(code), identity)

    def read_if_changed(self, code, identity, revision):
        """Idle polling validates membership without copying the game/history."""
        with self._lock:
            room = self._get(code)
            self._side(room, identity)
            room.touched = time.monotonic()
            if room.revision == revision:
                return None
            return self._view(room, identity)

    def play(self, code, identity, move, revision):
        with self._lock:
            room = self._get(code)
            side = self._side(room, identity)
            if len(room.players) != 2:
                raise RoomError("error_wait")
            if revision != room.revision:
                raise RoomError("error_revision")
            if side != room.game.current_turn:
                raise RoomError("error_turn")
            if not room.game.apply(move):
                raise RoomError("error_move")
            room.revision += 1
            return self._view(room, identity)

    def leave(self, code, identity):
        with self._lock:
            room = self._get(code)
            self._side(room, identity)
            # Explicit departure ends the match, without silently assigning
            # a new opponent to an already started game.
            del self._rooms[room.code]
