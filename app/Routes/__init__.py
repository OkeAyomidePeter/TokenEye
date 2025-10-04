# app/Routes/__init__.py
from .trigger import router as trigger_router
from .chronotrigger import router as chronotrigger_router

__all__ = ["trigger_router", "chronotrigger_router"]