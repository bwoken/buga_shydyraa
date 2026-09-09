# nodes and their connections to other nodes
board_nodes = {1: [2, 3, 4],
               2: [1, 3, 7],
               3: [1, 2, 4, 7],
               4: [1, 3, 7],
               5: [6, 11, 10],
               6: [5, 11, 7],
               7: [2, 3, 4, 6, 11, 12, 13, 8],
               8: [7, 13, 9],
               9: [8, 13, 14],
               10: [5, 11, 15],
               11: [5, 6, 7, 10, 12, 15, 16, 17],
               12: [11, 7, 13, 17],
               13: [7, 8, 9, 12, 14, 17, 18, 19],
               14: [9, 13, 19],
               15: [10, 11, 16, 21, 20],
               16: [15, 11, 17, 21],
               17: [11, 12, 13, 16, 18, 21, 22, 23],
               18: [17, 13, 19, 23],
               19: [13, 14, 18, 23, 24],
               20: [15, 21, 25],
               21: [15, 16, 17, 20, 22, 25, 26, 27],
               22: [17, 21, 23, 27],
               23: [17, 18, 19, 22, 24, 27, 28, 29],
               24: [19, 23, 29],
               25: [20, 21, 26],
               26: [21, 25, 27],
               27: [21, 22, 23, 26, 28, 30, 31, 32],
               28: [23, 27, 29],
               29: [23, 24, 28],
               30: [27, 31, 33],
               31: [27, 30, 32, 34],
               32: [27, 31, 35],
               33: [30, 34],
               34: [31, 33, 35],
               35: [32, 34]}
# key - starting node, first in the tuple - middle point (where boy should be), second in the tuple - endpoint
possible_moves = {1: [(3, 7)],
                  2: [(7, 13), (3, 4)],
                  3: [(7, 12)],
                  4: [(3, 2), (7, 11)],
                  5: [(6, 7), (11, 17), (10, 15)],
                  6: [(7, 8), (11, 16)],
                  7: [(3, 1), (6, 5), (8, 9), (11, 15), (12, 17), (13, 19)],
                  8: [(7, 6), (13, 18)],
                  9: [(8, 7), (13, 17), (14, 19)],
                  10: [(11, 12), (15, 20)],
                  11: [(12, 13), (17, 23), (16, 21), (7, 4)],
                  12: [(7, 3), (11, 10), (13, 14), (17, 22)],
                  13: [(7, 2), (12, 11), (17, 21), (18, 23)],
                  14: [(13, 12), (19, 24)],
                  15: [(10, 5), (11, 7), (16, 17), (21, 27), (20, 25)],
                  16: [(11, 6), (17, 18), (21, 26)],
                  17: [(11, 5), (12, 7), (13, 9), (18, 19), (23, 29), (22, 27), (21, 25), (16, 15)],
                  18: [(13, 8), (17, 16), (23, 28)],
                  19: [(13, 7), (14, 9), (18, 17), (23, 27), (24, 29)],
                  20: [(15, 10), (21, 22)],
                  21: [(16, 11), (17, 13), (22, 23), (27, 32)],
                  22: [(17, 12), (23, 24), (27, 31), (21, 20)],
                  23: [(17, 11), (18, 13), (22, 21), (27, 30)],
                  24: [(19, 14), (23, 22)],
                  25: [(20, 15), (21, 17), (26, 27)],
                  26: [(21, 16), (27, 28)],
                  27: [(21, 15), (22, 17), (23, 19), (26,25), (28, 29), (32, 35), (31, 34), (30, 33)],
                  28: [(23, 18), (27, 26)],
                  29: [(23, 17), (24, 19), (28, 27)],
                  30: [(27, 23), (31, 32)],
                  31: [(27, 22)],
                  32: [(27, 21), (31, 30)],
                  33: [(30, 27), (34, 35)],
                  34: [(31, 27)],
                  35: [(32, 27), (34, 33)]}

