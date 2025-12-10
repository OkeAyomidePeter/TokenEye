#!/usr/bin/env python3
"""
Database Export Script for TokenEye
Exports tokens_discovered and token_history tables to Parquet format.
Designed to run weekly via cron or manually.

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

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Create SQLAlchemy engine from DATABASE_URL."""
    from sqlalchemy import create_engine
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/tokenscout"
    )
    return create_engine(database_url)


def export_table_to_parquet(engine, table_name: str, output_dir: Path) -> Path:
    """Export a database table to Parquet format."""
    import pandas as pd
    
    logger.info(f"Exporting table: {table_name}")
    
    # Read table into DataFrame
    df = pd.read_sql_table(table_name, engine)
    
    # Generate filename with date
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{table_name}_{date_str}.parquet"
    output_path = output_dir / filename
    
    # Export to Parquet
    df.to_parquet(output_path, index=False, compression="snappy")
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"  → Exported {len(df)} rows to {output_path} ({file_size_mb:.2f} MB)")
    
    return output_path


def upload_to_s3(file_path: Path, bucket_name: str, s3_prefix: str = "exports"):
    """Upload file to S3 bucket."""
    try:
        import boto3
        
        s3 = boto3.client("s3")
        s3_key = f"{s3_prefix}/{file_path.name}"
        
        logger.info(f"Uploading to s3://{bucket_name}/{s3_key}")
        s3.upload_file(str(file_path), bucket_name, s3_key)
        logger.info(f"  → Upload complete")
        
    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        raise
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Export TokenEye database to Parquet")
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
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["tokens_discovered", "token_history"],
        help="Tables to export (default: tokens_discovered, token_history)"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("TokenEye Database Export")
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
    engine = get_db_connection()
    
    # Export each table
    exported_files = []
    for table_name in args.tables:
        try:
            output_path = export_table_to_parquet(engine, table_name, output_dir)
            exported_files.append(output_path)
        except Exception as e:
            logger.error(f"Failed to export {table_name}: {e}")
    
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
