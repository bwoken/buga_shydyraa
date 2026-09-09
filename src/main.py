import flet as ft
import flet.canvas as cv
import math
import logic  # Твой новый ООП logic.py


def main(page: ft.Page):
    page.title = "Buga Shydyraa"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE  # Для мобилок и маленьких экранов

    def choose_mode(e):
        nonlocal chosen_mode
        chosen_mode = e.control.data
        choose_mode_dialog.open = False

    choose_mode_dialog = ft.AlertDialog(title=ft.Text("Choose mode"),
                                        actions=[ft.TextButton("Local",data="local",on_click=choose_mode),
                                                ft.TextButton("Against bot",data="vs bot",on_click = choose_mode,disabled=True)],)
    page.show_dialog(choose_mode_dialog)
    chosen_mode = None

    # --- 1. СОЗДАЕМ ОБЪЕКТ ИГРЫ ---
    game = logic.BugaGame()
    selected_node = None
    legal_moves_for_selected = []

    # --- 2. ЭЛЕМЕНТЫ UI ---
    turn_text = ft.Text(value="TURN: BULLS", size=24, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
    boys_text = ft.Text(value=f"BOYS TO PLACE: {game.unused_boys}", size=24, color=ft.Colors.RED_400,
                        weight=ft.FontWeight.BOLD)

    game_info_row = ft.Row(
        [turn_text, boys_text],
        alignment=ft.MainAxisAlignment.SPACE_AROUND
    )

    def update_ui_text():
        """Обновляет текст хода и количества мальчиков."""
        turn_text.value = "TURN: BULLS" if game.current_turn == logic.BULL else "TURN: BOYS"
        boys_text.value = f"BOYS TO PLACE: {game.unused_boys}"

        # Если мальчиков в кармане нет, можно убрать надпись или сделать ее зеленой
        if game.unused_boys == 0:
            boys_text.color = ft.Colors.GREEN
            boys_text.value = "ALL BOYS PLACED"
        else:
            boys_text.color = ft.Colors.RED_400

    # --- 3. ОТРИСОВКА ДОСКИ ---
    def draw_board():
        """Рисует доску, читая состояние из объекта game.board."""
        shapes = []
        drawn_connections = set()


        # КОД ОТРИСОВКИ ЛИНИЙ
        for start_node, neighbors in logic.board_nodes.items():
            for end_node in neighbors:
                # Сортируем id, чтобы (1, 2) и (2, 1) считались одной связью
                connection = tuple(sorted((start_node, end_node)))
                if connection not in drawn_connections:
                    x1, y1 = logic.NODE_COORDS[start_node]
                    x2, y2 = logic.NODE_COORDS[end_node]
                    shapes.append(
                        cv.Line(
                            x1, y1, x2, y2,
                            ft.Paint(stroke_width=2, color=ft.Colors.BLACK)
                        )
                    )
                    drawn_connections.add(connection)

        # --- ВИЗУАЛИЗАЦИЯ ВОЗМОЖНЫХ ХОДОВ (под фигурами) ---
        for node_id in legal_moves_for_selected:
            x, y = logic.NODE_COORDS[node_id]
            # Рисуем зеленый кружок с пульсирующим эффектом
            shapes.append(
                cv.Circle(
                    x, y, 20,
                    ft.Paint(
                        color=ft.Colors.GREEN,
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=3,
                    )
                )
            )
            # Внутренний кружок (полупрозрачный)
            shapes.append(
                cv.Circle(
                    x, y, 15,
                    ft.Paint(
                        color=ft.Colors.with_opacity(0.3,ft.Colors.GREEN),
                        style=ft.PaintingStyle.FILL,
                    )
                )
            )

        # Отрисовка узлов и фигур
        for node_id, coords in logic.NODE_COORDS.items():
            x, y = coords
            piece = game.board.get(node_id)

            # Подсветка выбранной фигуры
            if selected_node == node_id:
                shapes.append(cv.Circle(x, y, 25, ft.Paint(color=ft.Colors.YELLOW, style=ft.PaintingStyle.FILL)))

            # Отрисовка самих фигур
            if piece == logic.BULL:
                shapes.append(cv.Circle(x, y, 20, ft.Paint(color=ft.Colors.GREY_300, style=ft.PaintingStyle.FILL)))
            elif piece == logic.BOY:
                shapes.append(cv.Circle(x, y, 15, ft.Paint(color=ft.Colors.BLUE, style=ft.PaintingStyle.FILL)))
            else:
                # Пустой узел
                shapes.append(cv.Circle(x, y, 5, ft.Paint(color=ft.Colors.BLACK, style=ft.PaintingStyle.FILL)))

        # Отрисовка номера узла
        for node_id, coords in logic.NODE_COORDS.items():
            x, y = coords
            shapes.append(cv.Text(x, y, spans=[ft.TextSpan(text=str(node_id),style=ft.TextStyle(color=ft.Colors.AMBER,weight=ft.FontWeight.BOLD))]))
        return cv.Canvas(shapes=shapes, expand=True)

    # --- 4. ОБРАБОТКА КЛИКА ---
    def on_board_click(e: ft.TapEvent):
        nonlocal selected_node,legal_moves_for_selected

        clicked_node = None
        legal_moves_for_selected = []
        # Ищем, по какому узлу кликнули
        for node_id, coords in logic.NODE_COORDS.items():
            dist = math.hypot(e.local_position.x - coords[0], e.local_position.y - coords[1])
            if dist <= 30:  # Увеличили радиус клика для удобства
                clicked_node = node_id
                break

        if not clicked_node:
            return

        # Логика Мальчика
        if game.current_turn == logic.BOY:
            if game.unused_boys > 0:
                # Если есть запас - только выставляем
                if game.place_boy(clicked_node):
                    selected_node = None
            else:
                # Если запаса нет - выбираем и ходим
                if selected_node is None:
                    if game.board.get(clicked_node) == logic.BOY:
                        selected_node = clicked_node
                        legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
                else:
                    if game.make_move(selected_node, clicked_node):
                        selected_node = None
                    else:
                        # Перевыбор фигуры, если кликнули на своего
                        if game.board.get(clicked_node) == logic.BOY:
                            selected_node = clicked_node
                            legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)
                        # Снятие выделения с мальчика если кликнули на чужую фигуру
                        else:
                            selected_node = None
                            legal_moves_for_selected = []

        # Логика Быка
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
                    # Перевыбор быка если нажали на своего
                    if game.board.get(clicked_node) == logic.BULL:
                        selected_node = clicked_node
                        legal_moves_for_selected = game.get_legal_moves_for_node(selected_node)

                    # Снятие выделения если нажали на чужую фигуру
                    else:
                        selected_node = None
                        legal_moves_for_selected = []
        # Проверка победы
        winner = game.check_winner()
        if winner:
            win_dialog.title.value = f"{winner} WON!"
            page.show_dialog(win_dialog)
            win_dialog.open = True
        update_ui_text()
        board_gest_detector.content = draw_board()
        page.update()

    # --- 5. СБРОС ИГРЫ ---
    def restart_game(e):
        nonlocal game, selected_node
        # Просто создаем новую чистую игру! Никаких проблем со словарями.
        game = logic.BugaGame()
        selected_node = None

        win_dialog.open = False
        update_ui_text()
        board_gest_detector.content = draw_board()
        page.update()

    # Диалог победы
    win_dialog = ft.AlertDialog(
        title=ft.Text(""),
        actions=[ft.TextButton("Play Again", on_click=restart_game)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # --- 6. СБОРКА ИНТЕРФЕЙСА ---
    board_gest_detector = ft.GestureDetector(
        on_tap_down=on_board_click,
        content=draw_board(),
    )

    board_container = ft.Container(
        bgcolor=ft.Colors.BROWN,
        width=500,  # Подстрой под свой BOARD_WIDTH
        height=800,  # Подстрой под свой BOARD_HEIGHT
        content=ft.Column(
            [game_info_row, board_gest_detector],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.Alignment.CENTER,
        padding=20,
    )
    lower_bar = ft.BottomAppBar(content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND))
    page.add(board_container,lower_bar)


if __name__ == "__main__":
    ft.run(main)