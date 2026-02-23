#!/usr/bin/env python3
"""
scripts/complete_export.py

Ensures that all tokens have a full set of snapshots (1h,3h,6h,1d,1w,1m,3m) and then exports the
complete dataset to Parquet files.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

# Setup path relative to script location
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import pandas as pd
from sqlalchemy import create_engine

# Import app components
from app.TokenChronoData.processor import process_due_schedules
from app.Database.repository import get_due_schedules

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_db_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")
    return create_engine(database_url)

async def fill_all_due_snapshots(limit_per_batch=100):
    logger.info("Checking for due snapshots to fill...")
    while True:
        due = get_due_schedules(limit=limit_per_batch)
        if not due:
            logger.info("All scheduled snapshots are up-to-date.")
            break
        
        logger.info(f"Processing batch of {len(due)} snapshots...")
        result = await process_due_schedules(limit=len(due))
        if result.get('processed', 0) == 0:
            logger.warning("No progress made in last batch, stopping.")
            break

def export_to_parquet(engine, output_dir: Path):
    query = """
    SELECT token_address
    FROM token_history
    WHERE check_type IN ('1h', '3h', '6h', '1d', '1w', '1m', '3m')
    GROUP BY token_address
    HAVING COUNT(DISTINCT check_type) = 7
    """
    addresses = pd.read_sql_query(query, engine)['token_address'].tolist()
    
    if not addresses:
        logger.info("No tokens with complete 7-snapshot history found yet.")
        return
    
    logger.info(f"Exporting {len(addresses)} complete token datasets...")
    addr_list = ", ".join(f"'{a}'" for a in addresses)
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export discovered metadata
    df_tokens = pd.read_sql_query(f"SELECT * FROM tokens_discovered WHERE address IN ({addr_list})", engine)
    df_tokens.to_parquet(output_dir / f"tokens_discovered_{date_str}.parquet", index=False)
    
    # Export history time-series
    df_history = pd.read_sql_query(f"SELECT * FROM token_history WHERE token_address IN ({addr_list})", engine)
    df_history.to_parquet(output_dir / f"token_history_{date_str}.parquet", index=False)
    
    logger.info(f"Files saved to {output_dir}")

async def run_pipeline():
    try:
        engine = get_db_engine()
        # 1. Backfill any due snapshots
        await fill_all_due_snapshots()
        # 2. Export only the 100% complete ones
        export_to_parquet(engine, Path("./exports"))
    except Exception as e:
        logger.error(f"Export pipeline failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
