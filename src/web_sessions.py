"""Backport Flet #6513 for the pinned 0.80.5 dynamic-web transport.

Chrome Duplicate Tab copies sessionStorage. A live session must not be
reattached to that second socket: it would steal the first tab's updates.
Disconnected sessions still reconnect normally. No SDK files are changed.
Remove this adapter when upgrading to a Flet release containing #6513.
"""

import msgpack
from flet.messaging.protocol import ClientAction
from flet.utils import sha1
from flet_web.fastapi.flet_app_manager import app_manager


class IsolateLiveSessions:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await self.app(scope, receive, send)
        registered = False

        async def isolated_receive():
            nonlocal registered
            message = await receive()
            payload = message.get("bytes")
            if registered or payload is None:
                return message
            data = msgpack.unpackb(payload)
            if data[0] != ClientAction.REGISTER_CLIENT.value:
                return message
            registered = True
            body = data[1]
            session_id = body.get("session_id")
            if session_id:
                ip = (scope.get("client") or ("", 0))[0]
                if ip in ("127.0.0.1", "::1"):
                    ip = ""
                user_agent = dict(scope.get("headers", [])).get(b"user-agent", b"").decode("latin-1")
                page_name = scope["path"].rsplit("/", 1)[0].lstrip("/")
                key = f"{page_name}_{session_id}_{sha1(ip + user_agent)}"
                session = await app_manager.get_session(key)
                if session is not None and session.connection is not None:
                    body["session_id"] = ""
                    message = {**message, "bytes": msgpack.packb(data, use_bin_type=True)}
            return message

        await self.app(scope, isolated_receive, send)
