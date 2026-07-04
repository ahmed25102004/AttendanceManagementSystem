
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

with engine.connect() as conn:
    # Make employee_code nullable
    conn.execute(text("ALTER TABLE employees ALTER COLUMN employee_code DROP NOT NULL"))
    conn.commit()
    print("Database schema updated! employee_code is now nullable.")
