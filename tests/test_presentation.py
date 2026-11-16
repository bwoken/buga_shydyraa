"""Window budgets, translation completeness and animated-control lifecycle."""

from pathlib import Path
from string import Formatter
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from board import BoardView, infer_move, LEGAL_STEP, LEGAL_CAPTURE, ACCENT
from i18n import MESSAGES, translate
from layout import fit_layout, BOARD_ASPECT, BOARD_PADDING, PAGE_PADDING, MOBILE_CHROME
from logic import BugaGame, BULL, BOY, Move
from test_game import FakePage


class LayoutTests(unittest.TestCase):
    def test_board_fits_actual_viewport_including_windows_scaling(self):
        # Physical 1920x1080, 125%/150% OS scaling, and browser chrome.
        for width, height in ((1920, 1000), (1536, 800), (1280, 650), (1100, 720)):
            with self.subTest(size=(width, height)):
                layout = fit_layout(width, height)
                self.assertFalse(layout.compact)
                self.assertLessEqual(layout.content_width + PAGE_PADDING * 2, width)
                total = layout.board_width * BOARD_ASPECT + 2 * (BOARD_PADDING + PAGE_PADDING)
                self.assertLessEqual(total, height + 0.01)
                self.assertGreater(total, height - 1)

    def test_phone_board_and_essential_controls_fit_the_viewport(self):
        for width, height in ((320, 568), (360, 640), (390, 844), (430, 932), (714, 700),
                              (853, 1280), (768, 1024), (540, 720), (859, 1280)):
            layout = fit_layout(width, height)
            self.assertTrue(layout.compact)
            self.assertLessEqual(layout.content_width + PAGE_PADDING * 2, width)
            total = layout.board_width * BOARD_ASPECT + 2 * BOARD_PADDING + MOBILE_CHROME
            self.assertLessEqual(total, layout.main_height + 0.01)
            self.assertLessEqual(layout.board_width + BOARD_PADDING * 2, layout.content_width)

    def test_landscape_phone_puts_controls_beside_the_board(self):
        for width, height in ((844, 390), (932, 430), (568, 320), (1100, 500)):
            layout = fit_layout(width, height)
            self.assertTrue(layout.landscape)
            self.assertLessEqual(layout.content_width + 2 * PAGE_PADDING, width)
            self.assertLessEqual(layout.board_width * BOARD_ASPECT + 2 * BOARD_PADDING,
                                 layout.main_height + 0.01)

    def test_viewport_matrix_keeps_board_inside_both_axes(self):
        for width in (320, 360, 390, 430, 540, 568, 720, 768, 853, 859, 860, 932, 1280, 1920):
            for height in (320, 390, 500, 559, 560, 640, 844, 1024, 1280):
                with self.subTest(size=(width, height)):
                    layout = fit_layout(width, height)
                    self.assertGreater(layout.board_width, 0)
                    self.assertLessEqual(layout.content_width + 2 * PAGE_PADDING, width + 0.01)
                    self.assertLessEqual(layout.board_width + 2 * BOARD_PADDING, layout.content_width)
                    required = layout.board_width * BOARD_ASPECT + 2 * BOARD_PADDING
                    if layout.compact and not layout.landscape:
                        required += MOBILE_CHROME
                    self.assertLessEqual(required, layout.main_height + 0.01)


class TranslationTests(unittest.TestCase):
    def test_translation_does_not_read_files_on_each_request(self):
        with patch("i18n.files", side_effect=AssertionError("catalog reread")):
            for _ in range(100):
                self.assertEqual(translate("en", "bulls"), "Bulls")

    def test_all_languages_have_same_keys_and_format_fields(self):
        def fields(text):
            return {name for _, name, _, _ in Formatter().parse(text) if name}
        base = MESSAGES["ru"]
        for language, catalog in MESSAGES.items():
            self.assertEqual(set(catalog), set(base), language)
            for key, value in catalog.items():
                self.assertTrue(value.strip(), (language, key))
                self.assertEqual(fields(value), fields(base[key]), (language, key))
                self.assertTrue(translate(language, key, **{f: 1 for f in fields(value)}))

    def test_service_error_is_localised_by_receiving_session(self):
        from online import RoomService, RoomError
        from auth import AuthStore, AuthError
        with self.assertRaises(RoomError) as error:
            RoomService().read("missing", AuthStore.guest())
        self.assertEqual(error.exception.key, "error_room_missing")
        self.assertIn("room", translate("en", error.exception.key))
        with self.assertRaises(AuthError) as error:
            AuthStore._name("a")
        self.assertIn("Username", translate("en", error.exception.key))


