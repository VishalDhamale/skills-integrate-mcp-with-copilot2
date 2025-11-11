from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional, List
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=False)


class Activity(SQLModel, table=True):
    name: str = Field(primary_key=True)
    description: Optional[str] = None
    schedule: Optional[str] = None
    max_participants: int = 0


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    activity_name: str = Field(foreign_key="activity.name")


def create_db_and_tables() -> None:
    """Create database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def seed_initial_data(initial_activities: dict) -> None:
    """Seed DB with the provided activities dict if DB is empty.

    This keeps the existing in-repo sample data while moving persistence to SQLite.
    """
    with Session(engine) as session:
        first = session.exec(select(Activity)).first()
        if first is not None:
            return

        for name, data in initial_activities.items():
            activity = Activity(
                name=name,
                description=data.get("description"),
                schedule=data.get("schedule"),
                max_participants=data.get("max_participants", 0),
            )
            session.add(activity)
            session.commit()

            for email in data.get("participants", []):
                participant = Participant(email=email, activity_name=name)
                session.add(participant)
            session.commit()


def get_all_activities() -> dict:
    """Return activities as a dict compatible with the previous API shape."""
    result = {}
    with Session(engine) as session:
        activities = session.exec(select(Activity)).all()
        for act in activities:
            participants = [p.email for p in session.exec(select(Participant).where(Participant.activity_name == act.name)).all()]
            result[act.name] = {
                "description": act.description,
                "schedule": act.schedule,
                "max_participants": act.max_participants,
                "participants": participants,
            }
    return result


def signup(activity_name: str, email: str) -> None:
    with Session(engine) as session:
        act = session.get(Activity, activity_name)
        if not act:
            raise KeyError("Activity not found")

        # already signed up?
        existing = session.exec(select(Participant).where(Participant.activity_name == activity_name, Participant.email == email)).first()
        if existing:
            raise ValueError("already_signed_up")

        participants = session.exec(select(Participant).where(Participant.activity_name == activity_name)).all()
        if len(participants) >= act.max_participants:
            raise OverflowError("activity_full")

        participant = Participant(email=email, activity_name=activity_name)
        session.add(participant)
        session.commit()


def unregister(activity_name: str, email: str) -> None:
    with Session(engine) as session:
        existing = session.exec(select(Participant).where(Participant.activity_name == activity_name, Participant.email == email)).first()
        if not existing:
            raise KeyError("not_signed_up")
        session.delete(existing)
        session.commit()
