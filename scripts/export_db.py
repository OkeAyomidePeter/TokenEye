#!/usr/bin/env python3
"""
Database Export Script for TokenEye
Exports ONLY "complete data sets" (tokens that have completed all scheduled checks)
to Parquet format for AI training.

Definition of Complete:
A token must have entries in `token_history` for ALL 7 presets:
['1h', '3h', '6h', '1d', '1w', '1m', '3m']

Usage:
    python scripts/export_db.py                    # Export to local ./exports/
    python scripts/export_db.py --upload-s3        # Export and upload to S3
    python scripts/export_db.py --output /path/    # Custom output directory
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Expected check types for a "complete" dataset
REQUIRED_CHECK_TYPES = {"1h", "3h", "6h", "1d", "1w", "1m", "3m"}


def get_db_connection():
    """Create SQLAlchemy engine from DATABASE_URL."""
    from sqlalchemy import create_engine
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/tokenscout"
    )
    return create_engine(database_url)


def get_complete_token_addresses(engine) -> List[str]:
    """
    Find token addresses that have history entries for ALL required check types.
    """
    import pandas as pd
    
    logger.info("Identifying tokens with complete datasets...")
    
    # Query to count distinct check_types per token. 
    # We explicitly look for the 7 signatures. 
    # Note: This assumes 1w, 1m, 3m are actually populated in history as '1w', '1m', '3m' strings.
    query = """
    SELECT token_address
    FROM token_history
    WHERE check_type IN ('1h', '3h', '6h', '1d', '1w', '1m', '3m')
    GROUP BY token_address
    HAVING COUNT(DISTINCT check_type) = 7
    """
    
    try:
        df = pd.read_sql_query(query, engine)
        addresses = df['token_address'].tolist()
        logger.info(f"  → Found {len(addresses)} tokens with complete history (all 7 checks).")
        return addresses
    except Exception as e:
        logger.error(f"Error checking for complete tokens: {e}")
        return []


def export_complete_datasets(engine, output_dir: Path) -> List[Path]:
    """
    Export tokens_discovered and token_history ONLY for complete tokens.
    """
    import pandas as pd
    
    complete_addresses = get_complete_token_addresses(engine)
    
    if not complete_addresses:
        logger.warning("No complete datasets found. Skipping export.")
        return []
        
    exported_files = []
    
    # --- Export 1: tokens_discovered (filtered) ---
    logger.info("Exporting table: tokens_discovered (filtered)")
    # SQL IN clause requires single quotes around strings
    formatted_addresses = ", ".join(f"'{addr}'" for addr in complete_addresses)
    
    query_tokens = f"""
    SELECT * FROM tokens_discovered 
    WHERE address IN ({formatted_addresses})
    """
    try:
        df_tokens = pd.read_sql_query(query_tokens, engine)
        
        date_str = datetime.now().strftime("%Y%m%d")
        filename_tokens = f"tokens_discovered_complete_{date_str}.parquet"
        path_tokens = output_dir / filename_tokens
        
        df_tokens.to_parquet(path_tokens, index=False, compression="snappy")
        file_size_mb = path_tokens.stat().st_size / (1024 * 1024)
        logger.info(f"  → Exported {len(df_tokens)} rows to {path_tokens} ({file_size_mb:.2f} MB)")
        exported_files.append(path_tokens)
    except Exception as e:
        logger.error(f"Failed to export filtered tokens_discovered: {e}")

    # --- Export 2: token_history (filtered) ---
    logger.info("Exporting table: token_history (filtered)")
    query_history = f"""
    SELECT * FROM token_history 
    WHERE token_address IN ({formatted_addresses})
    """
    try:
        df_history = pd.read_sql_query(query_history, engine)
        
        filename_history = f"token_history_complete_{date_str}.parquet"
        path_history = output_dir / filename_history
        
        df_history.to_parquet(path_history, index=False, compression="snappy")
        file_size_mb = path_history.stat().st_size / (1024 * 1024)
        logger.info(f"  → Exported {len(df_history)} rows to {path_history} ({file_size_mb:.2f} MB)")
        exported_files.append(path_history)
    except Exception as e:
        logger.error(f"Failed to export filtered token_history: {e}")
        
    return exported_files


def upload_to_s3(file_path: Path, bucket_name: str, s3_prefix: str = "exports"):
    """Upload file to S3 bucket."""
    try:
        import boto3
        
        s3 = boto3.client("s3")
        s3_key = f"{s3_prefix}/{file_path.name}"
        
        logger.info(f"Uploading to s3://{bucket_name}/{s3_key}")
        # Check if bucket exists/accessible omitted for brevity, boto3 will raise if error
        s3.upload_file(str(file_path), bucket_name, s3_key)
        logger.info(f"  → Upload complete")
        
    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        raise
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Export COMPLETE TokenEye datasets to Parquet")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./exports",
        help="Output directory for Parquet files"
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload exports to S3 after generating"
    )
    parser.add_argument(
        "--s3-bucket",
        type=str,
        default=os.getenv("S3_BUCKET_NAME", "tokeneye-backups"),
        help="S3 bucket name for uploads"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("TokenEye 'Complete Dataset' Export")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Output: {output_dir.absolute()}")
    logger.info("=" * 50)
    
    try:
        # Check for pandas/pyarrow
        import pandas
        import pyarrow
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Run: pip install pandas pyarrow")
        sys.exit(1)
    
    # Connect to database
    try:
        engine = get_db_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
    
    # Export complete datasets
    exported_files = export_complete_datasets(engine, output_dir)
    
    # Upload to S3 if requested
    if args.upload_s3 and exported_files:
        logger.info("\nUploading to S3...")
        for file_path in exported_files:
            try:
                upload_to_s3(file_path, args.s3_bucket)
            except Exception as e:
                logger.error(f"Failed to upload {file_path.name}: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Export complete! {len(exported_files)} files generated.")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
