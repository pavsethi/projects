"""Seed the database with a demo org hierarchy, tasks, and comments.

Run with:  python -m app.seed   (from the backend/ directory)

The tables must already exist — run ``alembic upgrade head`` first. This clears
the existing rows and re-inserts a consistent demo dataset, so it is destructive
to data by design. Every account uses the password ``password123``.
"""

from datetime import date, timedelta

from .database import SessionLocal
from .models import Comment, Task, TaskStatus, User
from .security import hash_password

DEMO_PASSWORD = "password123"


def run() -> None:
    db = SessionLocal()
    try:
        # Clear existing rows (child tables first to respect foreign keys).
        db.query(Comment).delete()
        db.query(Task).delete()
        db.query(User).delete()
        db.commit()

        # Org chart:  alice (admin) -> bob, carol ;  bob -> dave
        alice = User(
            username="alice",
            email="alice@example.com",
            first_name="Alice",
            last_name="Anderson",
            hashed_password=hash_password(DEMO_PASSWORD),
            manager_id=None,
        )
        db.add(alice)
        db.commit()
        db.refresh(alice)

        bob = User(
            username="bob",
            email="bob@example.com",
            first_name="Bob",
            last_name="Brown",
            hashed_password=hash_password(DEMO_PASSWORD),
            manager_id=alice.id,
        )
        carol = User(
            username="carol",
            email="carol@example.com",
            first_name="Carol",
            last_name="Clark",
            hashed_password=hash_password(DEMO_PASSWORD),
            manager_id=alice.id,
        )
        db.add_all([bob, carol])
        db.commit()
        db.refresh(bob)

        dave = User(
            username="dave",
            email="dave@example.com",
            first_name="Dave",
            last_name="Davis",
            hashed_password=hash_password(DEMO_PASSWORD),
            manager_id=bob.id,
        )
        db.add(dave)
        db.commit()
        db.refresh(carol)
        db.refresh(dave)

        today = date.today()
        tasks = [
            Task(
                title="Finalize Q3 roadmap",
                description="Draft and circulate the Q3 product roadmap for review.",
                deadline=today + timedelta(days=5),
                status=TaskStatus.pending,
                assigned_user_id=bob.id,
                created_by=alice.id,
            ),
            Task(
                title="Fix login redirect bug",
                description="Users are not redirected to the dashboard after login.",
                deadline=today + timedelta(days=2),
                status=TaskStatus.acknowledged,
                assigned_user_id=dave.id,
                created_by=bob.id,
            ),
            Task(
                title="Prepare onboarding deck",
                description="Slides for the new-hire onboarding session next week.",
                deadline=today + timedelta(days=9),
                status=TaskStatus.completed,
                assigned_user_id=carol.id,
                created_by=alice.id,
            ),
            Task(
                title="Migrate CI to GitHub Actions",
                description="Move the build pipeline off the legacy CI server.",
                deadline=today - timedelta(days=1),
                status=TaskStatus.failed,
                assigned_user_id=dave.id,
                created_by=dave.id,
            ),
        ]
        db.add_all(tasks)
        db.commit()
        for t in tasks:
            db.refresh(t)

        db.add_all(
            [
                Comment(
                    task_id=tasks[0].id,
                    content="Let's sync on priorities before circulating.",
                    created_by=alice.id,
                ),
                Comment(
                    task_id=tasks[1].id,
                    content="Reproduced it — looks like a missing redirect header.",
                    created_by=dave.id,
                ),
            ]
        )
        db.commit()

        print("Seeded database. Log in with any of: alice, bob, carol, dave")
        print(f"Password for all demo accounts: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
