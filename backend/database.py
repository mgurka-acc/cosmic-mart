from sqlmodel import create_engine, Session, SQLModel
from backend.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
