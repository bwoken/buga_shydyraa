"""Flet presentation and session controller.

All UI changes run on the page's event loop. CPU work uses private game
copies in a worker; generation numbers discard results after restart/undo.
"""

import asyncio
import logging
import math
import os
from pathlib import Path
import sqlite3

import flet as ft
import flet.canvas as cv

from auth import AuthStore, AuthError
from board import INK, MUTED, ACCENT, BACKGROUND
from i18n import translate
from ui import GameView
from layout import PAGE_PADDING
from bot import EasyBot, SmartBot
from logic import (BugaGame, Move, BULL, BOY, EMPTY, BULLS_WIN, BOYS_WIN,
                   DRAW_REPETITION, DRAW_NO_CAPTURE)
from online import RoomService, RoomError

ROOMS = RoomService()
STORAGE = Path(os.environ.get("BUGA_DATA_DIR") or
               os.environ.get("FLET_APP_STORAGE_DATA_DIR") or Path.cwd() / "data")
ACCOUNTS = AuthStore(STORAGE / "accounts.sqlite3")
LOGGER = logging.getLogger(__name__)
RESULT_KEYS = {BULLS_WIN: "win_bulls", BOYS_WIN: "win_boys",
               DRAW_REPETITION: "draw_repeat", DRAW_NO_CAPTURE: "draw_quiet"}


