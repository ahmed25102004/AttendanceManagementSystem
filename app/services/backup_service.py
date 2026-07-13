import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import Base

class BackupService:
    def __init__(self):
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def create_backup(self, db: Session) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Collect all data using the db connection
        from sqlalchemy import inspect
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        backup_data = {}
        for table in tables:
            # Use raw SQL to avoid model dependencies
            result = db.execute(text(f"SELECT * FROM {table}"))
            rows = result.mappings().all()
            backup_data[table] = [dict(row) for row in rows]
            
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
        return backup_path
        
    def clean_old_backups(self, retention_days: int):
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.backup_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_mtime < cutoff_date:
                    os.remove(filepath)
        
    def restore_backup(self, db: Session, file_content: bytes):
        import tempfile
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp:
            temp.write(file_content)
            
        backup_path = temp.name
        
        # Load backup data
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
            
        # Get tables to restore in order
        tables = list(backup_data.keys())
        
        # Restore data
        for table in tables:
            rows = backup_data.get(table, [])
            if not rows:
                continue
                
            # Get column names
            if rows:
                columns = list(rows[0].keys())
                
                # Delete existing data in table
                db.execute(text(f"DELETE FROM {table}"))
                
                # Insert new data
                for row in rows:
                    # Handle special data types
                    cleaned_row = {}
                    for key, value in row.items():
                        if isinstance(value, str) and value.startswith("0001-01-01"):
                            cleaned_row[key] = None
                        else:
                            cleaned_row[key] = value
                            
                    placeholders = ", ".join([f":{col}" for col in columns])
                    db.execute(
                        text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"),
                        cleaned_row
                    )
                    
        db.commit()
        
        # Cleanup temp file
        try:
            os.remove(backup_path)
        except OSError:
            pass
            
    def list_backups(self) -> list[dict]:
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    "name": filename,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size": stat.st_size
                })
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)
        
    def delete_backup(self, filename: str):
        filepath = os.path.join(self.backup_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
