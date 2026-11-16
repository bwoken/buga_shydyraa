"""Stable play surface, compact essentials and on-demand secondary panels.

Desktop keeps the board beside a bounded information column. A phone gets
a header, a turn/statistics strip, the board and a bottom action bar. Forms
open in dialogs or bottom sheets instead of lengthening the play screen.
"""

import flet as ft

from board import BoardView, INK, MUTED, ACCENT, SURFACE, LEGAL_STEP, LEGAL_CAPTURE
from i18n import LANGUAGES
from layout import (fit_layout, BOARD_PADDING, MOBILE_HEADER, MOBILE_STATUS, MOBILE_ACTIONS)
from logic import BULL, BOY, MOVES_WITHOUT_CAPTURE_LIMIT


class GameView:
    def __init__(self, app):
        self.app = app
        self.board = BoardView(app.on_node)
        self.title = self.text("", 24, weight=ft.FontWeight.BOLD)
        self.subtitle = self.text("", 12, MUTED)
        self.account = ft.TextButton("", on_click=app.show_account, expand=True)
        self.settings_button = ft.IconButton(ft.Icons.SETTINGS, on_click=self.open_settings)
        self.header = self.card([self.title, self.subtitle, ft.Row([self.account, self.settings_button])])
        self.status_text = self.text("", 16, weight=ft.FontWeight.BOLD, height=44,
                                      max_lines=2, expand=True)
        self.mode_tag = self.text("", 10, ACCENT)
        self.status = ft.Row([self.status_text, self.mode_tag])
        self.progress = ft.ProgressBar(color=ACCENT, bar_height=3, visible=False)
        self.notice = self.text("", 12, LEGAL_STEP, visible=False, max_lines=2)
        self.undo = ft.OutlinedButton("", on_click=app.undo, expand=True)
        self.new_game = ft.FilledButton("", on_click=self.open_new_game, expand=True)
        self.footer = ft.Row([self.undo, self.new_game], spacing=8)
        self.legend_labels = [self.text("", 11, MUTED), self.text("", 11, MUTED)]
        self.legend = ft.Row([ft.Row([
            ft.Container(width=9, height=9, bgcolor=color, border_radius=5), label], spacing=5)
            for label, color in zip(self.legend_labels, (LEGAL_STEP, LEGAL_CAPTURE))], spacing=16)
        self.game_card = self.card([self.status, ft.Container(self.progress, height=3),
                                    self.notice, self.footer, self.legend])
        self.stats_label = self.text("", 11, MUTED)
        self.reserve, self.captured = self.text("", 16), self.text("", 16, ACCENT)
        self.quiet, self.search = self.text("", 12, MUTED), self.text("", 12, MUTED, visible=False)
        self.stats_card = self.card([self.stats_label, ft.Row([self.reserve, self.captured], wrap=True),
                                     self.quiet, self.search])
        self.hint = self.text("", 13, MUTED, height=40, max_lines=3)
        self.online_button = ft.OutlinedButton("", on_click=self.open_online, expand=True)
        self.rules = ft.TextButton("", on_click=app.show_rules, expand=True)
        self.help_card = self.card([self.hint, ft.Row([self.online_button, self.rules])])
        self.sidebar_column = ft.Column([self.header, self.game_card, self.stats_card, self.help_card], spacing=10)
        self.sidebar = ft.Container(self.sidebar_column)

        # Secondary controls remain in memory and are mounted only in a panel.
        self.new_game_label = self.text("", 11, MUTED)
        self.start = ft.FilledButton("", on_click=app.start_game)
        app.mode_picker.expand = app.side_picker.expand = True
        self.settings_card = self.card([self.new_game_label,
            ft.Row([app.mode_picker, app.side_picker], spacing=10), self.start])
        self.create = ft.OutlinedButton("", on_click=app.create_room)
        self.join = ft.FilledButton("", on_click=app.join_room)
        app.code_field.expand = True
        self.online_hint = self.text("", 12, MUTED)
        self.online_card = self.card([self.create, ft.Row([app.code_field, self.join]), self.online_hint])
        self.invite = ft.TextField(read_only=True)
        self.your_side = self.text("", 16)
        self.seats = {side: self.text("", 13, MUTED) for side in (BULL, BOY)}
        self.leave = ft.OutlinedButton("", on_click=app.leave_room)
        self.leave_hint = self.text("", 12, MUTED)
        self.room_card = self.card([self.invite, self.your_side, *self.seats.values(),
                                    self.leave, self.leave_hint], visible=False)
        self.online_panel = ft.Column([self.online_card, self.room_card], spacing=0)
        self.draft = self.text("", 11, LEGAL_STEP, visible=False)
        self.preferences = self.card([app.language_picker, app.number_switch, app.animation_switch, self.draft])
        self.detail_stats = self.text("", 15)
        self.detail_hint = self.text("", 13, MUTED)
        self.detail_rules = ft.TextButton("", on_click=app.show_rules)
        self.information = self.card([self.detail_stats, self.detail_hint, self.detail_rules])

        # Mobile controls have fixed heights; variable labels cannot move the board.
        self.mobile_title = self.text("", 16, weight=ft.FontWeight.BOLD, expand=True, max_lines=1)
        self.mobile_account = ft.IconButton(ft.Icons.PERSON_OUTLINE, on_click=app.show_account)
        self.mobile_settings = ft.IconButton(ft.Icons.SETTINGS, on_click=self.open_settings)
        self.mobile_header = ft.Row([self.mobile_title, self.mobile_account, self.mobile_settings],
                                    height=MOBILE_HEADER, spacing=0)
        self.mobile_turn = self.text("", 12, weight=ft.FontWeight.BOLD, expand=True, max_lines=2)
        self.mobile_counts = self.text("", 11, MUTED, max_lines=2)
        self.mobile_progress = ft.ProgressBar(color=ACCENT, bar_height=3, visible=False)
        self.mobile_status = ft.Column([
            ft.Row([self.mobile_turn, self.mobile_counts], height=MOBILE_STATUS - 3, spacing=8),
            ft.Container(self.mobile_progress, height=3),
        ], height=MOBILE_STATUS, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.mobile_undo = ft.IconButton(ft.Icons.UNDO, on_click=app.undo, width=44, height=44)
        self.mobile_new = ft.FilledButton("", on_click=self.open_new_game, expand=True, height=44)
        self.mobile_online = ft.IconButton(ft.Icons.PEOPLE_OUTLINE, on_click=self.open_online, width=44, height=44)
        self.mobile_info = ft.IconButton(ft.Icons.INFO_OUTLINE, on_click=self.open_information, width=44, height=44)
        self.mobile_actions = ft.Row([self.mobile_undo, self.mobile_new, self.mobile_online, self.mobile_info],
                                     height=MOBILE_ACTIONS, spacing=4)
        self.board_card = ft.Container(self.board.control, padding=BOARD_PADDING,
                                        bgcolor=SURFACE, border_radius=18)
        self.mobile_board_holder = ft.Container(self.board_card, expand=True, alignment=ft.Alignment.CENTER)
        self.mobile_side = ft.Container(ft.Column([
            self.mobile_header, self.mobile_status, ft.Container(expand=True), self.mobile_actions], spacing=4))
        self.body_slot = ft.Container()
        self.root = ft.Container(self.body_slot)
        self.body, self.compact, self.layout = None, None, None
        self._body_mode = None
        self._language = None
        self._panel = self._panel_key = self._panel_title = self._panel_close = None
        self._panel_notice = None
        self._pending_panel = None

    @staticmethod
    def text(value, size=14, color=INK, **kwargs):
        return ft.Text(value, size=size, color=color, **kwargs)

    @staticmethod
    def card(controls, **kwargs):
        return ft.Container(ft.Column(controls, spacing=8), bgcolor=SURFACE,
                            border_radius=18, padding=14, **kwargs)

    def _localize(self):
        a, t = self.app, self.app.t
        if self._language == a.language:
            return
        for control, key in ((self.title, "title"), (self.mobile_title, "title"),
                             (self.subtitle, "subtitle"), (self.draft, "draft"),
                             (self.new_game_label, "new_game"), (self.leave_hint, "leave_hint"),
                             (self.stats_label, "statistics")):
            control.value = t(key)
        for control, key in ((self.undo, "undo"), (self.new_game, "new_game"), (self.mobile_new, "new_game"),
                             (self.start, "start"), (self.create, "create_room"), (self.join, "join"),
                             (self.leave, "leave"), (self.rules, "rules"), (self.detail_rules, "rules")):
            control.content = t(key)
        for control, key in ((a.mode_picker, "mode"), (a.side_picker, "your_side"),
                             (a.code_field, "room_code"), (a.number_switch, "node_numbers"),
                             (a.language_picker, "language"), (a.animation_switch, "animations"),
                             (self.invite, "invite_code")):
            control.label = t(key)
        for control, key in ((self.settings_button, "settings"), (self.mobile_settings, "settings"),
                             (self.mobile_undo, "undo"), (self.mobile_online, "online_action"),
                             (self.mobile_info, "more")):
            control.tooltip = t(key)
        a.mode_picker.options = [ft.DropdownOption(mode, t(f"mode_{mode}"))
                                 for mode in ("local", "easy", "smart", "expert")]
        a.side_picker.options = [ft.DropdownOption(str(side), a.side_name(side)) for side in (BULL, BOY)]
        a.language_picker.options = [ft.DropdownOption(code, name) for code, name in LANGUAGES.items()]
        self.legend_labels[0].value, self.legend_labels[1].value = t("legal_step"), t("legal_capture")
        self.draft.visible = a.language == "tyv"
        self._language = a.language

    def _update_board(self):
        a = self.app
        legal = a.game.get_legal_moves_for_node(a.selected) if a.selected else []
        self.board.update(a.game, a.selected, legal, width=self.layout.board_width,
                          show_numbers=a.number_switch.value,
                          language=a.language, animations=a.animation_switch.value)

    def update_selection(self):
        ft.context.disable_auto_update()
        self._update_board()
        self.app.page.update(self.board.control)

    def dismiss_panel(self):
        self._pending_panel = None
        if self._panel and self._panel.open:
            # Close our panel, even if a rules dialog is above it.
            self._panel.open = False
            self.app.page.update(self._panel)

    async def _panel_dismissed(self, event):
        # Flet has now unmounted the previous dialog and its controls. Reusing
        # those controls before this acknowledgement lets its late unmount
        # remove event handlers belonging to the newly opened panel.
        if event.control is not self._panel:
            return
        self._panel = None
        pending, self._pending_panel = self._pending_panel, None
        if pending:
            self._show_panel(*pending)

    async def reconnect(self):
        if self._panel is not None and not self._panel.open:
            # A refreshed client cannot acknowledge an old closing animation.
            # Finish Flet's wrapped dismissal before reusing the form controls.
            panel = self._panel
            await panel.on_dismiss(ft.ControlEvent(control=panel, name="dismiss", data=None))

    async def open_new_game(self, e=None):
        if not self.app.room:
            self._show_panel("new_game", self.settings_card, 260)

    async def open_online(self, e=None):
        self._show_panel("room" if self.app.room else "play_friend", self.online_panel, 350)

    async def open_settings(self, e=None):
        self._show_panel("settings", self.preferences, 290)

    async def open_information(self, e=None):
        self._show_panel("more", self.information, 300)

    def _show_panel(self, key, content, desired_height):
        if self._panel is not None:
            if self._panel.open and self._panel_key == key:
                return
            self.dismiss_panel()
            self._pending_panel = (key, content, desired_height)
            return
        page, t = self.app.page, self.app.t
        self._panel_key = key
        self._panel_title = self.text(t(key), 20, weight=ft.FontWeight.BOLD)
        self._panel_close = ft.TextButton(t("close"), on_click=lambda e: self.dismiss_panel())
        self._panel_notice = self.text(t(self.app.notice) if self.app.notice else "", 13, LEGAL_STEP,
                                       visible=bool(self.app.notice))
        panel_content = ft.Column([content, self._panel_notice], spacing=8)
        height = min(desired_height, self.layout.main_height * 0.7)
        if self.layout.compact:
            panel_body = ft.Container(ft.Column([
                ft.Row([self._panel_title, self._panel_close], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Column([panel_content], height=height, scroll=ft.ScrollMode.AUTO),
            ], tight=True), padding=16, width=self.layout.content_width)
            self._panel = ft.BottomSheet(panel_body, scrollable=True, show_drag_handle=True,
                                         use_safe_area=True, bgcolor=SURFACE, on_dismiss=self._panel_dismissed)
        else:
            self._panel = ft.AlertDialog(title=self._panel_title,
                content=ft.Column([panel_content], width=440, height=height, scroll=ft.ScrollMode.AUTO),
                actions=[self._panel_close], bgcolor=SURFACE, on_dismiss=self._panel_dismissed)
        page.show_dialog(self._panel)

    def render(self, *, flush=True):
        ft.context.disable_auto_update()
        a, t, page = self.app, self.app.t, self.app.page
        page.title = t("window_title")
        width, height = a.viewport_size or (page.width or 1000, page.height or 800)
        self.layout = layout = fit_layout(width, height)
        self.root.width, self.root.height = layout.content_width, layout.main_height
        self.body_slot.height = layout.main_height
        self.board_card.width = layout.board_width + 2 * BOARD_PADDING
        self.sidebar.width, self.sidebar.height = layout.sidebar_width, layout.main_height
        self.mobile_side.width, self.mobile_side.height = layout.sidebar_width, layout.main_height
        self._localize()
        self._update_board()
        result = a.game.check_winner()
        if result:
            status = t(a.RESULT_KEYS[result])
        elif a.room and not a.room.ready:
            status = t("waiting")
        elif a.thinking:
            status = t("thinking")
        else:
            status = t("turn", side=a.side_name(a.game.current_turn))
        self.status_text.value = status
        self.mobile_turn.value = t(a.notice) if a.notice else status
        self.mobile_turn.tooltip = self.mobile_turn.value if len(self.mobile_turn.value) > 40 else None
        self.mode_tag.value = t("online" if a.room else "local" if a.mode == "local" else "against_ai")
        thinking = a.thinking and not result and not a.room
        for progress in (self.progress, self.mobile_progress):
            progress.visible = thinking
            progress.value = None if thinking and a.animation_switch.value else 1
        self.notice.visible, self.notice.value = bool(a.notice), t(a.notice) if a.notice else ""
        self.undo.disabled = self.mobile_undo.disabled = bool(a.room) or not a.game.history
        self.new_game.disabled = self.mobile_new.disabled = bool(a.room)
        self.start.width = layout.sidebar_width
        self.create.disabled = self.join.disabled = not page.web
        self.online_hint.value = t("guests_online" if page.web else "web_only")
        self.online_card.visible, self.room_card.visible = a.room is None, a.room is not None
        self.online_button.content = t("room" if a.room else "online_action")
        self.account.content = f"{a.identity.name} · {t('guest' if a.identity.guest else 'account')}"
        self.account.disabled = self.mobile_account.disabled = bool(a.room)
        self.mobile_account.tooltip = self.account.content
        if a.room:
            self.invite.value = a.room.code
            self.your_side.value = t("you", side=a.side_name(a.room.side))
            for side, label in self.seats.items():
                label.value = t("seat", side=a.side_name(side), name=a.room.names.get(side, t("waiting_name")))
        remaining = sum(p == BOY for p in a.game.board.values()) + a.game.unused_boys
        self.reserve.value, self.captured.value = t("reserve", count=a.game.unused_boys), t("captured", count=24 - remaining)
        self.quiet.value = t("quiet", count=a.game.moves_without_capture, limit=MOVES_WITHOUT_CAPTURE_LIMIT)
        self.mobile_counts.value = t("reserve_short", count=a.game.unused_boys) + " · " + t("captured_short", count=24 - remaining)
        self.search.visible = bool(a.search_stats)
        if a.search_stats:
            self.search.value = t("search", depth=a.search_stats[0], nodes=a.search_stats[1])
        hint = t("hint_over" if result else "hint_place" if
                 a.game.current_turn == BOY and a.game.unused_boys else "hint_move")
        self.hint.value = self.detail_hint.value = hint
        self.detail_stats.value = "\n".join([self.reserve.value, self.captured.value, self.quiet.value,
                                            self.search.value if a.search_stats else "", self.notice.value]).strip()
        # Reduce secondary decoration in unusually short desktop windows.
        self.subtitle.visible = self.hint.visible = height >= 620
        body_mode = (layout.compact, layout.landscape)
        if self._body_mode != body_mode:
            self._body_mode = body_mode
            self.compact = layout.compact
            self.body = (ft.Row([self.board_card, self.mobile_side], spacing=16,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER) if layout.landscape else
                         ft.Column([self.mobile_header, self.mobile_status, self.mobile_board_holder, self.mobile_actions],
                                   spacing=4, height=layout.main_height,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER) if layout.compact else
                         ft.Row([self.board_card, self.sidebar], spacing=16,
                                vertical_alignment=ft.CrossAxisAlignment.START))
            self.body_slot.content = self.body
        self.body.height = layout.main_height if layout.compact else None
        if self._panel and self._panel.open:
            if self._panel_key in ("room", "play_friend"):
                self._panel_key = "room" if a.room else "play_friend"
            self._panel_title.value = t(self._panel_key)
            self._panel_close.content = t("close")
            self._panel_notice.visible = bool(a.notice)
            self._panel_notice.value = t(a.notice) if a.notice else ""
        if flush:
            # Send the board, turn status and open room panel in one patch.
            # Separate patches for piece controls can leave Flutter's stack stale.
            page.update()
