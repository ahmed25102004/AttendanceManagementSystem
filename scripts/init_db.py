from app.core.bootstrap import bootstrap_defaults
from app.core.database import Base, engine


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    bootstrap_defaults()
    print("Database tables created and default records initialized.")
