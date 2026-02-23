from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called once during application startup.
    """
    try:
        # Import models to ensure they're registered with Base
        from app.Database.models import TokenData, TokenHistory, TokenSchedule
        
        # Create all tables
        print(">>> SQLALCHEMY: Running create_all...")
        Base.metadata.create_all(bind=engine)
        print(">>> SQLALCHEMY: create_all SUCCESS.")
        logger.info("Database tables initialized successfully")
    except Exception as e:
        print(f">>> SQLALCHEMY ERROR: {e}")
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise
