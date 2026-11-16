"""Headless dynamic-web server; all players connect to this same process."""

import os

import flet as ft
import uvicorn

from web_sessions import IsolateLiveSessions


def create_server(main=None):
    if main is None:
        from main import main
    # Use the same web renderer across browsers by default. Flet still
    # honours FLET_WEB_RENDERER for browser-specific diagnosis.
    app = ft.run(main, export_asgi_app=True, web_renderer=ft.WebRenderer.CANVAS_KIT)
    app.add_middleware(IsolateLiveSessions)
    return app


def run_server(main=None):
    host = os.environ.get("BUGA_HOST") or os.environ.get("FLET_SERVER_IP") or "127.0.0.1"
    port = int(os.environ.get("BUGA_PORT") or os.environ.get("FLET_SERVER_PORT") or "8550")
    app = create_server(main)
    prefix = os.environ.get("FLET_DISPLAY_URL_PREFIX")
    if prefix:
        # Preserve `flet run --web` browser discovery and hot reload.
        app.add_event_handler("startup", lambda: print(prefix, f"http://{host}:{port}", flush=True))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
