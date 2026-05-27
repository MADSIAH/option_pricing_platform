"""Route modules for Spec C API."""

from .ai import router as ai_router
from .health import router as health_router
from .market import router as market_router
from .pricing import router as pricing_router
from .surface import router as surface_router

__all__ = [
    "ai_router",
    "health_router",
    "market_router",
    "pricing_router",
    "surface_router",
]
