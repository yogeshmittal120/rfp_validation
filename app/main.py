from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import RFP
from .schemas import RequirementOut, ScoreRequest, ScoreResult

app = FastAPI(
    title="RFP Validation API",
    description="Validate Cisco partner responses against RFP requirements.",
    version="1.1.0",
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    ensure_database_schema()
    seed_database()


def ensure_database_schema():
    """Add rfp_title to an existing SQLite database without losing its data."""
    inspector = inspect(engine)
    if "rfp" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("rfp")}
        if "rfp_title" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE rfp "
                        "ADD COLUMN rfp_title VARCHAR NOT NULL "
                        "DEFAULT 'Cisco Partner RFP'"
                    )
                )


def seed_database():
    db = SessionLocal()
    try:
        if db.query(RFP).count() == 0:
            rfp_title = "Cisco Partner RFP"
            sample_data = [
                ("The solution must support 24x7 technical support.", "YES"),
                ("The solution must provide role-based access control.", "YES"),
                ("The solution must support on-premises deployment.", "NO"),
                ("The solution must provide REST APIs.", "YES"),
                ("The solution must support IPv6.", "YES"),
                ("The solution must include automated backup.", "NO"),
                ("The solution must support multi-factor authentication.", "YES"),
                ("The solution must provide a mobile application.", "NO"),
                ("The solution must support high availability.", "YES"),
                ("The solution must provide real-time monitoring.", "YES"),
            ]

            db.add_all(
                [
                    RFP(
                        rfp_title=rfp_title,
                        requirement=requirement,
                        cisco_partner_response=response,
                    )
                    for requirement, response in sample_data
                ]
            )
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rfp/requirements", response_model=list[RequirementOut])
def get_random_requirements(db: Session = Depends(get_db)):
    if db.query(RFP).count() < 10:
        raise HTTPException(
            status_code=500,
            detail="At least 10 RFP requirements are required.",
        )

    return db.query(RFP).order_by(func.random()).limit(10).all()


@app.post("/rfp/score", response_model=ScoreResult)
def calculate_score(payload: ScoreRequest, db: Session = Depends(get_db)):
    if len(payload.responses) != 10:
        raise HTTPException(
            status_code=400,
            detail="Exactly 10 requirement responses are required.",
        )

    ids = [item.id for item in payload.responses]

    if len(set(ids)) != 10:
        raise HTTPException(
            status_code=400,
            detail="Duplicate requirement IDs are not allowed.",
        )

    records = db.query(RFP).filter(RFP.id.in_(ids)).all()

    if len(records) != 10:
        found_ids = {record.id for record in records}
        missing_ids = sorted(set(ids) - found_ids)
        raise HTTPException(
            status_code=404,
            detail=f"Requirement IDs not found: {missing_ids}",
        )

    record_by_id = {record.id: record for record in records}
    correct_answers = 0

    for item in payload.responses:
        expected = record_by_id[item.id].cisco_partner_response.upper()
        if item.response.upper() == expected:
            correct_answers += 1

    incorrect_answers = 10 - correct_answers
    percentage = (correct_answers / 10) * 100

    return ScoreResult(
        total_questions=10,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        score=correct_answers * 10,
        percentage=percentage,
    )
