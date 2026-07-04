from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Employee Attendance Management System"
    app_env: str = "development"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/attendance_db"
    admin_username: str = "admin"
    admin_password: str = "Admin@123"
    company_name: str = "verdebeautyclinic"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
