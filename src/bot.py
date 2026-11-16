"""Bounded iterative deepening with alpha-beta and tactical move ordering."""

import random
import time

from logic import BULL, BOY, EMPTY, BULLS_WIN, BOYS_WIN, INITIAL_BOYS
from topology import BOARD_NEIGHBORS, CAPTURE_PATHS

WIN_SCORE = 100_000


class SearchTimeout(Exception):
    pass


class EasyBot:
    def __init__(self, game, bot_side):
        self.game, self.bot_side = game, bot_side

    def get_move(self):
        if self.game.current_turn != self.bot_side or self.game.check_winner():
            return None
        moves = self.game.get_all_legal_moves()
        if not moves:
            return None
        captures = [move for move in moves if self.game.capture_node(move) is not None]
        return random.choice(captures or moves)

    def make_move(self):
        move = self.get_move()
        return self.game.apply(move) if move else False


class SmartBot(EasyBot):
    def __init__(self, game, bot_side, depth=6, time_limit=1.5):
        super().__init__(game, bot_side)
        self.depth, self.time_limit = depth, time_limit
        self.completed_depth = 0
        self.nodes = 0

    def get_move(self):
        if self.game.current_turn != self.bot_side or self.game.check_winner():
            return None
        self.search_game = self.game.clone()
        self.deadline = time.monotonic() + max(0, self.time_limit)
        self.completed_depth, self.nodes = 0, 0
        moves = self._order_moves(self.search_game.get_all_legal_moves())
        if not moves:
            return None
        best = moves[0]
        for depth in range(1, self.depth + 1):
            try:
                score, candidate = self._root(depth, best)
            except SearchTimeout:
                break
            best = candidate
            self.completed_depth = depth
            if abs(score) >= WIN_SCORE - 100:
                break
        return best

    def _check_time(self):
        if time.monotonic() >= self.deadline:
            raise SearchTimeout

    def _root(self, depth, preferred):
        alpha, beta = -float("inf"), float("inf")
        best = preferred
        for move in self._order_moves(self.search_game.get_all_legal_moves(), preferred):
            self._check_time()
            snapshot = self.search_game._snapshot()
            try:
                self.search_game.apply(move, save_undo=False)
                score = self._search(depth - 1, alpha, beta, 1)
            finally:
                self.search_game._restore_snapshot(snapshot)
            if score > alpha:
                alpha, best = score, move
        return alpha, best

    def _terminal_score(self, winner, ply):
        if winner not in (BULLS_WIN, BOYS_WIN):
            return 0
        won = winner == (BULLS_WIN if self.bot_side == BULL else BOYS_WIN)
        return WIN_SCORE - ply if won else -WIN_SCORE + ply

    def _search(self, depth, alpha, beta, ply, extensions=2):
        self._check_time()
        self.nodes += 1
        winner = self.search_game.check_winner()
        if winner:
            return self._terminal_score(winner, ply)
        moves = self.search_game.get_all_legal_moves()
        if depth <= 0:
            captures = any(self.search_game.capture_node(m) is not None for m in moves)
            if not captures or extensions <= 0:
                return self._evaluate()
            depth = 1
            extensions -= 1
        if not moves:
            return self._evaluate()
        maximizing = self.search_game.current_turn == self.bot_side
        best = -float("inf") if maximizing else float("inf")
        for move in self._order_moves(moves):
            snapshot = self.search_game._snapshot()
            try:
                self.search_game.apply(move, save_undo=False)
                score = self._search(depth - 1, alpha, beta, ply + 1, extensions)
            finally:
                self.search_game._restore_snapshot(snapshot)
            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)
            if alpha >= beta:
                break
        return best

    def _evaluate(self):
        game = self.search_game
        remaining = sum(p == BOY for p in game.board.values()) + game.unused_boys
        score = (INITIAL_BOYS - remaining) * 140
        for node, piece in game.board.items():
            if piece != BULL:
                continue
            mobility = len(game.destinations(node))
            captures = sum(game.board[mid] == BOY and game.board[end] == EMPTY
                           for mid, end in CAPTURE_PATHS[node])
            score += mobility * 9 + captures * 45
            score -= 180 if mobility == 0 else 60 if mobility == 1 else 0
        cohesion = sum(game.board[n] == BOY for node, p in game.board.items()
                       if p == BOY for n in BOARD_NEIGHBORS[node])
        score -= cohesion * 2
        return score if self.bot_side == BULL else -score

    def _order_moves(self, moves, preferred=None):
        def priority(move):
            _, start, end = move
            score = 10_000 if move == preferred else 0
            score += 1_000 if self.search_game.capture_node(move) is not None else 0
            score += len(BOARD_NEIGHBORS[end]) * 2
            if self.search_game.current_turn == BOY:
                board = self.search_game.board
                score += 25 * sum(board[n] == BULL for n in BOARD_NEIGHBORS[end])
                score -= 100 * sum(board[bull] == BULL and mid == end
                                   and board[landing] == EMPTY and landing != start
                                   for bull, paths in CAPTURE_PATHS.items()
                                   for mid, landing in paths)
            return score
        return sorted(moves, key=priority, reverse=True)
