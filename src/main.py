import flet as ft
import flet.canvas as cv
import math
import asyncio
import logic
from board import draw_board
from bot import EasyBot,SmartBot

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
    reset_button = ft.Button("RESET",on_click=lambda e: restart_game())
    undo_button = ft.Button("UNDO",on_click=lambda e: undo_move(e))

    game_info_row = ft.Row(
        [turn_text, boys_text, undo_button,reset_button],
        alignment=ft.MainAxisAlignment.CENTER,spacing=10,wrap=True
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

    def refresh_board():
        """Обновляет текст, доску и UI."""
        update_ui_text()
        board_gest_detector.content = draw_board(game, selected_node, legal_moves_for_selected)
        page.update()

    def show_game_over(result: str):
        """Показывает диалог окончания игры."""
        if result == logic.BULLS_WIN:
            win_dialog.title.value = "BULLS WON"
            win_dialog.content = ft.Text("Not enough boys left")
        elif result == logic.BOYS_WIN:
            win_dialog.title.value = "BOYS WON"
            win_dialog.content = ft.Text("Bulls are blocked")
        elif result == logic.DRAW_NO_CAPTURE:
            win_dialog.title.value = "DRAW"
            win_dialog.content = ft.Text("30 moves by each side without capturing")
        elif result == logic.DRAW_REPETITION:
            win_dialog.title.value = "DRAW"
            win_dialog.content = ft.Text("Position repeated three times")
        page.show_dialog(win_dialog)

    # ---------- ОТРИСОВКА ДОСКИ ----------

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
                show_game_over(winner)

            refresh_board()

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
            show_game_over(winner)
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
            show_game_over(winner)

        refresh_board()

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

    def undo_move(e):
        """Откатывает последний ход игрока (+ ответы бота в режиме vs bot)."""
        nonlocal selected_node, legal_moves_for_selected, is_bot_turn

        # если бот думает — не трогаем
        if is_bot_turn:
            return

        # в локальном режиме откатываем один ход
        if bot is None:
            if not game.undo_last():
                return
        else:
            # в vs bot откатываем до последнего хода игрока
            player_side = logic.BOY if bot_side == logic.BULL else logic.BULL
            if not game.undo_player_move(player_side):
                return

        # сброс визуального состояния и диалогов
        selected_node = None
        legal_moves_for_selected = []
        win_dialog.open = False

        refresh_board()

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
        elif mode == "vs_easy_bot_bulls":   # легкий бот за быков
            bot_side = logic.BULL
            bot = EasyBot(game, bot_side)
        elif mode == "vs_easy_bot_boys":    # легкий бот за мальчиков
            bot_side = logic.BOY
            bot = EasyBot(game, bot_side)
        elif mode == "vs_smart_bot_bulls":   # умный бот за быков
            bot_side = logic.BULL
            bot = SmartBot(game, bot_side)
        elif mode == "vs_smart_bot_boys":    # умный бот за мальчиков
            bot_side = logic.BOY
            bot = SmartBot(game, bot_side)

        choose_mode_dialog.open = False
        refresh_board()

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
                ft.Row(controls=[ft.Text("Against bot")]),
                ft.Text("Easy bot:"),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Play as Boys",
                            on_click=lambda e: start_game("vs_easy_bot_bulls"),
                        ),
                        ft.OutlinedButton(
                            "Play as Bulls",
                            on_click=lambda e: start_game("vs_easy_bot_boys"),
                        ),
                    ],
                ),
                ft.Text("Smart bot:"),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Play as Boys",
                            on_click=lambda e: start_game("vs_smart_bot_bulls"),
                        ),
                        ft.OutlinedButton(
                            "Play as Bulls",
                            on_click=lambda e: start_game("vs_smart_bot_boys"),
                        ),
                    ],
                )
            ],
        ),
    )

    # ---------- СБОРКА UI ----------
    board_gest_detector = ft.GestureDetector(
        on_tap_down=on_board_click,
        content=draw_board(game,selected_node,legal_moves_for_selected),
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