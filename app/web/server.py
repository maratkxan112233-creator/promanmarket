"""aiohttp web-server — Mini App (static do'kon) + JSON API.

Bot bilan bitta event-loop'da ishlaydi (app/main.py da ishga tushiriladi).
"""

import logging
import os
from pathlib import Path

from aiohttp import web

from app.storage import DATA_DIR
from app.web import api, panel_api

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
MEDIA_DIR = Path(DATA_DIR) / "product_images"
os.makedirs(MEDIA_DIR, exist_ok=True)


async def _index(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


def build_app() -> web.Application:
    # client_max_size — chek/rasm yuklash uchun (bir nechta rasm + zaxira).
    app = web.Application(client_max_size=24 * 1024 * 1024)
    app.router.add_get("/health", _health)
    app.router.add_get("/api/products", api.list_products)
    app.router.add_get("/api/product/{id}", api.get_product)
    app.router.add_get("/api/config", api.get_config)
    app.router.add_get("/api/stats", api.get_stats)
    app.router.add_get("/api/favorites", api.list_favorites)
    app.router.add_post("/api/favorite", api.toggle_favorite_ep)
    app.router.add_post("/api/order", api.create_order)
    # Panel — foydalanuvchi rollari
    app.router.add_get("/api/me", panel_api.get_me)
    # Panel — SELLER (o'z do'koni)
    app.router.add_get("/api/seller/products", panel_api.seller_products)
    app.router.add_post("/api/seller/product", panel_api.seller_create_product)
    app.router.add_post("/api/seller/product/{id}", panel_api.seller_update_product)
    app.router.add_post("/api/seller/product/{id}/delete", panel_api.seller_delete_product)
    app.router.add_get("/api/seller/orders", panel_api.seller_orders)
    app.router.add_post("/api/seller/order/{id}/status", panel_api.seller_order_status)
    app.router.add_get("/api/seller/shop", panel_api.seller_shop)
    app.router.add_post("/api/seller/shop", panel_api.seller_update_shop)
    app.router.add_get("/api/seller/stats", panel_api.seller_stats)
    # Panel — ADMIN (barcha mahsulotlar)
    app.router.add_get("/api/admin/products", panel_api.admin_products)
    app.router.add_get("/api/admin/sellers", panel_api.admin_sellers)
    app.router.add_post("/api/admin/product", panel_api.admin_create_product)
    app.router.add_post("/api/admin/product/{id}", panel_api.admin_update_product)
    app.router.add_post("/api/admin/product/{id}/delete", panel_api.admin_delete_product_ep)
    # Mini App (static) + yuklangan mahsulot rasmlari
    app.router.add_get("/", _index)
    app.router.add_static("/media/", MEDIA_DIR, show_index=False)
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
