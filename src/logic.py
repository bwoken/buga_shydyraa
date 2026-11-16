"""Pure game rules, independent of UI and networking.

Draw limits and the bull victory threshold belong to this app's rule variant.
"""

from copy import deepcopy
from typing import Literal, NamedTuple

from topology import NODE_COORDS, BOARD_NEIGHBORS, CAPTURE_PATHS

EMPTY, BULL, BOY = 0, 1, -1
BULLS_WIN, BOYS_WIN = "BULLS_WIN", "BOYS_WIN"
DRAW_NO_CAPTURE, DRAW_REPETITION = "DRAW_NO_CAPTURE", "DRAW_REPETITION"
BOYS_TO_WIN_AS_BULLS = 9
MOVES_WITHOUT_CAPTURE_LIMIT = 60  # plies, including placements
REPETITIONS_FOR_DRAW = 3
INITIAL_BOYS = 24


class Move(NamedTuple):
    kind: Literal["MOVE", "PLACE"]
    start: int | None
    end: int


def infer_move(before, after):
    """Recover one move from consecutive board positions."""
    if not before:
        return None
    removed = [n for n in before if before[n] != EMPTY and after[n] == EMPTY]
    added = [n for n in after if after[n] != EMPTY and before[n] == EMPTY]
    changed = {n for n in before if before[n] != after[n]}
    if len(added) != 1:
        return None
    end = added[0]
    if not removed and after[end] == BOY and changed == {end}:
        return Move("PLACE", None, end)
    starts = [n for n in removed if before[n] == after[end]]
    if len(starts) != 1 or len(removed) > 2 or changed != {end, *removed}:
        return None
    return Move("MOVE", starts[0], end)


class BugaGame:
    def __init__(self):
        self.board = self.initialize_board()
        self.current_turn = BULL
        self.unused_boys = 16
        self.moves_without_capture = 0
        self.position_history = [self.position_key()]
        self.history = []

    @staticmethod
    def initialize_board():
        board = dict.fromkeys(range(1, 36), EMPTY)
        for node in (7, 27):
            board[node] = BULL
        for node in (11, 12, 13, 16, 18, 21, 22, 23):
            board[node] = BOY
        return board

    def position_key(self):
        return tuple(self.board.values()), self.current_turn, self.unused_boys

    def clone(self):
        """A worker or client snapshot must never mutate the live game."""
        return deepcopy(self)

    def last_move(self):
        """Return the latest recorded move, including a placement."""
        if not self.history:
            return None
        _, snapshot = self.history[-1]
        return infer_move(snapshot[0], self.board)

    def _snapshot(self):
        return (self.board.copy(), self.current_turn, self.unused_boys,
                self.moves_without_capture, len(self.position_history))

    def _restore_snapshot(self, snapshot):
        board, turn, reserve, quiet_plies, history_length = snapshot
        self.board = board.copy()
        self.current_turn = turn
        self.unused_boys = reserve
        self.moves_without_capture = quiet_plies
        del self.position_history[history_length:]

    def undo_last(self):
        if not self.history:
            return False
        _, snapshot = self.history.pop()
        self._restore_snapshot(snapshot)
        return True

    def undo_player_move(self, player_side):
        if not any(side == player_side for side, _ in self.history):
            return False
        while self.history:
            side, _ = self.history[-1]
            self.undo_last()
            if side == player_side:
                return True
        return False

    def destinations(self, node):
        """Geometric moves for either side, independent of whose turn it is."""
        piece = self.board.get(node)
        if piece not in (BULL, BOY) or (piece == BOY and self.unused_boys):
            return []
        targets = [end for end in BOARD_NEIGHBORS[node] if self.board[end] == EMPTY]
        if piece == BULL:
            targets.extend(end for middle, end in CAPTURE_PATHS[node]
                           if self.board[middle] == BOY and self.board[end] == EMPTY)
        return targets

    def get_legal_moves_for_node(self, node):
        if self.board.get(node) != self.current_turn:
            return []
        return self.destinations(node)

    def is_valid_move(self, start, end):
        return end in self.get_legal_moves_for_node(start)

    def capture_node(self, move):
        kind, start, end = move
        if kind != "MOVE" or self.board.get(start) != BULL:
            return None
        return next((mid for mid, target in CAPTURE_PATHS[start]
                     if target == end and self.board[mid] == BOY
                     and self.board[end] == EMPTY), None)

    def get_all_legal_moves(self):
        if self.current_turn == BOY and self.unused_boys:
            return [Move("PLACE", None, node) for node, piece in self.board.items()
                    if piece == EMPTY]
        return [Move("MOVE", start, end) for start, piece in self.board.items()
                if piece == self.current_turn for end in self.destinations(start)]

    def apply(self, move, save_undo=True):
        if not isinstance(move, (tuple, list)) or len(move) != 3:
            return False
        kind, start, end = move
        if kind == "PLACE" and start is None:
            return self.place_boy(end, save_undo)
        if kind == "MOVE":
            return self.make_move(start, end, save_undo)
        return False

    def _finish_move(self, captured=False):
        self.moves_without_capture = 0 if captured else self.moves_without_capture + 1
        self.current_turn = -self.current_turn
        self.position_history.append(self.position_key())

    def make_move(self, start, end, save_undo=True):
        if self.check_winner() or not self.is_valid_move(start, end):
            return False
        if save_undo:
            self.history.append((self.current_turn, self._snapshot()))
        captured = self.capture_node(Move("MOVE", start, end))
        if captured is not None:
            self.board[captured] = EMPTY
        self.board[end], self.board[start] = self.board[start], EMPTY
        self._finish_move(captured is not None)
        return True

    def place_boy(self, node, save_undo=True):
        if (self.check_winner() or self.current_turn != BOY
                or self.unused_boys <= 0 or self.board.get(node) != EMPTY):
            return False
        if save_undo:
            self.history.append((self.current_turn, self._snapshot()))
        self.board[node] = BOY
        self.unused_boys -= 1
        self._finish_move()
        return True

    def can_bull_move(self):
        return any(self.destinations(node) for node, piece in self.board.items()
                   if piece == BULL)

    def check_winner(self):
        remaining = sum(piece == BOY for piece in self.board.values()) + self.unused_boys
        if remaining < BOYS_TO_WIN_AS_BULLS:
            return BULLS_WIN
        if not self.can_bull_move():
            return BOYS_WIN
        if self.moves_without_capture >= MOVES_WITHOUT_CAPTURE_LIMIT:
            return DRAW_NO_CAPTURE
        if self.position_history.count(self.position_key()) >= REPETITIONS_FOR_DRAW:
            return DRAW_REPETITION
        return None
