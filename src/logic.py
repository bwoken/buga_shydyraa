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
               13: [7, 8, 9, 12, 21, 14, 17, 18, 19],
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
                  27: [(21, 15), (22, 17), (23, 19), (28, 29), (32, 35), (31, 34), (30, 33)],
                  28: [(23, 18), (27, 26)],
                  29: [(23, 17), (24, 19), (28, 27)],
                  30: [(27, 23), (31, 32)],
                  31: [(27, 22)],
                  32: [(27, 21), (31, 30)],
                  33: [(30, 27), (34, 35)],
                  34: [(31, 27)],
                  35: [(32, 27), (34, 33)]}

EMPTY = 0
BULL = 1
BOY = -1

def initialize_board() -> dict:
    board_state = {}
    for i in range(1, 36):
        board_state[i] = EMPTY

    board_state[7] = BULL
    board_state[27] = BULL
    boy_nodes = [11, 12, 13, 16, 18, 21, 22, 23]
    for i in boy_nodes:
        board_state[i] = BOY

    return board_state


current_board_state = initialize_board()

# coordinates for board canvas
UNIT = 70.0 # minimal distance between nodes
OFFSET_X = 40.0   # Маленький отступ слева/справа
OFFSET_Y = 250.0  # Большой отступ сверху, чтобы влезла "голова"

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

selected_piece = None
current_turn = BULL
unused_boys = 16
initial_boys = 8
boys = unused_boys + initial_boys

def is_valid_move(start_node_id: int,end_node_id: int) -> bool:
    global current_turn
    # checking if end node or chosen node are empty
    if current_board_state.get(end_node_id) != EMPTY or current_board_state.get(start_node_id) == EMPTY:
        return False

    # right side to make a move
    if current_board_state.get(start_node_id) != current_turn:
        return False
    # checking if moving to node is possible (if there is a connection between start node and end node)
    if end_node_id in board_nodes.get(start_node_id,[]):
        return True

    # capturing
    if start_node_id in possible_moves:
        for boy_node, landing_node in possible_moves[start_node_id]:
            if landing_node == end_node_id:
                if current_board_state[boy_node] == BOY and current_board_state[start_node_id] == BULL:
                    return True

    return False

def make_move(start_node: int, end_node: int):
    global current_turn,initial_boys
    if is_valid_move(start_node,end_node):
        # moving the piece
        current_board_state[start_node],current_board_state[end_node] = current_board_state[end_node],current_board_state[start_node]
        if end_node not in board_nodes[start_node]:
            # removing the boy if move is a capture
            for boy_node,end_node_iter in possible_moves[start_node]:
                if end_node_iter == end_node:
                    current_board_state[boy_node] = EMPTY
                    initial_boys -= 1
        # handing move to other player
        current_turn = -current_turn
