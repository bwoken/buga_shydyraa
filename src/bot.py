import random
import time
from logic import BULL, BOY, EMPTY, board_nodes, possible_moves


class EasyBot:
    def __init__(self, game, bot_side):
        self.game = game
        self.bot_side = bot_side

    def get_move(self):
        if self.game.current_turn != self.bot_side:
            return None
        moves = self.game.get_all_legal_moves()
        if not moves:
            return None

        if self.bot_side == BULL:
            return self._choose_bull_move(moves)
        return self._choose_boy_move(moves)

    def make_move(self):
        move = self.get_move()
        if not move:
            return False
        kind, start, end = move
        if kind == "MOVE":
            return self.game.make_move(start, end)
        elif kind == "PLACE":
            return self.game.place_boy(end)
        return False

    # -------БЫК-----------
    def _choose_bull_move(self,moves):
        captures = [move for move in moves if self._is_capture(move)]
        if captures:
            return random.choice(captures)
        return random.choice(moves)

    def _is_capture(self,move):
        kind,start,end = move
        if kind != "MOVE":
            return False
        return end not in board_nodes.get(start,[])

    #------------МАЛЬЧИК------------

    def _choose_boy_move(self,moves):
        # 1. фильтруем ходы, после которых мальчика сразу съедят
        safe_moves = []
        for move in moves:
            kind,start,end = move
            if kind == "PLACE":
                if not self._would_be_captured(start=None,end=end,is_place=True):
                    safe_moves.append(move)
            else: # move
                if not self._would_be_captured(start=start,end=end,is_place=False):
                    safe_moves.append(move)

        #если все ходы плохие, то все равно делаем ход
        candidates = safe_moves if safe_moves else moves

        targets = self._empty_bull_neighbors()
        blocking = [move for move in candidates if move[2] in targets]
        return random.choice(blocking if blocking else candidates)

    def _would_be_captured(self,start,end,is_place):
        board = self.game.board.copy()
        if not is_place:
            board[start] = EMPTY
        board[end] = BOY

        for pos, piece in board.items():
            if piece != BULL:
                continue
            for mid, landing in possible_moves.get(pos,[]):
                if mid == end and board.get(landing) == EMPTY:
                    return True

        return False

    def _empty_bull_neighbors(self):
        result = set()
        for node, piece in self.game.board.items():
            if piece == BULL:
                for neighbor in board_nodes.get(node,[]):
                    if self.game.board.get(neighbor) == EMPTY:
                        result.add(neighbor)

        return result

class SmartBot:
    """
    Minimax с альфа-бета отсечением и оценкой позиции.

    depth      — максимальная глубина поиска (итеративное углубление)
    time_limit — жёсткий лимит на раздумья в секундах
    """

    def __init__(self, game, bot_side, depth=3, time_limit=2.0):
        self.game = game
        self.bot_side = bot_side
        self.depth = depth
        self.time_limit = time_limit
        self.deadline = None

    # ---------- ПУБЛИЧНЫЙ ИНТЕРФЕЙС ----------

    def get_move(self):
        if self.game.current_turn != self.bot_side:
            return None

        moves = self.game.get_all_legal_moves()
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]

        self.deadline = time.time() + self.time_limit
        self.timed_out = False

        best_move = moves[0]
        # Итеративное углубление: считаем на 1, потом на 2, ... — прерываемся по времени
        for d in range(1, self.depth + 1):
            try:
                m = self._search_root(d)
                if m is not None:
                    best_move = m
            except TimeoutError:
                break
            if time.time() > self.deadline:
                break

        return best_move

    def make_move(self):
        move = self.get_move()
        if not move:
            return False
        kind, start, end = move
        if kind == "MOVE":
            return self.game.make_move(start, end)
        else:
            return self.game.place_boy(end)

    # ---------- ПОИСК ----------

    def _search_root(self, depth):
        """Перебор ходов в корне — выбираем лучший по оценке."""
        moves = self._order_moves(self.game.get_all_legal_moves())
        is_max = (self.game.current_turn == self.bot_side)

        best_score = -float("inf") if is_max else float("inf")
        best_move = None
        snap = self._snapshot()

        for move in moves:
            self._apply(move)
            score = self._minimax(depth - 1, -float("inf"), float("inf"), not is_max)
            self._restore(snap)

            if is_max and score > best_score:
                best_score, best_move = score, move
            elif not is_max and score < best_score:
                best_score, best_move = score, move

        return best_move

    def _minimax(self, depth, alpha, beta, is_max):
        if time.time() > self.deadline:
            raise TimeoutError()

        winner = self.game.check_winner()
        if winner is not None:
            # Терминальная позиция. Чем раньше победа — тем лучше.
            if winner == self._my_win_str():
                return 100_000 + depth
            return -100_000 - depth

        if depth == 0:
            return self._evaluate()

        moves = self._order_moves(self.game.get_all_legal_moves())
        if not moves:
            return self._evaluate()

        snap = self._snapshot()

        if is_max:
            best = -float("inf")
            for move in moves:
                self._apply(move)
                score = self._minimax(depth - 1, alpha, beta, False)
                self._restore(snap)
                best = max(best, score)
                alpha = max(alpha, score)
                if alpha >= beta:
                    break
            return best
        else:
            best = float("inf")
            for move in moves:
                self._apply(move)
                score = self._minimax(depth - 1, alpha, beta, True)
                self._restore(snap)
                best = min(best, score)
                beta = min(beta, score)
                if alpha >= beta:
                    break
            return best

    # ---------- ОЦЕНКА ----------

    def _evaluate(self):
        """
        Оценка позиции с точки зрения бота.
        Больше — лучше для бота.
        """
        boys_on_board = sum(1 for p in self.game.board.values() if p == BOY)
        total_boys = boys_on_board + self.game.unused_boys

        bull_mobility = 0
        for node, piece in self.game.board.items():
            if piece == BULL:
                # обычные шаги
                for nb in board_nodes.get(node, []):
                    if self.game.board.get(nb) == EMPTY:
                        bull_mobility += 1
                # прыжки (съедания) — гораздо важнее
                for mid, landing in possible_moves.get(node, []):
                    if (self.game.board.get(landing) == EMPTY
                            and self.game.board.get(mid) == BOY):
                        bull_mobility += 5

        if self.bot_side == BULL:
            # Бык хочет: съесть побольше, не быть зажатым
            return (24 - total_boys) * 50 + bull_mobility * 3
        else:
            # Мальчик хочет: сохранить фигуры, зажать быков
            return total_boys * 50 - bull_mobility * 3

    def _my_win_str(self):
        return "BULLS" if self.bot_side == BULL else "BOYS"

    # ---------- УТИЛИТЫ ----------

    def _apply(self, move):
        kind, start, end = move
        if kind == "MOVE":
            self.game.make_move(start, end)
        else:
            self.game.place_boy(end)

    def _snapshot(self):
        """Сохраняем всё изменяемое состояние игры."""
        return (
            self.game.board.copy(),
            self.game.current_turn,
            self.game.unused_boys,
        )

    def _restore(self, snap):
        board, turn, unused = snap
        self.game.board = dict(board)  # ← копия, а не ссылка
        self.game.current_turn = turn
        self.game.unused_boys = unused

    def _order_moves(self, moves):
        """
        Сначала съедания, потом остальное.
        С правильным порядком альфа-бета режет гораздо больше ветвей.
        """
        captures, others = [], []
        for m in moves:
            kind, start, end = m
            if kind == "MOVE" and end not in board_nodes.get(start, []):
                captures.append(m)
            else:
                others.append(m)
        return captures + others