class GameApp:
    RESULT_KEYS = RESULT_KEYS

    def __init__(self, page: ft.Page):
        self.page = page
        self.language = "ru"
        self.viewport_size = None
        self.has_measured_viewport = False
        self.identity = ACCOUNTS.guest()
        self.game = BugaGame()
        self.mode = "local"
        self.bot_side = None
        self.selected = None
        self.room = None
        self.generation = 0
        self.thinking = False
        self.search_stats = None
        self.notice = ""
        self.poll_task = None
        self.mode_picker = ft.Dropdown(value="smart", text_size=13, content_padding=10)
        self.side_picker = ft.Dropdown(value=str(BULL), text_size=13, content_padding=10)
        self.code_field = ft.TextField(max_length=8, text_size=13,
                                       capitalization=ft.TextCapitalization.CHARACTERS)
        self.number_switch = ft.Switch(value=False,
                                       on_change=self.refresh_event)
        self.language_picker = ft.Dropdown(value="ru", width=155, text_size=13,
                                            content_padding=10, on_select=self.change_language)
        self.animation_switch = ft.Switch(value=True, on_change=self.refresh_event)
        self.view = GameView(self)
        self.root = self.view.root

    async def mount(self):
        page = self.page
        page.title = self.t("window_title")
        page.bgcolor = BACKGROUND
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(color_scheme_seed=ACCENT, font_family="Segoe UI")
        page.padding = PAGE_PADDING
        page.scroll = None
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.on_resize = self.resize
        page.on_close = self.close
        page.on_connect = self.reconnect
        self.view.render(flush=False)
        if page.web:
            # Measure the available space independently of the initial page
            # metrics and of the explicitly sized game root.
            viewport = cv.Canvas(
                content=ft.Container(self.root, alignment=ft.Alignment.TOP_CENTER),
                expand=True,
                on_resize=self.resize_viewport,
            )
            page.add(viewport)
        else:
            page.add(self.root)

    @staticmethod
    def text(value, size=14, color=INK, **kwargs):
        return ft.Text(value, size=size, color=color, **kwargs)

    def t(self, key, **values):
        return translate(self.language, key, **values)

    def side_name(self, side):
        return self.t("bulls" if side == BULL else "boys")

    async def change_language(self, e=None):
        self.language = self.language_picker.value
        # Flutter does not provide a built-in Tuvan Material locale. App
        # strings are Tuvan; framework widgets use Russian as their fallback.
        self.page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("ru"), ft.Locale("en")],
            current_locale=ft.Locale("en" if self.language == "en" else "ru"))
        self.render()

    async def refresh_event(self, e):
        self.render()

    async def reconnect(self, e=None):
        await self.view.reconnect()
        self.render()

    async def resize(self, e):
        if not self.has_measured_viewport and self.valid_viewport(e.width, e.height):
            self.update_viewport(e.width, e.height)

    async def resize_viewport(self, e):
        if self.valid_viewport(e.width, e.height):
            self.has_measured_viewport = True
            # The canvas is measured inside the padding. fit_layout expects
            # the whole window and subtracts the padding itself.
            self.update_viewport(e.width + 2 * PAGE_PADDING, e.height + 2 * PAGE_PADDING)

    @staticmethod
    def valid_viewport(width, height):
        # Hidden browser surfaces can report zero dimensions.
        return all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                   for value in (width, height))

    def update_viewport(self, width, height):
        if self.viewport_size != (width, height):
            self.viewport_size = (width, height)
            self.render()

    def render(self):
        self.view.render()

    def invalidate(self):
        self.generation += 1
        self.view.board.reset()
        self.thinking = False
        self.selected = None
        self.search_stats = None
        self.notice = ""

    async def start_game(self, e=None):
        if self.room:
            return
        self.view.dismiss_panel()
        self.invalidate()
        self.game = BugaGame()
        self.mode = self.mode_picker.value
        self.bot_side = -int(self.side_picker.value) if self.mode != "local" else None
        self.schedule_bot(render=False)
        self.render()

    async def on_node(self, node):
        if self.thinking or self.game.check_winner():
            return
        if self.room and (not self.room.ready or self.room.side != self.game.current_turn):
            return
        if self.bot_side == self.game.current_turn and not self.room:
            return
        move = None
        if self.game.current_turn == BOY and self.game.unused_boys:
            if self.game.board[node] == EMPTY:
                move = Move("PLACE", None, node)
        elif self.selected is not None and self.game.is_valid_move(self.selected, node):
            move = Move("MOVE", self.selected, node)
        elif self.game.board[node] == self.game.current_turn:
            self.selected = None if self.selected == node else node
        else:
            self.selected = None
        if move:
            try:
                if self.room:
                    self.room = ROOMS.play(self.room.code, self.identity, move, self.room.revision)
                    self.game = self.room.game
                else:
                    self.game.apply(move)
                self.selected = None
                self.notice = ""
            except RoomError as error:
                self.notice = error.key
            self.schedule_bot(render=False)
            self.render()
        else:
            self.view.update_selection()

    def schedule_bot(self, *, render=True):
        if (self.room or self.thinking or self.bot_side != self.game.current_turn
                or self.game.check_winner()):
            return
        self.thinking = True
        if render:
            self.render()
        self.page.run_task(self.bot_move, self.generation, self.game.clone(), self.mode)

    async def bot_move(self, generation, snapshot, mode):
        bot = (EasyBot(snapshot, snapshot.current_turn) if mode == "easy" else
               SmartBot(snapshot, snapshot.current_turn, depth=8 if mode == "expert" else 6,
                        time_limit=3.0 if mode == "expert" else 1.0))
        try:
            move = await asyncio.to_thread(bot.get_move)
            if generation != self.generation:
                return
            if move:
                self.game.apply(move)
            if isinstance(bot, SmartBot):
                self.search_stats = (bot.completed_depth, bot.nodes)
        except Exception:
            LOGGER.exception("AI search failed")
            if generation == self.generation:
                self.notice = "error_ai"
        finally:
            if generation == self.generation:
                self.thinking = False
                self.render()

    async def undo(self, e=None):
        if self.room:
            return
        self.invalidate()
        if self.bot_side is None:
            self.game.undo_last()
        else:
            self.game.undo_player_move(-self.bot_side)
        self.schedule_bot(render=False)
        self.render()

    async def create_room(self, e=None):
        if not self.page.web or self.room:
            return
        try:
            view = ROOMS.create(self.identity, int(self.side_picker.value))
            self.enter_room(view)
        except RoomError as error:
            self.notice = error.key
            self.render()

    async def join_room(self, e=None):
        if not self.page.web or self.room:
            return
        try:
            view = ROOMS.join(self.code_field.value or "", self.identity)
            self.view.dismiss_panel()
            self.enter_room(view)
        except RoomError as error:
            self.notice = error.key
            self.render()

    def enter_room(self, view):
        self.invalidate()
        self.room = view
        self.game = view.game
        self.bot_side = None
        self.render()
        self.poll_task = self.page.run_task(self.poll_room)

    async def poll_room(self):
        try:
            while self.room:
                await asyncio.sleep(0.6)
                if not self.room:
                    break
                try:
                    view = ROOMS.read_if_changed(self.room.code, self.identity, self.room.revision)
                except RoomError as error:
                    self.room = None
                    self.notice = error.key
                    self.mode = "local"
                    self.render()
                    break
                if view is not None:
                    self.room, self.game = view, view.game
                    self.selected = None
                    self.render()
        except asyncio.CancelledError:
            pass

    async def leave_room(self, e=None):
        self.view.dismiss_panel()
        if self.room:
            try:
                ROOMS.leave(self.room.code, self.identity)
            except RoomError:
                pass
        if self.poll_task:
            self.poll_task.cancel()
            self.poll_task = None
        self.room = None
        self.invalidate()
        self.mode, self.bot_side = "local", None
        self.game = BugaGame()
        self.render()

    async def close(self, e=None):
        self.generation += 1
        if self.poll_task:
            self.poll_task.cancel()
        if self.room:
            try:
                ROOMS.leave(self.room.code, self.identity)
            except RoomError:
                pass

    async def show_account(self, e=None):
        if self.room:
            return
        username = ft.TextField(label=self.t("username"), max_length=24, autofocus=True)
        password = ft.TextField(label=self.t("password"), password=True, can_reveal_password=True,
                                max_length=128)
        error_text = self.text("", 13, "#E7BC74")
        busy = ft.ProgressBar(visible=False)
        pending = False

        async def submit(kind):
            nonlocal pending
            if pending:
                return
            pending = True
            busy.visible = True
            error_text.value = ""
            for action in dialog.actions:
                action.disabled = True
            self.page.update()
            try:
                if kind == "guest":
                    identity = ACCOUNTS.guest(username.value or "")
                else:
                    method = ACCOUNTS.login if kind == "login" else ACCOUNTS.register
                    identity = await asyncio.to_thread(method, username.value or "", password.value or "")
                self.identity = identity
                password.value = ""
                dialog.open = False
                self.render()
            except AuthError as error:
                error_text.value = self.t(error.key)
            except sqlite3.Error:
                LOGGER.exception("Account storage failed")
                error_text.value = self.t("error_storage")
            finally:
                pending = False
                busy.visible = False
                for action in dialog.actions:
                    action.disabled = False
                self.page.update()

        async def login(e):
            await submit("login")

        async def register(e):
            await submit("register")

        async def guest(e):
            await submit("guest")

        dialog = ft.AlertDialog(
            modal=True, title=self.text(self.t("player"), 24),
            content=ft.Column([username, password,
                               self.text(self.t("register_hint"), 12, MUTED),
                               error_text, busy], tight=True, width=330),
            actions=[ft.TextButton(self.t("guest_logout"), on_click=guest),
                     ft.TextButton(self.t("register"), on_click=register),
                     ft.FilledButton(self.t("login"), on_click=login),
                     ft.TextButton(self.t("close"), on_click=lambda e: self.page.pop_dialog())],
            actions_overflow_button_spacing=8,
        )
        self.page.show_dialog(dialog)

    async def show_rules(self, e=None):
        self.page.show_dialog(ft.AlertDialog(
            title=self.text(self.t("how_to_play"), 24),
            content=ft.Column([
                *[self.text(self.t(f"rule_{number}")) for number in range(1, 6)],
                self.text(self.t("rule_variant"), 12, MUTED),
            ], tight=True, width=420, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton(self.t("understood"), on_click=lambda e: self.page.pop_dialog())],
        ))
