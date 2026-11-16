"""Desktop or dynamic-web entry point (Flet 0.80.5)."""

import os

import flet as ft

from app import GameApp


async def main(page: ft.Page):
    await GameApp(page).mount()


if __name__ == "__main__":
    if os.environ.get("FLET_FORCE_WEB_SERVER", "").lower() in ("true", "1"):
        from server import run_server
        run_server(main)
    else:
        ft.run(main)
