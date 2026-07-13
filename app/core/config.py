from functools import lru_cache
import os
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict


# First load .env.local (if available) - HIGHEST PRIORITY
if os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)

# Then load .env (LOWER PRIORITY, only if var not set)
if os.path.exists(".env"):
    load_dotenv(".env", override=False)


class Settings(BaseSettings):
    app_name: str = "Employee Attendance Management System"
    app_env: str = "development"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/attendance_db"
    admin_username: str = "admin"
    admin_password: str = "Admin@123"
    company_name: str = "Demo Company"
    device_ip: str = "192.168.1.201"
    device_port: int = 4370
    device_password: str = ""
    device_timeout: int = 10

    # We'll use the env vars we loaded manually
    model_config = SettingsConfigDict(case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
