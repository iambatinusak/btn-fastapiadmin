"""fastapiadmin — a beautiful, minimal admin panel for FastAPI + SQLAlchemy."""

from .admin import AdminSite, ModelAdmin

__all__ = ["AdminSite", "ModelAdmin"]
__version__ = "0.1.0"