# coordinates for board canvas
UNIT = 70.0 # minimal distance between nodes
OFFSET_X = 40.0   # Маленький отступ слева/справа
OFFSET_Y = 165.0  # Большой отступ сверху, чтобы влезла "голова"

NODE_COORDS = {
    # --- Голова и Шея ---
    # Y отсчитывается от OFFSET_Y (250) минус 3 юнита (210) = 40. Все координаты положительные!
    1: (OFFSET_X + 2 * UNIT, OFFSET_Y - 2 * UNIT),
    2: (OFFSET_X + 1 * UNIT, OFFSET_Y - 1 * UNIT),
    3: (OFFSET_X + 2 * UNIT, OFFSET_Y - 1 * UNIT),
    4: (OFFSET_X + 3 * UNIT, OFFSET_Y - 1 * UNIT),

    # --- Плечи ---
    5: (OFFSET_X, OFFSET_Y),
    6: (OFFSET_X + 1 * UNIT, OFFSET_Y),
    7: (OFFSET_X + 2 * UNIT, OFFSET_Y),
    8: (OFFSET_X + 3 * UNIT, OFFSET_Y),
    9: (OFFSET_X + 4 * UNIT, OFFSET_Y),

    # --- Сетка 5x5 ---
    # Row 1
    10: (OFFSET_X, OFFSET_Y + 1 * UNIT),
    11: (OFFSET_X + 1 * UNIT, OFFSET_Y + 1 * UNIT),
    12: (OFFSET_X + 2 * UNIT, OFFSET_Y + 1 * UNIT),
    13: (OFFSET_X + 3 * UNIT, OFFSET_Y + 1 * UNIT),
    14: (OFFSET_X + 4 * UNIT, OFFSET_Y + 1 * UNIT),

    # Row 2
    15: (OFFSET_X, OFFSET_Y + 2 * UNIT),
    16: (OFFSET_X + 1 * UNIT, OFFSET_Y + 2 * UNIT),
    17: (OFFSET_X + 2 * UNIT, OFFSET_Y + 2 * UNIT),
    18: (OFFSET_X + 3 * UNIT, OFFSET_Y + 2 * UNIT),
    19: (OFFSET_X + 4 * UNIT, OFFSET_Y + 2 * UNIT),

    # Row 3
    20: (OFFSET_X, OFFSET_Y + 3 * UNIT),
    21: (OFFSET_X + 1 * UNIT, OFFSET_Y + 3 * UNIT),
    22: (OFFSET_X + 2 * UNIT, OFFSET_Y + 3 * UNIT),
    23: (OFFSET_X + 3 * UNIT, OFFSET_Y + 3 * UNIT),
    24: (OFFSET_X + 4 * UNIT, OFFSET_Y + 3 * UNIT),

    # Row 4 (Основание квадрата)
    25: (OFFSET_X, OFFSET_Y + 4 * UNIT),
    26: (OFFSET_X + 1 * UNIT, OFFSET_Y + 4 * UNIT),
    27: (OFFSET_X + 2 * UNIT, OFFSET_Y + 4 * UNIT),
    28: (OFFSET_X + 3 * UNIT, OFFSET_Y + 4 * UNIT),
    29: (OFFSET_X + 4 * UNIT, OFFSET_Y + 4 * UNIT),

    # --- Ноги ---
    30: (OFFSET_X + 1 * UNIT, OFFSET_Y + 5 * UNIT),
    31: (OFFSET_X + 2 * UNIT, OFFSET_Y + 5 * UNIT),
    32: (OFFSET_X + 3 * UNIT, OFFSET_Y + 5 * UNIT),

    33: (OFFSET_X, OFFSET_Y + 6 * UNIT),
    34: (OFFSET_X + 2 * UNIT, OFFSET_Y + 6 * UNIT),
    35: (OFFSET_X + 4 * UNIT, OFFSET_Y + 6 * UNIT),
}

# --- КОНСТАНТЫ ---
EMPTY = 0
BULL = 1
BOY = -1

