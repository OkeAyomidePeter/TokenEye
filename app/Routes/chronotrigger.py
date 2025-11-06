# app/Routes/chronotrigger.py

from fastapi import APIRouter, HTTPException
import logging
from app.TokenChronoData import process_due_schedules

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/start", summary="Run Token Chrono Pipeline for due schedules")
async def run_chrono_pipeline(limit: int = 50):
    try:
        result = await process_due_schedules(limit=limit)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Chrono pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chrono pipeline error: {str(e)}")