class BoardTests(unittest.TestCase):
    def test_only_latest_move_is_marked_and_undo_restores_the_previous_mark(self):
        from topology import NODE_COORDS
        game = BugaGame()
        self.assertTrue(game.make_move(7, 17))
        board = BoardView()
        board.update(game)
        self.assertEqual(len(board.move_trace.shapes), 3)
        self.assertTrue(game.place_boy(1))
        board.update(game.clone())
        self.assertEqual(game.last_move(), Move("PLACE", None, 1))
        mark, = board.move_trace.shapes
        self.assertEqual((mark.x, mark.y), NODE_COORDS[1])

        game.undo_last()
        board.update(game, animations=False)
        _, start, end = board.move_trace.shapes
        self.assertEqual((start.x, start.y), NODE_COORDS[7])
        self.assertEqual((end.x, end.y), NODE_COORDS[17])
        board.update(BugaGame())
        self.assertFalse(board.move_trace.shapes)

    def test_static_geometry_and_control_tree_are_reused_on_selection(self):
        game, board = BugaGame(), BoardView()
        board.update(game)
        tree, lines = tuple(board.control.controls), board.lines.shapes
        node_disc, piece_disc = board.nodes[3].content, board.pieces[7].content
        for selected in (7, None, 27, None):
            board.update(game, selected=selected, legal=game.destinations(selected) if selected else [])
            self.assertIs(board.lines.shapes, lines)
            self.assertEqual(tuple(board.control.controls), tree)
            self.assertIs(board.nodes[3].content, node_disc)
            self.assertIs(board.pieces[7].content, piece_disc)

    def test_placement_and_capture_use_mounted_slots_without_delayed_flush(self):
        game, board = BugaGame(), BoardView()
        board.update(game)
        tree = tuple(board.control.controls)
        captured = board.pieces[12]
        self.assertTrue(game.make_move(7, 17))
        board.update(game)
        self.assertIn(captured, board.control.controls)
        self.assertEqual(captured.opacity, 0)
        self.assertGreater(captured.animate_opacity.duration, 0)
        inactive = {id(c) for c in board.control.controls if isinstance(c.data, int) and c.opacity == 0}
        self.assertTrue(game.place_boy(7))
        board.update(game)
        boy = board.pieces[7]
        self.assertIn(id(boy), inactive)
        self.assertEqual(boy.opacity, 1)
        self.assertGreater(boy.animate_opacity.duration, 0)
        self.assertEqual(tuple(board.control.controls), tree)

    def test_moving_piece_keeps_its_control_and_animates_position(self):
        game, board = BugaGame(), BoardView()
        tree = board.update(game)
        bull = board.pieces[7]
        old_top = bull.top
        self.assertTrue(game.make_move(7, 17))
        self.assertIs(board.update(game), tree)
        self.assertIs(board.pieces[17], bull)
        self.assertNotEqual(bull.top, old_top)
        self.assertGreater(bull.animate_position.duration, 0)
        self.assertNotIn(12, board.pieces)
        self.assertEqual(infer_move(BugaGame().board, game.board), Move("MOVE", 7, 17))

    def test_resize_and_disabled_animations_snap_to_target(self):
        game, board = BugaGame(), BoardView()
        board.update(game)
        game.make_move(7, 3)
        board.update(game, width=300)
        self.assertEqual(board.pieces[3].animate_position.duration, 0)
        game.place_boy(1)
        board.update(game, width=300, animations=False)
        self.assertEqual(board.pieces[1].animate_opacity.duration, 0)

    def test_number_labels_are_offset_without_replacing_piece_mark(self):
        from topology import NODE_COORDS
        board = BoardView()
        board.update(BugaGame(), show_numbers=True)
        x, y = NODE_COORDS[7]
        label = board.numbers[7]
        self.assertGreater(label.left, x)
        self.assertGreater(label.top, y)
        self.assertEqual(board.pieces[7].content.content.value, "Б")
        self.assertTrue(label.ignore_interactions)
        self.assertIsNone(label.bgcolor)

    def test_small_phone_keeps_touch_targets_and_labels_readable(self):
        layout = fit_layout(320, 568)
        board = BoardView()
        board.update(BugaGame(), width=layout.board_width, show_numbers=True)
        for node in board.nodes.values():
            self.assertGreaterEqual(node.width, 44)
            self.assertGreaterEqual(node.height, 44)
        for label in board.numbers.values():
            self.assertIsNone(label.bgcolor)
            self.assertGreaterEqual(label.content.size, 10)

    def test_highlights_differ_from_pieces_and_distinguish_captures(self):
        game, board = BugaGame(), BoardView()
        board.update(game, selected=7, legal=game.destinations(7))
        self.assertEqual(board.nodes[3].content.bgcolor, LEGAL_STEP)
        self.assertEqual(board.nodes[17].content.bgcolor, LEGAL_CAPTURE)
        self.assertNotEqual(LEGAL_STEP, ACCENT)
        self.assertNotEqual(LEGAL_CAPTURE, ACCENT)


class LocalizedAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_phone_has_only_essential_controls_without_a_scrolling_page(self):
        from app import GameApp
        from types import SimpleNamespace
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        await app.resize(SimpleNamespace(width=390, height=844))
        self.assertIsNone(page.scroll)
        self.assertIsNone(app.view.body.scroll)
        self.assertEqual(app.view.body.controls, [app.view.mobile_header, app.view.mobile_status,
                         app.view.mobile_board_holder, app.view.mobile_actions])
        self.assertNotIn(app.view.settings_card, app.view.body.controls)
        self.assertIs(app.view.mobile_board_holder.content, app.view.board_card)
        self.assertLessEqual(app.root.height + PAGE_PADDING * 2, 844)
        await app.close()

    async def test_secondary_panels_use_a_sheet_on_phone_and_do_not_reset_game(self):
        import flet as ft
        from app import GameApp
        from types import SimpleNamespace
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        await app.resize(SimpleNamespace(width=360, height=640))
        await app.on_node(7)
        await app.on_node(3)
        before = app.game.clone().__dict__
        for opener in (app.view.open_settings, app.view.open_information, app.view.open_online):
            await opener()
            self.assertIsInstance(page.dialogs[-1], ft.BottomSheet)
            self.assertEqual(app.game.__dict__, before)
            app.view.dismiss_panel()
            await page.finish_dismissal()
        app.mode_picker.value = "local"
        await app.view.open_new_game()
        panel = page.dialogs[-1]
        await app.start_game()
        self.assertFalse(panel.open)
        self.assertEqual(len(app.game.history), 0)
        await app.close()

    async def test_phone_height_updates_when_growing_without_crossing_breakpoint(self):
        from app import GameApp
        from types import SimpleNamespace
        app = GameApp(FakePage())
        await app.mount()
        for width, height in ((320, 568), (390, 844), (360, 640)):
            await app.resize(SimpleNamespace(width=width, height=height))
            self.assertEqual(app.view.body.height, height - 2 * PAGE_PADDING)
            required = app.view.board.control.height + 2 * BOARD_PADDING + MOBILE_CHROME
            self.assertLessEqual(required, app.view.body.height + 0.01)
        await app.close()

    async def test_desktop_keeps_forms_outside_the_main_sidebar(self):
        import flet as ft
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        self.assertEqual(app.view.sidebar_column.controls,
                         [app.view.header, app.view.game_card, app.view.stats_card, app.view.help_card])
        self.assertIsNone(app.view.sidebar_column.scroll)
        await app.view.open_new_game()
        self.assertIsInstance(page.dialogs[-1], ft.AlertDialog)
        await app.close()

    async def test_changing_status_cannot_move_or_resize_the_board(self):
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        original = (app.view.board.control.width, app.view.board.control.height,
                    app.view.board_card.padding, app.view.body.controls[0])
        for language, thinking, notice in (("en", True, ""), ("tyv", False, "error_ai"), ("ru", False, "")):
            app.language = language
            app.thinking, app.notice = thinking, notice
            app.render()
            self.assertEqual((app.view.board.control.width, app.view.board.control.height,
                              app.view.board_card.padding, app.view.body.controls[0]), original)
            self.assertIs(app.view.board_card.content, app.view.board.control)
        await app.close()

    async def test_mobile_thinking_animation_keeps_its_space_and_can_be_disabled(self):
        from app import GameApp
        from types import SimpleNamespace
        app = GameApp(FakePage())
        await app.mount()
        await app.resize(SimpleNamespace(width=390, height=694))
        view = app.view
        board_height, status_height = view.board.control.height, view.mobile_status.height
        for thinking, animations, value in ((False, True, 1), (True, True, None),
                                            (True, False, 1), (False, False, 1)):
            app.thinking = thinking
            app.animation_switch.value = animations
            app.render()
            self.assertEqual(view.mobile_progress.visible, thinking)
            self.assertEqual(view.mobile_progress.value, value)
            self.assertEqual((view.board.control.height, view.mobile_status.height),
                             (board_height, status_height))
        await app.close()

    async def test_resize_uses_latest_event_dimensions(self):
        from types import SimpleNamespace
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        await app.resize(SimpleNamespace(width=1536, height=800))
        expected = fit_layout(1536, 800)
        self.assertEqual(app.view.board.control.width, expected.board_width)
        self.assertEqual(app.root.width, expected.content_width)
        await app.close()

    async def test_invalid_resize_does_not_replace_last_valid_viewport(self):
        from types import SimpleNamespace
        from app import GameApp
        app = GameApp(FakePage())
        await app.mount()
        await app.resize(SimpleNamespace(width=853, height=1280))
        before = app.view.layout
        for width, height in ((0, 0), (-1, 844), (390, None), (float('nan'), 844)):
            await app.resize(SimpleNamespace(width=width, height=height))
            self.assertEqual(app.view.layout, before)
        await app.close()

    async def test_web_layout_uses_measured_space_when_page_reports_a_tiny_viewport(self):
        from types import SimpleNamespace
        from app import GameApp
        page = FakePage()
        page.width, page.height = 128, 220
        app = GameApp(page)
        await app.mount()
        try:
            canvas = page.controls[0]
            for width, height in ((390, 694), (844, 390), (390, 694)):
                await canvas.on_resize(SimpleNamespace(width=width - 2 * PAGE_PADDING,
                                                       height=height - 2 * PAGE_PADDING))
                expected = fit_layout(width, height)
                self.assertEqual(app.view.layout, expected)
                self.assertEqual(app.view.board.control.width, expected.board_width)
                await app.resize(SimpleNamespace(width=128, height=220))
                self.assertEqual(app.view.layout, expected)
        finally:
            await app.close()

    async def test_fast_reopen_waits_for_old_panel_unmount(self):
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        await app.view.open_online()
        first = app.view._panel
        app.view.dismiss_panel()
        await app.view.open_online()
        await app.view.open_online()
        self.assertEqual(len(page.dialogs), 1)
        await page.finish_dismissal(first)
        second = app.view._panel
        self.assertIsNot(first, second)
        self.assertTrue(second.open)
        await page.finish_dismissal(first)  # A late event cannot close the new panel.
        self.assertIs(app.view._panel, second)
        await app.view.open_settings()
        app.view.dismiss_panel()  # Cancels a pending panel switch, e.g. start/leave.
        await page.finish_dismissal(second)
        self.assertIsNone(app.view._panel)
        await app.close()

    async def test_reconnect_finishes_a_dismissal_lost_during_refresh(self):
        from app import GameApp
        app = GameApp(FakePage())
        await app.mount()
        await app.view.open_online()
        app.view.dismiss_panel()
        await app.view.open_online()
        old = app.view._panel
        await app.reconnect()
        self.assertIsNot(app.view._panel, old)
        self.assertTrue(app.view._panel.open)
        await app.close()


class WireUpdateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def capture_session():
        import asyncio
        import msgpack
        from types import SimpleNamespace
        from flet.messaging.connection import Connection
        from flet.messaging.session import Session
        from flet.messaging.protocol import configure_encode_object_for_msgpack
        from flet.controls.base_control import BaseControl
        encode = configure_encode_object_for_msgpack(BaseControl)

        class Capture(Connection):
            pubsubhub = SimpleNamespace()

            def __init__(self):
                super().__init__()
                self.loop = asyncio.get_running_loop()
                self.messages, self.payloads = [], []

            def send_message(self, message):
                self.messages.append(message)
                self.payloads.append(msgpack.packb(message, default=encode))

        connection = Capture()
        session = Session(connection)
        # Serialising the handshake initializes Flet's property snapshots.
        msgpack.packb(session.get_page_patch(), default=encode)
        return session, connection

    async def test_repeated_room_panels_keep_buttons_registered_after_dismissal(self):
        from types import SimpleNamespace
        from app import GameApp
        session, _ = self.capture_session()
        page = session.page
        page.width, page.height, page.web = 1100, 800, True
        app = GameApp(page)
        await app.mount()
        try:
            await app.view.open_online()
            panel = app.view._panel
            await app.create_room()
            code = app.room.code
            self.assertIs(app.view._panel, panel)
            self.assertTrue(panel.open)
            self.assertEqual(app.view.invite.value, code)
            self.assertTrue(app.view.room_card.visible)
            self.assertFalse(app.view.online_card.visible)
            app.view.dismiss_panel()
            await session.dispatch_event(panel._i, "dismiss", None)
            for width, height in ((1100, 800), (853, 1280), (390, 844), (844, 390), (1100, 800)):
                await app.resize(SimpleNamespace(width=width, height=height))
                for _ in range(3):
                    await app.view.open_online()
                    panel = app.view._panel
                    self.assertTrue(panel.open)
                    self.assertIn(app.view.leave._i, session.index)
                    self.assertEqual(app.view.invite.value, code)
                    app.view.dismiss_panel()
                    await app.view.open_online()  # Reopen while dismissal is still in flight.
                    await session.dispatch_event(panel._i, "dismiss", None)
                    self.assertIsNot(panel, app.view._panel)
                    self.assertIn(app.view.leave._i, session.index)
                    app.view.dismiss_panel()
                    await session.dispatch_event(app.view._panel._i, "dismiss", None)
                    self.assertIsNone(app.view._panel)
                    self.assertIn(app.view.board.pieces[7]._i, session.index)
        finally:
            await app.close()

    async def test_poll_updates_mobile_board_and_turn_together_without_dialogs(self):
        import asyncio
        from app import GameApp, ROOMS
        from auth import AuthStore
        session, connection = self.capture_session()
        page = session.page
        page.width, page.height, page.web = 390, 844, True
        app = GameApp(page)
        await app.mount()
        host = AuthStore.guest()
        room = ROOMS.create(host)
        app.enter_room(ROOMS.join(room.code, app.identity))
        try:
            position = app.view.board.pieces[7].top
            connection.messages.clear()
            connection.payloads.clear()
            ROOMS.play(room.code, host, Move("MOVE", 7, 3), app.room.revision)

            async def wait_for_update():
                while app.game.board[3] != BULL:
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_for_update(), 2)
            self.assertIsNone(app.view._panel)
            self.assertNotEqual(app.view.board.pieces[3].top, position)
            self.assertEqual(len(connection.messages), 1)
            self.assertEqual(connection.messages[0].body.id, page._i)
            patch = connection.payloads[0]
            self.assertIn(app.view.mobile_turn.value.encode(), patch)
            self.assertIn(app.view.board.pieces[3].tooltip.encode(), patch)
        finally:
            await app.close()

    async def test_selection_sends_small_property_patches_and_keeps_registered_controls(self):
        from app import GameApp
        session, connection = self.capture_session()
        page = session.page
        page.width, page.height, page.web = 1536, 800, True
        app = GameApp(page)
        app.view.render(flush=False)
        page.add(app.root)
        registered = set(session.index)
        for selected in (7, None, 27, None):
            connection.messages.clear()
            connection.payloads.clear()
            app.selected = selected
            app.view.update_selection()
            self.assertEqual(set(session.index), registered)
            self.assertGreater(len(connection.messages), 0)
            self.assertLess(sum(map(len, connection.payloads)), 12_000)
            self.assertNotIn(page._i, {message.body.id for message in connection.messages})

    async def test_language_changes_preserve_game_choices_and_board_ancestry(self):
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        await app.on_node(7)
        await app.on_node(3)
        before = app.game.clone().__dict__
        root, body, card, stack = app.root.content, app.view.body, app.view.board_card, app.view.board.control
        bull = app.view.board.pieces[3]
        for language in ("en", "tyv", "ru"):
            app.language_picker.value = language
            await app.change_language()
            self.assertEqual(app.game.__dict__, before)
            self.assertIs(app.root.content, root)
            self.assertIs(app.view.body, body)
            self.assertIs(app.view.board_card, card)
            self.assertIs(app.view.board.control, stack)
            self.assertIs(app.view.board.pieces[3], bull)
            self.assertEqual(app.number_switch.label, translate(language, "node_numbers"))
            await app.show_rules()
            self.assertEqual(page.dialogs[-1].title.value, translate(language, "how_to_play"))
        await app.close()


if __name__ == "__main__":
    unittest.main()
