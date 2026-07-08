"""HTTP delivery layer: middleware, route registration, and page serving.

This package owns everything that is specific to *how* the application is
exposed over HTTP. Business logic lives in ``services``; persistence in
``repositories``. Nothing in here should contain domain rules.
"""
