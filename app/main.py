from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import RFP
from .schemas import RequirementOut, ScoreRequest, ScoreResult

app = FastAPI(
    title="RFP Validation API",
    description="Validate Cisco partner responses against RFP requirements.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    seed_database()


def seed_database():
    db = SessionLocal()
    try:
        if db.query(RFP).count() == 0:
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
    if db.query(RFP).count() < 5:
        raise HTTPException(
            status_code=500,
            detail="At least 5 RFP requirements are required.",
        )

    return db.query(RFP).order_by(func.random()).limit(5).all()


@app.post("/rfp/score", response_model=ScoreResult)
def calculate_score(payload: ScoreRequest, db: Session = Depends(get_db)):
    if len(payload.responses) != 5:
        raise HTTPException(
            status_code=400,
            detail="Exactly 5 requirement responses are required.",
        )

    ids = [item.id for item in payload.responses]

    if len(set(ids)) != 5:
        raise HTTPException(
            status_code=400,
            detail="Duplicate requirement IDs are not allowed.",
        )

    records = db.query(RFP).filter(RFP.id.in_(ids)).all()

    if len(records) != 5:
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

    incorrect_answers = 5 - correct_answers
    percentage = (correct_answers / 5) * 100

    return ScoreResult(
        total_questions=5,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        score=correct_answers * 20,
        percentage=percentage,
    )
