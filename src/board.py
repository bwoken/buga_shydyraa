"""Persistent board. Only changed properties are sent to the Flet client.

All 26 piece slots stay mounted, including reserve and captured boys. This
lets Flutter animate insertion/removal locally without a timed second patch.
"""

from collections.abc import Callable

import flet as ft
import flet.canvas as cv

from i18n import translate
from logic import BugaGame, BULL, BOY, EMPTY, Move, infer_move
from topology import NODE_COORDS, BOARD_NEIGHBORS

BOARD_WIDTH, BOARD_HEIGHT = 360, 620
INK, MUTED, ACCENT = "#EEE9DC", "#91A69E", "#89D5BB"
SURFACE, BACKGROUND = "#172E28", "#10221D"
LEGAL_STEP, LEGAL_CAPTURE, SELECTED = "#FFD166", "#FF8F75", "#FFFFFF"
LAST_MOVE_COLOR = "#8D819F"
MOVE_DURATION = 280
MOVE_ANIMATION = ft.Animation(MOVE_DURATION, ft.AnimationCurve.EASE_OUT_CUBIC)
APPEAR_ANIMATION = ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC)
INSTANT = ft.Animation(0)


class BoardView:
    def __init__(self, on_node: Callable | None = None):
        self.on_node = on_node
        self._handlers = {n: self._handler(n) for n in NODE_COORDS}
        self.lines = cv.Canvas([])
        self.move_trace = cv.Canvas([])
        self.nodes, self.numbers = {}, {}
        self._node_discs, self._node_marks, self._piece_marks, self._piece_discs = {}, {}, {}, {}
        for node in NODE_COORDS:
            mark = self._node_marks[node] = ft.Text("·", weight=ft.FontWeight.BOLD)
            disc = self._node_discs[node] = ft.Container(content=mark, alignment=ft.Alignment.CENTER)
            self.nodes[node] = ft.Container(key=f"node-{node}", content=disc,
                                            alignment=ft.Alignment.CENTER)
            self.numbers[node] = ft.Container(
                key=f"number-{node}", ignore_interactions=True,
                alignment=ft.Alignment.CENTER, visible=False,
                content=ft.Text(str(node), color=INK, weight=ft.FontWeight.BOLD))
        self._pool = []
        for index in range(26):
            mark = self._piece_marks[index] = ft.Text(color=BACKGROUND, weight=ft.FontWeight.BOLD)
            disc = self._piece_discs[index] = ft.Container(content=mark, alignment=ft.Alignment.CENTER)
            self._pool.append(ft.Container(
                key=f"piece-{index}", data=index, content=disc, left=0, top=0,
                opacity=0, scale=0.65, ignore_interactions=True,
                alignment=ft.Alignment.CENTER, animate_position=MOVE_ANIMATION,
                animate_opacity=APPEAR_ANIMATION, animate_scale=APPEAR_ANIMATION))
        self.control = ft.Stack([self.lines, self.move_trace, *self.nodes.values(), *self._pool, *self.numbers.values()],
                                clip_behavior=ft.ClipBehavior.NONE)
        self.pieces = {}
        self._before = {}
        self._width = None
        self._trace_state = None
        self._node_styles, self._piece_styles = {}, {}
        self._ever_used = set()
        self._reset = True
        self._slot_states = {}

    def _handler(self, node):
        async def click(event):
            await self.on_node(node)
        return click if self.on_node else None

    def reset(self):
        self.pieces.clear()
        self._before = {}
        self._ever_used.clear()
        self._reset = True

    def _reconcile(self, board, move):
        if move and move.kind == "MOVE" and move.start in self.pieces:
            self.pieces[move.end] = self.pieces.pop(move.start)
        for node in list(self.pieces):
            slot = self.pieces[node]
            slot_side = BULL if slot.data < 2 else BOY
            if board[node] != slot_side:
                del self.pieces[node]
        taken = {slot.data for slot in self.pieces.values()}
        inserted = set()
        for node, piece in board.items():
            if piece == EMPTY or node in self.pieces:
                continue
            candidates = [slot for slot in self._pool if slot.data not in taken
                          and (BULL if slot.data < 2 else BOY) == piece]
            # Use the reserve first; a just-captured piece may still be fading.
            slot = min(candidates, key=lambda s: (s.data in self._ever_used, s.data))
            self.pieces[node] = slot
            taken.add(slot.data)
            self._ever_used.add(slot.data)
            inserted.add(slot.data)
        return inserted

    def _resize(self, width):
        scale = width / BOARD_WIDTH
        hit_size = max(44, 50 * scale)
        shapes = []
        for start, neighbors in BOARD_NEIGHBORS.items():
            for end in neighbors:
                if end > start:
                    x1, y1 = NODE_COORDS[start]
                    x2, y2 = NODE_COORDS[end]
                    shapes.append(cv.Line(x1 * scale, y1 * scale, x2 * scale, y2 * scale,
                                          ft.Paint(color="#526C5A", stroke_width=1.3)))
        self.lines.shapes = shapes
        self.lines.width, self.lines.height = width, BOARD_HEIGHT * scale
        self.move_trace.width, self.move_trace.height = self.lines.width, self.lines.height
        self.control.width, self.control.height = width, BOARD_HEIGHT * scale
        for node, (x, y) in NODE_COORDS.items():
            dot, number = self.nodes[node], self.numbers[node]
            dot.left, dot.top = x * scale - hit_size / 2, y * scale - hit_size / 2
            dot.width = dot.height = hit_size
            number.left, number.top = (x + 9) * scale, (y + 10) * scale
            number.width, number.height = max(18, 23 * scale), max(14, 16 * scale)
            number.content.size = max(10, 11 * scale)
        self._node_styles.clear()
        self._piece_styles.clear()
        self._slot_states.clear()

    def _update_move_trace(self, game, move, scale):
        endpoints = [node for node in (move.start, move.end) if node is not None] if move else []
        state = (move, scale, tuple(game.board[node] for node in endpoints))
        if self._trace_state == state:
            return
        self._trace_state = state
        shapes = []
        if move:
            paint = ft.Paint(
                color=LAST_MOVE_COLOR,
                stroke_width=3.2,
                stroke_cap=ft.StrokeCap.ROUND,
                style=ft.PaintingStyle.STROKE,
            )
            end_x, end_y = NODE_COORDS[move.end]
            if move.start is not None:
                start_x, start_y = NODE_COORDS[move.start]
                shapes.append(cv.Line(start_x * scale, start_y * scale,
                                      end_x * scale, end_y * scale, paint))
            for node in endpoints:
                x, y = NODE_COORDS[node]
                piece = game.board[node]
                if piece == BULL:
                    radius = max(17, 22 * scale)
                elif piece == BOY:
                    radius = max(14, 18 * scale)
                else:
                    radius = max(13, 17 * scale)
                shapes.append(cv.Circle(x * scale, y * scale, radius + 3, paint))
        self.move_trace.shapes = shapes

    def update(self, game: BugaGame, selected=None, legal=(), *, width=360,
               last_move=None, show_numbers=False, language="ru", animations=True):
        move = infer_move(self._before, game.board)
        first_paint = self._width is None
        resizing = self._width != width
        if resizing:
            self._resize(width)
        scale = width / BOARD_WIDTH
        self._update_move_trace(game, game.last_move() or last_move, scale)
        hit_size = max(44, 50 * scale)
        animate = animations and (first_paint or (not resizing and not self._reset))
        inserted = self._reconcile(game.board, move)
        active = {control.data for control in self.pieces.values()}
        for slot in self._pool:
            if slot.data not in active:
                state = ("inactive", animate)
                if self._slot_states.get(slot.data) != state:
                    slot.animate_opacity = slot.animate_scale = APPEAR_ANIMATION if animate else INSTANT
                    slot.opacity, slot.scale = 0, 0.65
                    slot.on_click, slot.tooltip, slot.ignore_interactions = None, None, True
                    self._slot_states[slot.data] = state
        for node, (x, y) in NODE_COORDS.items():
            piece = game.board[node]
            target = node in legal
            capture = bool(target and selected is not None and
                           game.capture_node(Move("MOVE", selected, node)) is not None)
            signature = (piece, target, capture, language)
            dot, disc, mark = self.nodes[node], self._node_discs[node], self._node_marks[node]
            if self._node_styles.get(node) != signature:
                name = translate(language, "bull" if piece == BULL else "boy" if piece == BOY else "empty")
                tooltip = translate(language, "node", piece=name, node=node)
                dot.tooltip = tooltip if piece == EMPTY else None
                dot.on_click = self._handlers[node] if piece == EMPTY else None
                disc.visible = piece == EMPTY
                size = max(26, 34 * scale) if target else 20 * scale
                disc.width = disc.height = size
                disc.border_radius = size / 2
                disc.bgcolor = (LEGAL_CAPTURE if capture else LEGAL_STEP) if target else SURFACE
                disc.border = ft.Border.all(2, "#FFF4DB" if target else "#526C5A")
                mark.value = "×" if capture else "•" if target else "·"
                mark.size = max(12, 18 * scale) if target else 12 * scale
                mark.color = BACKGROUND if target else MUTED
                self._node_styles[node] = signature
            if self.numbers[node].visible != show_numbers:
                self.numbers[node].visible = show_numbers
            if piece == EMPTY:
                continue
            slot = self.pieces[node]
            state = ("active", node, animate, slot.data in inserted and not first_paint)
            if self._slot_states.get(slot.data) != state:
                slot.animate_position = MOVE_ANIMATION if animate and not state[-1] else INSTANT
                slot.animate_opacity = slot.animate_scale = APPEAR_ANIMATION if animate else INSTANT
                slot.left, slot.top = x * scale - hit_size / 2, y * scale - hit_size / 2
                slot.width = slot.height = hit_size
                slot.opacity, slot.scale, slot.ignore_interactions = 1, 1, False
                slot.on_click = self._handlers[node]
                self._slot_states[slot.data] = state
            signature = (piece, node, selected == node, language)
            if self._piece_styles.get(slot.data) != signature:
                name = translate(language, "bull" if piece == BULL else "boy")
                slot.tooltip = translate(language, "node", piece=name, node=node)
                disc, mark = self._piece_discs[slot.data], self._piece_marks[slot.data]
                size = max(34, 44 * scale) if piece == BULL else max(28, 36 * scale)
                disc.width = disc.height = size
                disc.border_radius = size / 2
                disc.bgcolor = INK if piece == BULL else ACCENT
                disc.border = ft.Border.all(3 if selected == node else 1.5,
                                            SELECTED if selected == node else "#526C5A")
                mark.value = translate(language, "bull_mark") if piece == BULL else "●"
                mark.size = max(12, 16 * scale)
                self._piece_styles[slot.data] = signature
        self._before, self._width, self._reset = game.board.copy(), width, False
        return self.control


def draw_board(game, selected_node=None, legal_moves=(), *, on_node=None, **kwargs):
    return BoardView(on_node).update(game, selected_node, legal_moves, **kwargs)
