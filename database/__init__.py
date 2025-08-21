"""
Database connection and session management.
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from .models import Base
from config import Settings, get_settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize database connection."""
        # Create engine with appropriate settings
        connect_args = {}
        
        if self.settings.database.url.startswith("sqlite"):
            # SQLite-specific settings
            connect_args = {
                "check_same_thread": False,
            }
            # Use static pool for SQLite to maintain connections
            self.engine = create_engine(
                self.settings.database.url,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=self.settings.database.echo,
            )
        else:
            # PostgreSQL/other database settings
            self.engine = create_engine(
                self.settings.database.url,
                pool_size=self.settings.database.pool_size,
                pool_pre_ping=True,
                echo=self.settings.database.echo,
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database initialized: {self.settings.database.url}")
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database instance
_database: Optional[Database] = None


def get_database(settings: Optional[Settings] = None) -> Database:
    """Get database instance."""
    global _database
    if _database is None:
        _database = Database(settings)
    return _database


def get_db_session() -> Generator[Session, None, None]:
    """Dependency function for FastAPI to get database session."""
    db = get_database()
    with db.session_scope() as session:
        yield session


def init_database(settings: Optional[Settings] = None, create_tables: bool = True) -> Database:
    """Initialize database and optionally create tables."""
    db = get_database(settings)
    if create_tables:
        db.create_tables()
    return db


# Backwards compatibility alias
DatabaseManager = Database