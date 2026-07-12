"""ASGI / Starlette middleware for the application.

Order of registration matters and is owned by ``portfolio_tracker.main``:
``CORSPreflightMiddleware`` must be the outermost layer so OPTIONS requests
are answered before ``SessionMiddleware`` can reject them.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from portfolio_tracker.config import settings

logger = logging.getLogger(__name__)


class CORSPreflightMiddleware:
    """Raw ASGI middleware that answers OPTIONS preflights before anything else.

    This runs at the lowest level, before SessionMiddleware can reject the
    request, which is required for cross-origin preflights to succeed.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            # Get origin from headers
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode("utf-8")

            logger.debug(f"[ASGI] OPTIONS preflight: {scope['path']} - Origin: {origin}")

            # Check if origin is allowed (use same logic as config)
            allowed_origin = ""
            if origin in settings.CORS_ORIGINS:
                allowed_origin = origin
            elif "*" in settings.CORS_ORIGINS and settings.CORS_ORIGINS == ["*"]:
                # Only allow "*" if it's the ONLY origin (already validated in config)
                allowed_origin = "*"

            # Send CORS preflight response directly
            response_headers = [
                (b"access-control-allow-origin", allowed_origin.encode() if allowed_origin else b""),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                (b"access-control-allow-headers", b"authorization, content-type, accept, origin, x-requested-with"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"3600"),
                (b"content-length", b"0"),
            ]

            await send({
                "type": "http.response.start",
                "status": 200 if allowed_origin else 403,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": b"",
            })
            return

        # For non-OPTIONS requests, wrap send to inject CORS headers on every response
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode("utf-8")
        allowed_origin = ""
        if origin in settings.CORS_ORIGINS:
            allowed_origin = origin

        if not allowed_origin:
            await self.app(scope, receive, send)
            return

        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                existing = list(message.get("headers", []))
                # Only inject if not already present
                existing_keys = {k.lower() for k, _ in existing}
                if b"access-control-allow-origin" not in existing_keys:
                    existing += [
                        (b"access-control-allow-origin", allowed_origin.encode()),
                        (b"access-control-allow-credentials", b"true"),
                    ]
                message = {**message, "headers": existing}
            await send(message)

        await self.app(scope, receive, send_with_cors)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response pair with origin for CORS debugging."""

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get('origin', 'None')
        logger.info(f"Incoming: {request.method} {request.url.path} - Origin: {origin}")

        response = await call_next(request)

        logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
        return response
