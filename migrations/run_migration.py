import os
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import settings

def run_migration():
    print("Running migration to add doctors department columns...")
    
    # Read the SQL file
    sql_path = os.path.join(os.path.dirname(__file__), "add_doctors_department_columns.sql")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Execute the SQL
    with SessionLocal() as db:
        try:
            db.execute(text(sql))
            db.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error running migration: {e}")
            db.rollback()
            raise

if __name__ == "__main__":
    run_migration()
