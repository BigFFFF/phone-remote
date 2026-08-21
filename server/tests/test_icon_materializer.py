from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

from PIL import Image

from phone_remote.icon_materializer import IconMaterializer


def test_website_icon_is_discovered_and_converted_to_png(tmp_path: Path) -> None:
    icon_buffer = BytesIO()
    Image.new("RGBA", (48, 48), (25, 200, 110, 255)).save(icon_buffer, format="PNG")
    icon_data = icon_buffer.getvalue()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/icon.png":
                body, content_type = icon_data, "image/png"
            else:
                body = b'<html><head><link rel="icon" sizes="48x48" href="/icon.png"></head></html>'
                content_type = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    destination = tmp_path / "website.png"
    try:
        assert IconMaterializer(tmp_path).materialize_website(
            f"http://127.0.0.1:{server.server_port}/page", destination
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    with Image.open(destination) as result:
        assert result.format == "PNG"
        assert result.size == (48, 48)
