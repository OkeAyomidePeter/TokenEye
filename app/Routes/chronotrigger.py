# app/Routes/chronotrigger.py

from fastapi import APIRouter
from app.DataStream import tokenstream

router = APIRouter()

@router.get("/start", summary="Run Chrono Sniper Bot (basic Dexscreener fetch)")
async def run_chrono_sniper():
    """
    Temporary endpoint: Fetch top tokens (placeholder for chrono logic)
    """
    data = await tokenstream.fetch_top_tokens()
    return {"status": "success", "count": data.count if data else 0, "data": data}
