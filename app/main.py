import asyncio
import json
import logging
import os
import threading
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from app.bot.bot import bot
from app.bot.dispatcher import dp
from app.app.config.settings import settings
from app.storage import get_all_products, get_sellers, get_seller_rating

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBAPP_FILE = os.path.join(BASE_DIR, "webapp", "index.html")

# file_id -> (file_path, ts) keshi (Telegram file_path vaqtinchalik bo'ladi)
_PHOTO_CACHE: dict = {}
_CACHE_TTL = 60 * 30  # 30 daqiqa


def build_products_payload() -> list:
    sellers = get_sellers()
    out = []
    for p in get_all_products():
        sid = p.get("seller_id")
        s = sellers.get(str(sid), {})
        rating, cnt = get_seller_rating(int(sid)) if sid is not None else (0.0, 0)
        out.append({
            "id":          p.get("id"),
            "name":        p.get("name", ""),
            "description": p.get("description", ""),
            "price":       p.get("price", 0),
            "old_price":   p.get("old_price"),
            "shop_name":   p.get("shop_name", s.get("shop_name", "")),
            "seller_id":   sid,
            "city":        s.get("city", ""),
            "rating":      rating,
            "reviews":     cnt,
            "has_photo":   bool(p.get("photo")),
        })
    return out


def _tg_file_path(file_id: str):
    now = time.time()
    cached = _PHOTO_CACHE.get(file_id)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0]
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
        if data.get("ok"):
            fp = data["result"]["file_path"]
            _PHOTO_CACHE[file_id] = (fp, now)
            return fp
    except Exception as e:
        logger.warning("getFile xato: %s", e)
    return None


def _product_photo_id(product_id: int):
    for p in get_all_products():
        if p.get("id") == product_id:
            return p.get("photo")
    return None


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/healthz", "/health"):
            self._send(200, b"OK"); return

        if path == "/api/products":
            body = json.dumps(build_products_payload(), ensure_ascii=False).encode()
            self._send(200, body, "application/json; charset=utf-8"); return

        if path == "/api/photo":
            pid = qs.get("id", [None])[0]
            file_id = qs.get("file_id", [None])[0]
            if not file_id and pid is not None:
                try:
                    file_id = _product_photo_id(int(pid))
                except Exception:
                    file_id = None
            if not file_id:
                self._send(404, b"no photo"); return
            fp = _tg_file_path(file_id)
            if not fp:
                self._send(404, b"not found"); return
            try:
                file_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{fp}"
                with urllib.request.urlopen(file_url, timeout=15) as r:
                    img = r.read()
                ctype = "image/jpeg"
                low = fp.lower()
                if low.endswith(".png"):
                    ctype = "image/png"
                elif low.endswith(".webp"):
                    ctype = "image/webp"
                self._send(200, img, ctype, {"Cache-Control": "public, max-age=3600"})
            except Exception:
                _PHOTO_CACHE.pop(file_id, None)
                self._send(404, b"fetch failed")
            return

        if path in ("/", "/app", "/index.html"):
            try:
                with open(WEBAPP_FILE, "rb") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(200, b"OK")
            return

        self._send(404, b"not found")


def run_http_server():
    port = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8080")))
    server = HTTPServer(("0.0.0.0", port), AppHandler)
    logger.info("HTTP server (Mini App + API) :%s da ishlamoqda", port)
    server.serve_forever()


async def main():
    logger.info("Man Market starting...")
    threading.Thread(target=run_http_server, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
