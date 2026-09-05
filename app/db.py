from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine_options: dict = {}
if settings.database_url.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema_compatibility() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    if "products" not in inspect(engine).get_table_names():
        return
    columns = {column["name"] for column in inspect(engine).get_columns("products")}
    if "image_url" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
