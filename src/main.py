import flet as ft
import flet.canvas as cv
import math

# USEFUL!!! maybe be shown as unused for some reason
from flet import TapEvent

import logic
from logic import (board_nodes,NODE_COORDS,
                   current_board_state,OFFSET_X,OFFSET_Y,UNIT,make_move,is_valid_move)

def main(page: ft.Page):
    page.title = 'Bull Chess'
    page.vertical_alignment = ft.MainAxisAlignment.SPACE_BETWEEN
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.bgcolor = ft.Colors.BLUE_GREY_50

    selected_node = None
    #detecting clicks on board
    def on_board_click(e: ft.TapEvent):
        nonlocal  selected_node
        click_x = e.local_position.x
        click_y = e.local_position.y
        CLICK_RADIUS = 20
        clicked_node_id = None
        for node_id, (nx,ny) in NODE_COORDS.items():
            distance = math.sqrt((click_x-nx)**2 + (click_y-ny)**2)
            if distance < CLICK_RADIUS:
                clicked_node_id = node_id
                break

        # STATE  MACHINE

        # placing boys until zero are left in "pocket"
        if logic.place_boy(clicked_node_id):
            current_turn_text.value = 'TURN: BULLS' if logic.current_turn == 1 else 'TURN: BOYS'
            current_turn_text.color = ft.Colors.GREY_400 if logic.current_turn == 1 else ft.Colors.CYAN
            unused_boys_text.value = f'BOYS TO PLACE: {logic.unused_boys}'
            selected_node = None
            new_board_canvas = draw_board()
            board_gest_detector.content = new_board_canvas
            page.update()
            return

        #1. nothing is selected, waiting selection state
        if selected_node is None:
            if current_board_state.get(clicked_node_id) == logic.current_turn:
                selected_node = clicked_node_id #selecting the node

        #2. deselecting if clicked on the selected
        else:
            if clicked_node_id == selected_node:
                selected_node = None

            # selecting other piece if clicked on current turn's piece
            elif current_board_state.get(clicked_node_id) == logic.current_turn:
                selected_node = clicked_node_id

            else: #moving
                if is_valid_move(selected_node,clicked_node_id):
                    make_move(selected_node,clicked_node_id)
                    current_turn_text.value = 'TURN: BULLS' if logic.current_turn == 1 else 'TURN: BOYS'
                    current_turn_text.color = ft.Colors.GREY_400 if logic.current_turn == 1 else ft.Colors.CYAN
                    selected_node = None
        new_board_canvas = draw_board()
        board_gest_detector.content = new_board_canvas
        page.update()


    # making the visual board
    def draw_board():
        line_paint = ft.Paint(stroke_width=2,color=ft.Colors.BLACK,stroke_cap=ft.StrokeCap.ROUND)
        bull_paint = ft.Paint(style=ft.PaintingStyle.FILL,color=ft.Colors.GREY_400)
        boy_paint = ft.Paint(style=ft.PaintingStyle.FILL, color=ft.Colors.BLUE_800)
        selected_paint = ft.Paint(style=ft.PaintingStyle.STROKE,color=ft.Colors.GREEN,stroke_width=4)

        # drawing lines between nodes
        shapes = []
        for node_id,neighbours in board_nodes.items():
            x1,y1 = NODE_COORDS[node_id]
            for neighbour_id in neighbours:
                if neighbour_id > node_id:
                    x2,y2 = NODE_COORDS[neighbour_id]
                    shapes.append(cv.Line(x1=x1,y1=y1,x2=x2,y2=y2,paint=line_paint))


        # drawing pieces on the board
        for node_id,piece_type in current_board_state.items():
            x,y = NODE_COORDS[node_id]
            if node_id == selected_node:
                shapes.append(cv.Circle(x=x,y=y,radius=28,paint=selected_paint))
            if piece_type == -1:
                shapes.append(cv.Circle(x=x,y=y,radius=14, paint=boy_paint))
            elif piece_type == 1:
                shapes.append(cv.Circle(x=x,y=y,radius=24,paint=bull_paint))

        return  cv.Canvas(shapes=shapes,expand=True)

    BOARD_WIDTH = (4 * UNIT) + (2 * OFFSET_X)
    BOARD_HEIGHT = OFFSET_Y + (6 * UNIT) + 40

    # making it visible on the screen
    board_canvas = draw_board()

    board_gest_detector = ft.GestureDetector(on_tap_down=on_board_click,content=board_canvas)

    board_stack = ft.Stack(
        [
            ft.Container(
                width=BOARD_WIDTH,
                height=BOARD_HEIGHT,
                bgcolor=ft.Colors.BROWN_400,
                border_radius=10
            ),
            board_gest_detector,
        ],width = BOARD_WIDTH,height = BOARD_HEIGHT,
    )

    current_turn_text = ft.Text(f'TURN: BULLS',weight=ft.FontWeight.BOLD,size=20,color=ft.Colors.GREY)
    unused_boys_text = ft.Text(f'BOYS TO PLACE: {logic.unused_boys}',weight=ft.FontWeight.BOLD,size=20,color=ft.Colors.RED)
    game_info_row = ft.Row(controls=[current_turn_text,unused_boys_text],alignment=ft.MainAxisAlignment.SPACE_AROUND)

    board_container = ft.Container(
        bgcolor=ft.Colors.BROWN,
        width=BOARD_WIDTH + 40,
        height=BOARD_HEIGHT + 40,
        content=ft.Column([game_info_row,board_stack]),
    alignment=ft.Alignment.CENTER)
    page.add(board_container)

    # lower bar
    help_button = ft.IconButton(icon=ft.Icons.HELP_OUTLINE)
    helpful_bar = ft.Container(bgcolor=ft.Colors.GREY,width=page.width,height=100,content=help_button)
    page.add(helpful_bar)


if __name__ == "__main__":
    ft.run(main)