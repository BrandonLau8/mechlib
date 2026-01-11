"""
API routers for MechLib.

This package contains all FastAPI router modules:
- auth: Authentication endpoints (Google OAuth, JWT)
- image: Image management endpoints (upload, process, search, update, delete)
"""

from . import auth, image

__all__ = ['auth', 'image']
