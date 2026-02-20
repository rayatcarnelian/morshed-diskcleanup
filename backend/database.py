from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./disk_cleanup.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    filepath = Column(String, index=True)
    filename = Column(String)
    filesize_mb = Column(Float)
    filetype = Column(String)
    last_modified = Column(String)
    category = Column(String)
    is_safe_to_delete = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)
