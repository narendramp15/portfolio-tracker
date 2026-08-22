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
        # DEBUG, not INFO: at INFO this logged the full path of every request —
        # including any credential that had been passed as a query parameter —
        # into the default production log stream.
        origin = request.headers.get('origin', 'None')
        logger.debug("Incoming: %s %s - Origin: %s", request.method, request.url.path, origin)

        response = await call_next(request)

        logger.debug(
            "Response: %s %s - Status: %s",
            request.method, request.url.path, response.status_code,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach the standard hardening headers to every response.

    ``Referrer-Policy`` is the load-bearing one here: it stops any credential
    that still reaches a URL from leaking to third parties via the Referer
    header. The CSP is the main remaining mitigation against an XSS payload
    reading the access token out of localStorage.
    """

    # Kept permissive enough for the SPA (Vite emits inline style attributes)
    # and the Razorpay checkout, which loads its own script and iframes.
    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://checkout.razorpay.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.razorpay.com https://lumberjack.razorpay.com; "
        "frame-src https://api.razorpay.com https://checkout.razorpay.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    )

    _STATIC_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(self)",
        "Cross-Origin-Opener-Policy": "same-origin",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        for header, value in self._STATIC_HEADERS.items():
            response.headers.setdefault(header, value)

        # /docs and /redoc pull Swagger assets from a CDN; a strict CSP would
        # blank them out. Everything else gets the policy.
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers.setdefault("Content-Security-Policy", self._CSP)

        # HSTS only makes sense once TLS terminates in front of us, and sending
        # it over plain HTTP in local dev pins localhost to https in the browser.
        if settings.IS_PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response
