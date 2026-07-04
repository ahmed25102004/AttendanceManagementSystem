
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.config import get_settings
from app.models.company_setting import CompanySetting

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

try:
    setting = db.query(CompanySetting).first()
    if setting:
        setting.face_match_threshold = 0.6
        db.commit()
        print("Updated face_match_threshold to 0.6")
    else:
        print("No setting found.")
finally:
    db.close()
