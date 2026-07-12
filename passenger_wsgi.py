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

# Passenger expects a WSGI callable named `application`.
# FastAPI is ASGI-only — bridge it synchronously using asyncio.run().
import asyncio
import traceback
from io import BytesIO

# ---------------------------------------------------------------------------
# 3.  Import the FastAPI app and wrap it for Passenger.
#     Passenger can serve ASGI apps directly when uvicorn is not available;
#     we use the standard approach of exposing the ASGI app via the
#     `application` name.  If your cPanel host supports it you can also
#     use `uvicorn` as the startup command instead (see deployment guide).
# ---------------------------------------------------------------------------
from portfolio_tracker.main import app  # FastAPI / Starlette ASGI app

# HTTP status reason phrases
_STATUS_REASONS = {
    200: "OK", 201: "Created", 204: "No Content", 301: "Moved Permanently",
    302: "Found", 307: "Temporary Redirect", 400: "Bad Request",
    401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    405: "Method Not Allowed", 409: "Conflict", 422: "Unprocessable Entity",
    429: "Too Many Requests", 500: "Internal Server Error",
    502: "Bad Gateway", 503: "Service Unavailable",
}


def _build_scope(environ):
    headers = []
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            header_name = key[5:].replace("_", "-").lower().encode()
            headers.append((header_name, value.encode()))
    if "CONTENT_TYPE" in environ and environ["CONTENT_TYPE"]:
        headers.append((b"content-type", environ["CONTENT_TYPE"].encode()))
    if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
        headers.append((b"content-length", environ["CONTENT_LENGTH"].encode()))

    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": environ.get("SERVER_PROTOCOL", "HTTP/1.1").split("/")[-1],
        "method": environ["REQUEST_METHOD"].upper(),
        "headers": headers,
        "path": environ.get("PATH_INFO", "/"),
        "query_string": environ.get("QUERY_STRING", "").encode(),
        "root_path": environ.get("SCRIPT_NAME", ""),
        "server": (
            environ.get("SERVER_NAME", "localhost"),
            int(environ.get("SERVER_PORT", 80)),
        ),
        "scheme": environ.get("wsgi.url_scheme", "https"),
    }


def application(environ, start_response):
    scope = _build_scope(environ)

    # Read body safely, respecting Content-Length
    wsgi_input = environ.get("wsgi.input") or BytesIO()
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = wsgi_input.read(content_length) if content_length > 0 else b""
    except (ValueError, OSError):
        body = b""

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
            chunk = message.get("body", b"")
            if chunk:
                response_body.append(chunk)

    async def run():
        await app(scope, receive, send)

    try:
        asyncio.run(run())
    except Exception:
        traceback.print_exc()
        # Return a plain 500 so LiteSpeed doesn't swallow the error
        start_response("500 Internal Server Error", [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", environ.get("HTTP_ORIGIN", "*")),
            ("Access-Control-Allow-Credentials", "true"),
        ])
        return [b'{"detail":"Internal server error"}']

    if not response_started:
        start_response("500 Internal Server Error", [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", environ.get("HTTP_ORIGIN", "*")),
            ("Access-Control-Allow-Credentials", "true"),
        ])
        return [b'{"detail":"No response from application"}']

    status_code, raw_headers = response_started[0]
    reason = _STATUS_REASONS.get(status_code, "Unknown")
    headers = [(k.decode("latin-1"), v.decode("latin-1")) for k, v in raw_headers]
    start_response(f"{status_code} {reason}", headers)
    return response_body
