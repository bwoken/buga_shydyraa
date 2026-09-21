import random
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
    pass