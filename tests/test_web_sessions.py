"""Real WebSocket handshake: cloned tab, reload and connection ownership."""

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
import socket
import sys
import unittest

import flet as ft
import msgpack
import uvicorn
from websockets.asyncio.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import create_server
from flet.utils import sha1
from flet_web.fastapi.flet_app_manager import app_manager


class WebSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_cannot_steal_updates_and_reload_restores_session(self):
        pages = {}

        async def main(page):
            label = ft.Text("initial")

            async def click(event):
                label.value = "clicked"
                page.update()

            page.add(label, ft.TextButton("click", on_click=click))
            pages[page.session.id] = page

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_server(main), log_level="error"))
        task = asyncio.create_task(server.serve(sockets=[listener]))
        agent = "buga-session-regression"

        async def until(predicate):
            async def poll():
                while not predicate():
                    await asyncio.sleep(0.01)
            await asyncio.wait_for(poll(), 3)

        async def register(stack, session_id=""):
            ws = await stack.enter_async_context(connect(f"ws://127.0.0.1:{port}/ws", user_agent_header=agent))
            await ws.send(msgpack.packb([1, {"session_id": session_id, "page_name": "",
                                             "page": {"width": 390, "height": 844, "web": True}}]))
            reply = msgpack.unpackb(await asyncio.wait_for(ws.recv(), 3))
            self.assertEqual(reply[0], 1)
            self.assertEqual(reply[1]["error"], "")
            new_id = reply[1]["session_id"]
            await until(lambda: new_id in pages)
            return ws, new_id

        try:
            await until(lambda: server.started)
            async with AsyncExitStack() as stack:
                first, first_id = await register(stack)
                original = pages[first_id].session.connection
                duplicate, duplicate_id = await register(stack, first_id)
                self.assertNotEqual(first_id, duplicate_id)
                self.assertIs(pages[first_id].session.connection, original)
                await duplicate.close()
                await until(lambda: pages[duplicate_id].session.connection is None)
                self.assertIs(pages[first_id].session.connection, original)

                # The original tab still receives its own button's patch.
                button = pages[first_id].controls[1]
                await first.send(msgpack.packb([3, {"target": button._i, "name": "click", "data": None}]))
                async def clicked_patch():
                    while b"clicked" not in await first.recv():
                        pass
                await asyncio.wait_for(clicked_patch(), 3)
                await first.close()
                await until(lambda: pages[first_id].session.connection is None)
                reloaded, reloaded_id = await register(stack, first_id)
                self.assertEqual(first_id, reloaded_id)
                self.assertEqual(pages[reloaded_id].controls[0].value, "clicked")
                self.assertIsNot(pages[first_id].session.connection, original)
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, 5)
            for session_id in pages:
                await app_manager.delete_session(f"_{session_id}_{sha1(agent)}")
            listener.close()


if __name__ == "__main__":
    unittest.main()