class BugaGame:
    def __init__(self):
        # Состояние игры теперь хранится внутри объекта
        self.unused_boys = 16
        self.current_turn = BULL
        self.board = self.initialize_board()

    def initialize_board(self):
        """Создает доску и расставляет начальные фигуры."""
        # Создаем пустую доску (предполагаем 35 узлов, если у тебя 34 — исправь range)
        state = {i: EMPTY for i in range(1, 36)}

        # Расстановка быков (по твоим координатам)
        state[7] = BULL
        state[27] = BULL

        # Расстановка 8 начальных мальчиков
        for i in [11, 12, 13, 16, 18, 21, 22, 23]:
            state[i] = BOY

        return state

    def is_valid_move(self, start, end):
        """Проверяет, возможен ли ход по правилам."""
        if self.board.get(end) != EMPTY:
            return False

        piece = self.board.get(start)

        # ЛОГИКА МАЛЬЧИКА
        if piece == BOY:
            # Мальчики не могут ходить, пока карман не пуст!
            if self.unused_boys > 0:
                return False
            # Если карман пуст, могут ходить на соседние узлы
            if end in board_nodes.get(start, []):
                return True

        # ЛОГИКА БЫКА
        elif piece == BULL:
            # 1. Обычный шаг на соседний узел
            if end in board_nodes.get(start, []):
                return True
            # 2. Прыжок (съедание) через мальчика
            if start in possible_moves:
                for mid_node, landing_node in possible_moves[start]:
                    if landing_node == end and self.board.get(mid_node) == BOY:
                        return True

        return False

    def make_move(self, start, end):
        """Выполняет ход и обрабатывает съедание."""
        if not self.is_valid_move(start, end):
            return False

        piece = self.board[start]

        # Если ходит бык и это не обычный шаг (значит это прыжок)
        if piece == BULL and end not in board_nodes.get(start, []):
            if start in possible_moves:
                for mid_node, landing_node in possible_moves[start]:
                    if landing_node == end:
                        # Удаляем съеденного мальчика навсегда
                        self.board[mid_node] = EMPTY

                        # Выполняем перемещение
        self.board[end] = piece
        self.board[start] = EMPTY

        # Передаем ход
        self.current_turn = BOY if self.current_turn == BULL else BULL
        return True

    def place_boy(self, node_id):
        """Выставляет мальчика из 'кармана' на пустую клетку."""
        if self.current_turn == BOY and self.unused_boys > 0:
            if self.board.get(node_id) == EMPTY:
                self.board[node_id] = BOY
                self.unused_boys -= 1
                self.current_turn = BULL
                return True
        return False

    def can_bull_move(self):
        """Проверяет, есть ли у любого из быков хоть один законный ход."""
        # Ищем все позиции, где стоят быки
        bull_positions = [node for node, piece in self.board.items() if piece == BULL]

        for pos in bull_positions:
            # 1. Проверяем обычные шаги (соседние пустые узлы)
            neighbors = board_nodes.get(pos, [])
            for neighbor in neighbors:
                if self.board.get(neighbor) == EMPTY:
                    return True  # Нашли хоть один ход — быки не заблокированы

            # 2. Проверяем прыжки (бык может прыгнуть, если за мальчиком пусто)
            jumps = possible_moves.get(pos, [])
            for mid_node, landing_node in jumps:
                if (self.board.get(landing_node) == EMPTY and
                        self.board.get(mid_node) == BOY):
                    return True  # Бык может съесть мальчика — он не заблокирован

        return False  # Ни один бык не может ни шагнуть, ни прыгнуть

    def check_winner(self):
        """Проверка условий победы."""
        on_board_boys = sum(1 for p in self.board.values() if p == BOY)
        total_boys = on_board_boys + self.unused_boys

        # Условие победы БЫКОВ
        if total_boys < 4:
            return "BULLS"

        # Условие победы МАЛЬЧИКОВ (быки заблокированы)
        # ВАЖНО: Мальчики побеждают, если у быков НЕТ ходов
        if not self.can_bull_move():
            return "BOYS"

        return None
