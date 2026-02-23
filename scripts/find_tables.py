#!/usr/bin/env python3
"""
find_tables.py
Searches all accessible databases and schemas for TokenEye tables.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def find():
    # Try the URL from .env first
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        print(f"Testing DATABASE_URL from .env...")
        try_url(env_url, "Environment URL")
    
    # We'll also try common variations based on your setup
    # Password extracted from your .env
    pwd = "Ay0_m1d3p3t3r"
    users = ["ayomide", "postgres"]
    db_names = ["tokenscout", "postgres"]
    
    for user in users:
        for db_name in db_names:
            url = f"postgresql+psycopg2://{user}:{pwd}@localhost:5432/{db_name}"
            try_url(url, f"User: {user}, DB: {db_name}")

def try_url(url, label):
    print(f"\nChecking {label}...")
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            query = text("""
                SELECT schemaname, tablename 
                FROM pg_catalog.pg_tables 
                WHERE tablename IN ('tokens_discovered', 'token_history', 'token_schedule');
            """)
            results = conn.execute(query).fetchall()
            if results:
                for schema, table in results:
                    print(f"  [FOUND] Schema: {schema}, Table: {table}")
            else:
                print("  [NOT FOUND] No TokenEye tables here.")
    except Exception as e:
        print(f"  [ERROR] Connection failed: {str(e).split(' (Background')[0]}")

if __name__ == "__main__":
    find()
