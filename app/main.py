# app/main.py

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.Routes import trigger_router, chronotrigger_router
from app.Database import init_db
from app.Logging import setup_logging
import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles app startup and shutdown events in one place."""
    # You can perform startup tasks here (e.g., init DB client, warm caches).
    # Use logging instead of print in production; this is kept minimal for now.
    loop = asyncio.get_event_loop()
    # Initialize logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Service starting up")
    
    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized (or already present)")
    except Exception as e:
        # Log error but don't crash the app - tables might already exist
        logger.warning(f"Database initialization warning: {e}")
    
    # Simulate a small startup task
    await asyncio.sleep(0.1)

    try:
        yield
    finally:
        # Place shutdown/cleanup tasks here (e.g., flush queues, close clients)
        await asyncio.sleep(0.01)
        logger.info("Service shutting down")


app = FastAPI(
    title="TokenScout Sniper Bot",
    description="Early microcap token discovery system for Solana",
    version="0.2.0",
    lifespan=lifespan,
)

# Health / root endpoint
@app.get("/", summary="Service health")
async def root():
    return {"message": "TokenScout v0.2.0 is running 🚀"}

# Register routes using package-level exports
app.include_router(trigger_router, prefix="/sniper", tags=["Sniper"])
app.include_router(chronotrigger_router, prefix="/chronosniper", tags=["ChronoSniper"])
