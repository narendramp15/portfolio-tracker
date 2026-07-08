"""
cPanel Passenger WSGI entry point for Portfolio Tracker.

cPanel's Python Selector uses Phusion Passenger, which looks for this file
at the application root. It must expose a callable named `application`.
"""

import os
import sys

# ---------------------------------------------------------------------------
# 1.  Make sure the project root is on sys.path so imports resolve correctly.
#     cPanel sets the CWD to the application root, but sys.path may not
#     include it.
# ---------------------------------------------------------------------------
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# ---------------------------------------------------------------------------
# 2.  Load environment variables from .env (optional but recommended).
#     If python-dotenv is not yet installed, this import is skipped silently.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_ROOT, ".env"))
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 3.  Import the FastAPI app and wrap it for Passenger.
#     Passenger can serve ASGI apps directly when uvicorn is not available;
#     we use the standard approach of exposing the ASGI app via the
#     `application` name.  If your cPanel host supports it you can also
#     use `uvicorn` as the startup command instead (see deployment guide).
# ---------------------------------------------------------------------------
from portfolio_tracker.main import app  # FastAPI / Starlette ASGI app

# Passenger expects a WSGI callable named `application`.
# FastAPI is ASGI-only, so we wrap it with asgiref's WsgiToAsgi adapter.
# If asgiref is not available we fall back to a simple ASGI-to-WSGI shim.
try:
    from asgiref.wsgi import WsgiToAsgi  # type: ignore

    # asgiref's adapter goes the other way; use the ASGI app directly with
    # a helper that bridges synchronously.
    # Actually use the correct asgiref wrapper: AsgiHandler / run_asgi_threaded
    raise ImportError("use built-in shim below")
except ImportError:
    # Minimal synchronous ASGI→WSGI bridge using asyncio
    import asyncio
    from io import BytesIO

    def _build_scope(environ):
        headers = [
            (k.lower().encode(), v.encode())
            for k, v in (
                (
                    key[5:].replace("_", "-"),
                    value,
                )
                for key, value in environ.items()
                if key.startswith("HTTP_")
            )
        ]
        # Add Content-Type and Content-Length if present
        if "CONTENT_TYPE" in environ:
            headers.append((b"content-type", environ["CONTENT_TYPE"].encode()))
        if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
            headers.append((b"content-length", environ["CONTENT_LENGTH"].encode()))

        return {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": environ["REQUEST_METHOD"].upper(),
            "headers": headers,
            "path": environ.get("PATH_INFO", "/"),
            "query_string": environ.get("QUERY_STRING", "").encode(),
            "root_path": environ.get("SCRIPT_NAME", ""),
            "server": (
                environ.get("SERVER_NAME", "localhost"),
                int(environ.get("SERVER_PORT", 80)),
            ),
        }

    def application(environ, start_response):
        scope = _build_scope(environ)
        body = environ.get("wsgi.input", BytesIO()).read()
        response_started = []
        response_body = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                response_started.append(
                    (message["status"], message.get("headers", []))
                )
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(app(scope, receive, send))
        finally:
            loop.close()

        status_code, raw_headers = response_started[0]
        headers = [
            (k.decode(), v.decode()) for k, v in raw_headers
        ]
        start_response(f"{status_code} OK", headers)
        return response_body
