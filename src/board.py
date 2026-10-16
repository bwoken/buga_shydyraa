# board.py
import flet.canvas as cv
import flet as ft
from logic import NODE_COORDS, board_nodes, BULL, BOY, EMPTY


def draw_board(game, selected_node, legal_moves) -> cv.Canvas:
    shapes = []
    drawn = set()

    # линии
    for start, neighbors in board_nodes.items():
        for end in neighbors:
            key = tuple(sorted((start, end)))
            if key in drawn:
                continue
            x1, y1 = NODE_COORDS[start]
            x2, y2 = NODE_COORDS[end]
            shapes.append(cv.Line(x1, y1, x2, y2,
                                  ft.Paint(stroke_width=2, color=ft.Colors.BLACK)))
            drawn.add(key)

    # подсветка возможных ходов
    for node in legal_moves:
        x, y = NODE_COORDS[node]
        shapes.append(cv.Circle(x, y, 20, ft.Paint(
            color=ft.Colors.GREEN, style=ft.PaintingStyle.STROKE, stroke_width=3)))
        shapes.append(cv.Circle(x, y, 15, ft.Paint(
            color=ft.Colors.with_opacity(0.3, ft.Colors.GREEN),
            style=ft.PaintingStyle.FILL)))

    # фигуры
    for node, (x, y) in NODE_COORDS.items():
        piece = game.board.get(node)
        if selected_node == node:
            shapes.append(cv.Circle(x, y, 25, ft.Paint(
                color=ft.Colors.YELLOW, style=ft.PaintingStyle.FILL)))
        if piece == BULL:
            shapes.append(cv.Circle(x, y, 20, ft.Paint(
                color=ft.Colors.GREY_300, style=ft.PaintingStyle.FILL)))
        elif piece == BOY:
            shapes.append(cv.Circle(x, y, 15, ft.Paint(
                color=ft.Colors.BLUE, style=ft.PaintingStyle.FILL)))
        else:
            shapes.append(cv.Circle(x, y, 5, ft.Paint(
                color=ft.Colors.BLACK, style=ft.PaintingStyle.FILL)))

    # номера узлов
    for node, (x, y) in NODE_COORDS.items():
        shapes.append(cv.Text(x, y, spans=[ft.TextSpan(
            text=str(node),
            style=ft.TextStyle(color=ft.Colors.AMBER, weight=ft.FontWeight.BOLD))]))

    return cv.Canvas(shapes=shapes, expand=True)