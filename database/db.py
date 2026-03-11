from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from .models import Base

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Creates database tables from models."""
    Base.metadata.create_all(bind=engine)

def get_session():
    """Provides a database session."""
    return SessionLocal()
