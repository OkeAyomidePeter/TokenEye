# app/main.py

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.Routes import trigger_router, chronotrigger_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles app startup and shutdown events in one place."""
    # You can perform startup tasks here (e.g., init DB client, warm caches).
    # Use logging instead of print in production; this is kept minimal for now.
    loop = asyncio.get_event_loop()
    # Simulate a small startup task
    await asyncio.sleep(0.1)

    try:
        yield
    finally:
        # Place shutdown/cleanup tasks here (e.g., flush queues, close clients)
        await asyncio.sleep(0.01)


app = FastAPI(
    title="TokenScout Sniper Bot",
    description="Early microcap token discovery system for Solana and Base.",
    version="0.1.0",
    lifespan=lifespan,
)

# Health / root endpoint
@app.get("/", summary="Service health")
async def root():
    return {"message": "TokenScout v2 is running 🚀"}

# Register routes using package-level exports
app.include_router(trigger_router, prefix="/sniper", tags=["Sniper"])
app.include_router(chronotrigger_router, prefix="/chronosniper", tags=["ChronoSniper"])
