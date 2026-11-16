"""Regression coverage for rules, search, authentication and online authority."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthStore, AuthError
from bot import SmartBot, EasyBot
from logic import (BugaGame, Move, BULL, BOY, EMPTY, BULLS_WIN, BOYS_WIN,
                   DRAW_NO_CAPTURE, DRAW_REPETITION)
from online import RoomService, RoomError
from topology import BOARD_NEIGHBORS, CAPTURE_PATHS, NODE_COORDS


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.game = BugaGame()

    def test_initial_state_and_topology(self):
        self.assertEqual(sum(p == BULL for p in self.game.board.values()), 2)
        self.assertEqual(sum(p == BOY for p in self.game.board.values()), 8)
        self.assertEqual(self.game.unused_boys, 16)
        self.assertIsNone(self.game.check_winner())
        for start, neighbors in BOARD_NEIGHBORS.items():
            for end in neighbors:
                self.assertIn(start, BOARD_NEIGHBORS[end])
            for middle, end in CAPTURE_PATHS[start]:
                self.assertIn(middle, neighbors)
                self.assertIn(end, BOARD_NEIGHBORS[middle])
                self.assertIn((middle, start), CAPTURE_PATHS[end])
                x, y = NODE_COORDS[start]
                mx, my = NODE_COORDS[middle]
                ex, ey = NODE_COORDS[end]
                self.assertEqual((mx - x) * (ey - my), (my - y) * (ex - mx))

    def test_wrong_side_and_bad_moves_do_not_change_state(self):
        before = self.game.clone().__dict__
        for move in (Move("MOVE", 11, 10), Move("PLACE", None, 1),
                     Move("MOVE", 7, 999), Move("MOVE", 999, 1),
                     ("UNKNOWN", 7, 1), ("PLACE", 7, 1)):
            self.assertFalse(self.game.apply(move))
        self.assertEqual(self.game.__dict__, before)

    def test_capture_resets_counter_to_zero(self):
        self.game.moves_without_capture = 17
        self.assertTrue(self.game.make_move(7, 17))  # over boy on 12
        self.assertEqual(self.game.board[12], EMPTY)
        self.assertEqual(self.game.board[17], BULL)
        self.assertEqual(self.game.moves_without_capture, 0)
        self.assertEqual(self.game.current_turn, BOY)

    def test_placement_consumes_turn_and_counts_quiet_ply(self):
        self.game.make_move(7, 3)
        self.assertFalse(self.game.make_move(11, 10))
        self.assertTrue(self.game.place_boy(7))
        self.assertEqual(self.game.unused_boys, 15)
        self.assertEqual(self.game.moves_without_capture, 2)
        self.assertEqual(self.game.current_turn, BULL)

    def test_boys_move_after_reserve_is_empty(self):
        self.game.current_turn = BOY
        self.game.unused_boys = 0
        self.game.board[1] = BOY  # nine boys remain, so the match is still live
        self.assertTrue(self.game.make_move(11, 10))
        self.assertEqual(self.game.board[10], BOY)

    def test_undo_restores_all_history_and_draw_state(self):
        before = self.game.clone().__dict__
        self.game.make_move(7, 17)
        self.game.place_boy(7)
        self.assertTrue(self.game.undo_player_move(BULL))
        self.assertEqual(self.game.__dict__, before)

    def test_repetition_and_no_capture_draws(self):
        self.game.position_history = [self.game.position_key()] * 3
        self.assertEqual(self.game.check_winner(), DRAW_REPETITION)
        self.game.position_history = [self.game.position_key()]
        self.game.moves_without_capture = 60
        self.assertEqual(self.game.check_winner(), DRAW_NO_CAPTURE)
        self.assertFalse(self.game.make_move(7, 3))

    def test_wins(self):
        self.game.unused_boys = 0
        self.assertEqual(self.game.check_winner(), BULLS_WIN)
        self.game = BugaGame()
        self.game.board = dict.fromkeys(range(1, 36), BOY)
        self.game.board[1] = self.game.board[33] = BULL
        self.assertEqual(self.game.check_winner(), BOYS_WIN)


class BotTests(unittest.TestCase):
    def test_search_does_not_mutate_caller(self):
        for side in (BULL, BOY):
            game = BugaGame()
            if side == BOY:
                game.make_move(7, 3)
            before = game.clone().__dict__
            bot = SmartBot(game, side, depth=3, time_limit=0.08)
            move = bot.get_move()
            self.assertIn(move, game.get_all_legal_moves())
            self.assertEqual(game.__dict__, before)

    def test_immediate_winning_capture(self):
        game = BugaGame()
        game.unused_boys = 1  # nine remaining: a capture wins
        bot = SmartBot(game, BULL, depth=2, time_limit=0.2)
        self.assertTrue(game.apply(bot.get_move()))
        self.assertEqual(game.check_winner(), BULLS_WIN)

    def test_boys_find_winning_blockade(self):
        game = BugaGame()
        game.board = dict.fromkeys(range(1, 36), EMPTY)
        game.board[1] = game.board[33] = BULL
        for node in (2, 3, 4, 7, 27, 30, 34):
            game.board[node] = BOY
        game.current_turn = BOY
        game.unused_boys = 17
        game.position_history = [game.position_key()]
        bot = SmartBot(game, BOY, depth=2, time_limit=0.4)
        self.assertEqual(bot.get_move(), Move("PLACE", None, 35))
        self.assertTrue(game.place_boy(35))
        self.assertEqual(game.check_winner(), BOYS_WIN)

    def test_terminal_scores_and_draws_from_both_sides(self):
        for side in (BULL, BOY):
            bot = SmartBot(BugaGame(), side)
            self.assertEqual(bot._terminal_score(DRAW_NO_CAPTURE, 1), 0)
            self.assertEqual(bot._terminal_score(DRAW_REPETITION, 1), 0)
            self.assertGreater(bot._terminal_score(BULLS_WIN if side == BULL else BOYS_WIN, 1), 0)
            self.assertLess(bot._terminal_score(BOYS_WIN if side == BULL else BULLS_WIN, 1), 0)

    def test_zero_budget_has_legal_fallback(self):
        game = BugaGame()
        bot = SmartBot(game, BULL, depth=20, time_limit=0)
        start = time.monotonic()
        self.assertIn(bot.get_move(), game.get_all_legal_moves())
        self.assertLess(time.monotonic() - start, 0.5)

    def test_finished_game_and_wrong_turn_have_no_bot_move(self):
        game = BugaGame()
        self.assertIsNone(SmartBot(game, BOY).get_move())
        game.unused_boys = 0
        self.assertIsNone(EasyBot(game, BULL).get_move())


class OnlineTests(unittest.TestCase):
    def setUp(self):
        self.service = RoomService()
        self.host = AuthStore.guest("Игрок")
        self.guest = AuthStore.guest("Игрок")  # equal names grant no privileges
        self.view = self.service.create(self.host)

    def test_waiting_room_and_membership(self):
        with self.assertRaises(RoomError):
            self.service.play(self.view.code, self.host, Move("MOVE", 7, 3), 0)
        with self.assertRaises(RoomError):
            self.service.read(self.view.code, self.guest)
        with self.assertRaises(RoomError):
            self.service.leave(self.view.code, self.guest)

    def test_authoritative_turn_revision_and_private_snapshots(self):
        joined = self.service.join(self.view.code.lower(), self.guest)
        self.assertEqual(joined.side, BOY)
        self.assertTrue(joined.ready)
        with self.assertRaises(RoomError):
            self.service.play(joined.code, self.guest, Move("PLACE", None, 1), joined.revision)
        with self.assertRaises(RoomError):
            self.service.play(joined.code, self.host, Move("MOVE", 11, 10), joined.revision)
        view = self.service.play(joined.code, self.host, Move("MOVE", 7, 3), joined.revision)
        with self.assertRaises(RoomError):
            self.service.play(joined.code, self.guest, Move("PLACE", None, 1), joined.revision)
        view.game.board[3] = EMPTY
        self.assertEqual(self.service.read(view.code, self.host).game.board[3], BULL)
        self.service.play(view.code, self.guest, Move("PLACE", None, 1), view.revision)

    def test_only_one_joiner_can_claim_last_seat(self):
        def join(index):
            try:
                return self.service.join(self.view.code, AuthStore.guest(f"Гость{index}"))
            except RoomError:
                return None
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(join, range(6)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_leaving_closes_room(self):
        self.service.join(self.view.code, self.guest)
        self.service.leave(self.view.code, self.host)
        with self.assertRaises(RoomError):
            self.service.read(self.view.code, self.guest)

    def test_one_room_per_session(self):
        with self.assertRaises(RoomError):
            self.service.create(self.host)

    def test_duplicate_session_join_does_not_take_opponents_seat(self):
        duplicate = self.service.join(self.view.code, self.host)
        self.assertEqual(duplicate.side, BULL)
        self.assertFalse(duplicate.ready)
        self.assertEqual(duplicate.revision, self.view.revision)
        joined = self.service.join("  " + self.view.code.lower() + "  ", self.guest)
        self.assertTrue(joined.ready)
        with self.assertRaises(RoomError) as error:
            self.service.join(self.view.code, AuthStore.guest())
        self.assertEqual(error.exception.key, "error_room_full")

    def test_expired_room_and_server_capacity(self):
        from unittest.mock import patch
        from online import ROOM_TTL
        touched = self.service._rooms[self.view.code].touched
        with patch("online.time.monotonic", return_value=touched + ROOM_TTL + 1):
            with self.assertRaises(RoomError) as error:
                self.service.read(self.view.code, self.host)
            self.assertEqual(error.exception.key, "error_room_missing")
            self.assertIsNotNone(self.service.create(self.host))
        with patch("online.MAX_ROOMS", 1):
            with self.assertRaises(RoomError) as error:
                self.service.create(self.guest)
            self.assertEqual(error.exception.key, "error_server_full")

    def test_idle_poll_does_not_copy_history_but_still_checks_membership(self):
        from unittest.mock import patch
        with patch.object(BugaGame, "clone", side_effect=AssertionError("idle clone")):
            self.assertIsNone(self.service.read_if_changed(self.view.code, self.host, self.view.revision))
            with self.assertRaises(RoomError):
                self.service.read_if_changed(self.view.code, self.guest, self.view.revision)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = AuthStore(Path(self.directory.name) / "accounts.sqlite3")

    def test_registration_login_casefold_and_salted_hash(self):
        password = "correct horse battery"
        user = self.store.register("Игрок", password)
        self.store.register("Другой", password)
        logged = self.store.login("игрок", password)
        self.assertFalse(user.guest)
        self.assertEqual(logged.name, "Игрок")
        self.assertNotEqual(user.session_id, logged.session_id)
        connection = sqlite3.connect(self.store.path)
        try:
            rows = connection.execute("SELECT salt, password_hash FROM users").fetchall()
        finally:
            connection.close()
        self.assertNotEqual(rows[0], rows[1])
        self.assertNotIn(password.encode(), self.store.path.read_bytes())
        with self.assertRaises(AuthError):
            self.store.register("ИГРОК", password)
        with self.assertRaises(AuthError):
            self.store.login("Игрок", "incorrect")

    def test_validation_and_throttling(self):
        with self.assertRaises(AuthError):
            self.store.register("ab", "password123")
        with self.assertRaises(AuthError):
            self.store.register("valid", "short")
        for _ in range(5):
            with self.assertRaises(AuthError):
                self.store.login("unknown", "password123")
        with self.assertRaisesRegex(AuthError, "Слишком много"):
            self.store.login("unknown", "password123")


class FakePage:
    width = 1100
    height = 800
    web = True

    def __init__(self):
        self.controls = []
        self.dialogs = []
        self.tasks = []

    def add(self, control):
        self.controls.append(control)

    def update(self, *controls):
        pass

    def show_dialog(self, dialog):
        dialog.open = True
        self.dialogs.append(dialog)

    def pop_dialog(self):
        for dialog in reversed(self.dialogs):
            if dialog.open:
                dialog.open = False
                return dialog

    async def finish_dismissal(self, dialog=None):
        from types import SimpleNamespace
        dialog = dialog or self.dialogs[-1]
        dialog.open = False
        if dialog.on_dismiss:
            await dialog.on_dismiss(SimpleNamespace(control=dialog, data=None))

    def run_task(self, handler, *args):
        task = asyncio.create_task(handler(*args))
        self.tasks.append(task)
        return task


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_layouts_dialogs_and_real_async_node_handler(self):
        from app import GameApp
        from board import BoardView
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        for width in (360, 1100):
            page.width = width
            app.render()
        await app.show_rules()
        await app.show_account()
        board = BoardView(on_node=app.on_node)
        board.update(app.game)
        handler = board.pieces[7].on_click
        self.assertTrue(inspect.iscoroutinefunction(handler))
        await handler(None)
        self.assertEqual(app.selected, 7)
        await app.on_node(3)
        self.assertEqual(app.game.board[3], BULL)
        await app.undo()
        self.assertEqual(app.game.board[7], BULL)
        await app.close()

    async def test_stale_ai_cannot_move_in_new_game(self):
        from app import GameApp
        page = FakePage()
        app = GameApp(page)
        await app.mount()
        app.mode_picker.value = "smart"
        app.side_picker.value = str(BOY)
        await app.start_game()
        self.assertTrue(app.thinking)
        app.mode_picker.value = "local"
        await app.start_game()
        before = app.game.clone().__dict__
        await asyncio.gather(*page.tasks)
        self.assertEqual(app.game.__dict__, before)
        self.assertFalse(app.thinking)


if __name__ == "__main__":
    unittest.main()
