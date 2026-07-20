"""aiohttp web-server — Mini App (static do'kon) + JSON API.

Bot bilan bitta event-loop'da ishlaydi (app/main.py da ishga tushiriladi).
"""

import logging
from pathlib import Path

from aiohttp import web

from app.web import api

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


async def _index(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


def build_app() -> web.Application:
    # client_max_size — chek fayli yuklash uchun (10MB chek + zaxira).
    app = web.Application(client_max_size=12 * 1024 * 1024)
    app.router.add_get("/health", _health)
    app.router.add_get("/api/products", api.list_products)
    app.router.add_get("/api/product/{id}", api.get_product)
    app.router.add_get("/api/config", api.get_config)
    app.router.add_get("/api/stats", api.get_stats)
    app.router.add_get("/api/favorites", api.list_favorites)
    app.router.add_post("/api/favorite", api.toggle_favorite_ep)
    app.router.add_post("/api/order", api.create_order)
    # Mini App (static)
    app.router.add_get("/", _index)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)
    return app


async def start_web_server(host: str, port: int) -> web.AppRunner:
    """Web-serverni ishga tushiradi va AppRunner qaytaradi (keyin cleanup uchun)."""
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Mini App web-server tinglayapti: %s:%s", host, port)
    return runner
