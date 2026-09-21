import flet as ft
import flet.canvas as cv
import math
import asyncio
import logic
from bot import EasyBot

def main(page: ft.Page):
    page.title = "Buga Shydyraa"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # ---------- СОСТОЯНИЕ ----------
    chosen_mode = None
    game = logic.BugaGame()
    bot = None
    bot_side = None
    is_bot_turn = False
    selected_node = None
    legal_moves_for_selected = []

    # ---------- UI ЭЛЕМЕНТЫ ----------
    turn_text = ft.Text(value="TURN: BULLS", size=24,
                        color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
    boys_text = ft.Text(value=f"BOYS TO PLACE: {game.unused_boys}", size=24,
                        color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD)

    game_info_row = ft.Row(
        [turn_text, boys_text],
        alignment=ft.MainAxisAlignment.SPACE_AROUND
    )

    win_dialog = ft.AlertDialog(
        title=ft.Text(""),
        actions=[ft.TextButton("Play Again", on_click=lambda e: restart_game())],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def update_ui_text():
        turn_text.value = "TURN: BULLS" if game.current_turn == logic.BULL else "TURN: BOYS"
        turn_text.color = ft.Colors.WHITE if game.current_turn == logic.BULL else ft.Colors.BLUE
        boys_text.value = f"BOYS TO PLACE: {game.unused_boys}"
        if game.unused_boys == 0:
            boys_text.color = ft.Colors.GREEN
            boys_text.value = "ALL BOYS PLACED"
        else:
            boys_text.color = ft.Colors.RED_400

    # ---------- ОТРИСОВКА ДОСКИ ----------
    def draw_board():
        shapes = []
        drawn_connections = set()

        # линии
        for start_node, neighbors in logic.board_nodes.items():
            for end_node in neighbors:
                connection = tuple(sorted((start_node, end_node)))
                if connection not in drawn_connections:
                    x1, y1 = logic.NODE_COORDS[start_node]
                    x2, y2 = logic.NODE_COORDS[end_node]
                    shapes.append(
                        cv.Line(x1, y1, x2, y2,
                                ft.Paint(stroke_width=2, color=ft.Colors.BLACK))
                    )
                    drawn_connections.add(connection)

        # подсветка возможных ходов
        for node_id in legal_moves_for_selected:
            x, y = logic.NODE_COORDS[node_id]
            shapes.append(cv.Circle(
                x, y, 20,
                ft.Paint(color=ft.Colors.GREEN,
                         style=ft.PaintingStyle.STROKE, stroke_width=3)
            ))
            shapes.append(cv.Circle(
                x, y, 15,
                ft.Paint(color=ft.Colors.with_opacity(0.3, ft.Colors.GREEN),
                         style=ft.PaintingStyle.FILL)
            ))

        # фигуры
        for node_id, coords in logic.NODE_COORDS.items():
            x, y = coords
            piece = game.board.get(node_id)

            if selected_node == node_id:
                shapes.append(cv.Circle(
                    x, y, 25,
                    ft.Paint(color=ft.Colors.YELLOW, style=ft.PaintingStyle.FILL)
                ))

            if piece == logic.BULL:
                shapes.append(cv.Circle(
                    x, y, 20,
                    ft.Paint(color=ft.Colors.GREY_300, style=ft.PaintingStyle.FILL)
                ))
            elif piece == logic.BOY:
                shapes.append(cv.Circle(
                    x, y, 15,
                    ft.Paint(color=ft.Colors.BLUE, style=ft.PaintingStyle.FILL)
                ))
            else:
                shapes.append(cv.Circle(
                    x, y, 5,
                    ft.Paint(color=ft.Colors.BLACK, style=ft.PaintingStyle.FILL)
                ))

        # номера узлов (дебаг)
        for node_id, coords in logic.NODE_COORDS.items():
            x, y = coords
            shapes.append(cv.Text(
                x, y,
                spans=[ft.TextSpan(
                    text=str(node_id),
                    style=ft.TextStyle(color=ft.Colors.AMBER,
                                       weight=ft.FontWeight.BOLD)
                )]
            ))

        return cv.Canvas(shapes=shapes, expand=True)

    # ---------- ХОД БОТА ----------
    async def make_bot_move():
        nonlocal is_bot_turn, selected_node, legal_moves_for_selected

        if not bot or game.current_turn != bot_side:
            is_bot_turn = False
            return

        is_bot_turn = True
        await asyncio.sleep(0.4)

        if bot.make_move():
            selected_node = None
            legal_moves_for_selected = []

            winner = game.check_winner()
            if winner:
                win_dialog.title.value = f"{winner} WON!"
                page.show_dialog(win_dialog)

            update_ui_text()
            board_gest_detector.content = draw_board()
            page.update()

            if game.current_turn == bot_side and not winner:
                page.run_task(make_bot_move)
            else:
                is_bot_turn = False
        else:
            is_bot_turn = False

    # ---------- КЛИК ПО ДОСКЕ ----------
    def on_board_click(e: ft.TapEvent):
        nonlocal selected_node, legal_moves_for_selected

        winner = game.check_winner()
        if winner:
            win_dialog.title.value = f"{winner} WON!"
            page.show_dialog(win_dialog)
            return

        if is_bot_turn or (bot and game.current_turn == bot_side):
            return

        clicked_node = None
        for node_id, coords in logic.NODE_COORDS.items():
            dist = math.hypot(e.local_position.x - coords[0],
                              e.local_position.y - coords[1])
            if dist <= 30:
                clicked_node = node_id
                break

        if not clicked_node:
            return

        # логика мальчика
        if game.current_turn == logic.BOY:
            if game.unused_boys > 0:
                if game.place_boy(clicked_node):
                    selected_node = None
                    legal_moves_for_selected = []
            else:
                if selected_node is None:
                    if game.board.get(clicked_node) == logic.BOY:
                        selected_node = clicked_node
                        legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
                else:
                    if game.make_move(selected_node, clicked_node):
                        selected_node = None
                        legal_moves_for_selected = []
                    else:
                        if game.board.get(clicked_node) == logic.BOY:
                            selected_node = clicked_node
                            legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
                        else:
                            selected_node = None
                            legal_moves_for_selected = []

        # логика быка
        elif game.current_turn == logic.BULL:
            if selected_node is None:
                if game.board.get(clicked_node) == logic.BULL:
                    selected_node = clicked_node
                    legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
            else:
                if game.make_move(selected_node, clicked_node):
                    selected_node = None
                    legal_moves_for_selected = []
                else:
                    if game.board.get(clicked_node) == logic.BULL:
                        selected_node = clicked_node
                        legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
                    else:
                        selected_node = None
                        legal_moves_for_selected = []

        winner = game.check_winner()
        if winner:
            win_dialog.title.value = f"{winner} WON!"
            page.show_dialog(win_dialog)

        update_ui_text()
        board_gest_detector.content = draw_board()
        page.update()

        if bot and game.current_turn == bot_side and not winner:
            page.run_task(make_bot_move)

    # ---------- СБРОС ----------
    def restart_game():
        """Открывает окно выбора режима заново."""
        nonlocal is_bot_turn, selected_node, legal_moves_for_selected

        # сбрасываем всё, чтобы клики не уходили в старую игру
        is_bot_turn = False
        selected_node = None
        legal_moves_for_selected = []

        win_dialog.open = False
        page.update()

        choose_mode_dialog.open = True
        page.show_dialog(choose_mode_dialog)
        page.update()

    # ---------- СТАРТ ИГРЫ (выбор режима) ----------
    def start_game(mode: str):
        nonlocal chosen_mode, game, bot, bot_side, is_bot_turn
        nonlocal selected_node, legal_moves_for_selected

        chosen_mode = mode
        game = logic.BugaGame()
        selected_node = None
        legal_moves_for_selected = []
        is_bot_turn = False

        if mode == "local":
            bot, bot_side = None, None
        elif mode == "vs_bot_bulls":   # бот за быков
            bot_side = logic.BULL
            bot = EasyBot(game, bot_side)
        elif mode == "vs_bot_boys":    # бот за мальчиков
            bot_side = logic.BOY
            bot = EasyBot(game, bot_side)

        choose_mode_dialog.open = False
        update_ui_text()
        board_gest_detector.content = draw_board()
        page.update()

        if bot and game.current_turn == bot_side:
            page.run_task(make_bot_move)

    choose_mode_dialog = ft.AlertDialog(
        title=ft.Text("Choose mode"),
        content=ft.Column(
            tight=True,
            spacing=12,
            controls=[
                ft.FilledButton(
                    "Local (2 players)",
                    width=240,
                    on_click=lambda e: start_game("local"),
                ),
                ft.Divider(),
                ft.Text("Against bot:"),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Play as Boys",
                            on_click=lambda e: start_game("vs_bot_bulls"),
                        ),
                        ft.OutlinedButton(
                            "Play as Bulls",
                            on_click=lambda e: start_game("vs_bot_boys"),
                        ),
                    ],
                ),
            ],
        ),
    )

    # ---------- СБОРКА UI ----------
    board_gest_detector = ft.GestureDetector(
        on_tap_down=on_board_click,
        content=draw_board(),
    )

    board_container = ft.Container(
        bgcolor=ft.Colors.BROWN,
        width=500,
        height=800,
        content=ft.Column(
            [game_info_row, board_gest_detector],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.Alignment.CENTER,
        padding=20,
    )

    page.add(board_container)
    page.show_dialog(choose_mode_dialog)
    update_ui_text()


if __name__ == "__main__":
    ft.run(main)