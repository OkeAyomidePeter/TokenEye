#!/usr/bin/env python3
"""
complete_export.py

1. Fills missing snapshots by processing due schedules.
2. Identifies tokens with all 7 snapshots (1h, 3h, 6h, 1d, 1w, 1m, 3m).
3. Exports these "complete" tokens to Parquet format.

Run this via cron once a day or every few hours.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from sqlalchemy import create_engine

from app.TokenChronoData.processor import process_due_schedules
from app.Database.repository import get_due_schedules, SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_db_engine():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/tokenscout"
    )
    return create_engine(database_url)

async def fill_all_due_snapshots(limit_per_batch=100):
    """Keep processing due schedules until none are left."""
    logger.info("Filling missing snapshots...")
    while True:
        # Check how many are due
        due = get_due_schedules(limit=limit_per_batch)
        if not due:
            logger.info("No more due snapshots to fill.")
            break
        
        logger.info(f"Processing batch of {len(due)} snapshots...")
        result = await process_due_schedules(limit=len(due))
        logger.info(f"Batch processed: {result.get('processed', 0)} successes.")
        
        # Avoid infinite loop if things are failing
        if result.get('processed', 0) == 0:
            logger.warning("No snapshots were processed in this batch, stopping to avoid loop.")
            break

def get_complete_token_addresses(engine) -> List[str]:
    query = """
    SELECT token_address
    FROM token_history
    WHERE check_type IN ('1h', '3h', '6h', '1d', '1w', '1m', '3m')
    GROUP BY token_address
    HAVING COUNT(DISTINCT check_type) = 7
    """
    try:
        df = pd.read_sql_query(query, engine)
        return df['token_address'].tolist()
    except Exception as e:
        logger.error(f"Error finding complete tokens: {e}")
        return []

def export_to_parquet(engine, output_dir: Path):
    addresses = get_complete_token_addresses(engine)
    if not addresses:
        logger.info("No tokens found with complete 7-snapshot history.")
        return
    
    logger.info(f"Found {len(addresses)} complete tokens for export.")
    formatted_addresses = ", ".join(f"'{addr}'" for addr in addresses)
    date_str = datetime.now().strftime("%Y%m%d")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export discovered tokens
    df_tokens = pd.read_sql_query(f"SELECT * FROM tokens_discovered WHERE address IN ({formatted_addresses})", engine)
    token_path = output_dir / f"tokens_discovered_complete_{date_str}.parquet"
    df_tokens.to_parquet(token_path, index=False)
    
    # Export history
    df_history = pd.read_sql_query(f"SELECT * FROM token_history WHERE token_address IN ({formatted_addresses})", engine)
    history_path = output_dir / f"token_history_complete_{date_str}.parquet"
    df_history.to_parquet(history_path, index=False)
    
    logger.info(f"Exported to {output_dir}")

async def run():
    engine = get_db_engine()
    
    # 1. Fill missing snapshots
    await fill_all_due_snapshots()
    
    # 2. Export
    output_dir = Path(__file__).parent.parent / "exports"
    export_to_parquet(engine, output_dir)

if __name__ == "__main__":
    asyncio.run(run())
