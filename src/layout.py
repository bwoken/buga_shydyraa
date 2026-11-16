"""A board-only column spanning the usable window height in landscape."""

from dataclasses import dataclass

BOARD_ASPECT = 620 / 360
PAGE_PADDING = 8
BOARD_PADDING = 8
PANEL_GAP = 16
MOBILE_HEADER = 44
MOBILE_STATUS = 36
MOBILE_ACTIONS = 48
MOBILE_GAPS = 12
MOBILE_CHROME = MOBILE_HEADER + MOBILE_STATUS + MOBILE_ACTIONS + MOBILE_GAPS


@dataclass(frozen=True)
class GameLayout:
    compact: bool
    board_width: float
    sidebar_width: float
    content_width: float
    main_height: float
    landscape: bool = False


def fit_layout(width: float, height: float) -> GameLayout:
    compact = width < 860 or height < 560
    if compact:
        main_height = max(240, height - 2 * PAGE_PADDING)
        if width > height and height < 560:
            sidebar = min(320, width * 0.45)
            board_width = min((main_height - 2 * BOARD_PADDING) / BOARD_ASPECT,
                              width - 2 * PAGE_PADDING - sidebar - PANEL_GAP - 2 * BOARD_PADDING)
            return GameLayout(True, board_width, sidebar,
                              board_width + 2 * BOARD_PADDING + PANEL_GAP + sidebar,
                              main_height, landscape=True)
        board_height = max(1, main_height - MOBILE_CHROME - 2 * BOARD_PADDING)
        content_width = min(720, width - 2 * PAGE_PADDING)
        # Use the column's actual width, including its maximum on tablets/folds.
        board_width = min(content_width - 2 * BOARD_PADDING, board_height / BOARD_ASPECT)
        return GameLayout(True, board_width, content_width, content_width, main_height)
    sidebar = min(480, max(340, width * 0.33))
    main_height = max(280, height - 2 * PAGE_PADDING)
    board_width = min((main_height - 2 * BOARD_PADDING) / BOARD_ASPECT,
                      width - 2 * PAGE_PADDING - sidebar - PANEL_GAP - 2 * BOARD_PADDING)
    board_width = max(120, board_width)
    return GameLayout(False, board_width, sidebar,
                      board_width + 2 * BOARD_PADDING + PANEL_GAP + sidebar, main_height)
