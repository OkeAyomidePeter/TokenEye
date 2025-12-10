#!/bin/bash
# ===========================================
# Sync TokenEye backups from S3 to local
# ===========================================
# Usage: ./scripts/sync_from_s3.sh
# 
# Requires: aws cli configured with credentials
# Install: pip install awscli && aws configure

set -e

# Configuration
S3_BUCKET="${S3_BUCKET_NAME:-tokeneye-backups}"
LOCAL_DIR="${LOCAL_DATA_DIR:-$HOME/tokeneye-data}"
S3_PREFIX="exports"

echo "============================================"
echo "TokenEye S3 Backup Sync"
echo "============================================"
echo "S3 Bucket: s3://$S3_BUCKET/$S3_PREFIX/"
echo "Local Dir: $LOCAL_DIR"
echo "============================================"

# Create local directory if needed
mkdir -p "$LOCAL_DIR"

# Sync from S3
echo "Syncing from S3..."
aws s3 sync "s3://$S3_BUCKET/$S3_PREFIX/" "$LOCAL_DIR/" --exclude "*" --include "*.parquet"

echo ""
echo "============================================"
echo "Sync complete!"
echo "Files downloaded to: $LOCAL_DIR"
ls -lh "$LOCAL_DIR"/*.parquet 2>/dev/null || echo "No parquet files found yet."
echo "============================================"
