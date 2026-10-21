import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import RFP
from .schemas import RequirementOut, ScoreRequest, ScoreResult
from .services.training_recommender import recommend_training

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RFP Validation API",
    description="Validate Cisco partner responses against RFP requirements and recommend relevant training.",
    version="1.4.0",
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
    """Seed three sample RFPs, adding only titles that are not already present."""
    sample_rfps = {
        "Cisco Partner RFP": [
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
        ],
        "Network Security RFP": [
            ("The solution must provide a network firewall.", "YES"),
            ("The solution must detect and prevent network intrusions.", "YES"),
            ("The solution must support VPN connectivity.", "YES"),
            ("The solution must provide centralized security logging.", "YES"),
            ("The solution must support network traffic encryption.", "YES"),
            ("The solution must include a built-in email marketing tool.", "NO"),
            ("The solution must support security policy management.", "YES"),
            ("The solution must provide real-time threat alerts.", "YES"),
            ("The solution must support integration with SIEM platforms.", "YES"),
            ("The solution must require all administration to be done manually.", "NO"),
        ],
        "Cloud Infrastructure RFP": [
            ("The solution must support deployment on a public cloud.", "YES"),
            ("The solution must support automated resource scaling.", "YES"),
            ("The solution must provide infrastructure monitoring.", "YES"),
            ("The solution must support automated backups.", "YES"),
            ("The solution must provide role-based access control.", "YES"),
            ("The solution must require physical servers for every deployment.", "NO"),
            ("The solution must support disaster recovery.", "YES"),
            ("The solution must provide usage and cost reporting.", "YES"),
            ("The solution must support encrypted data storage.", "YES"),
            ("The solution must disable audit logging by default.", "NO"),
        ],
    }

    db = SessionLocal()
    try:
        existing_titles = {
            title
            for (title,) in db.query(RFP.rfp_title).distinct().all()
            if title is not None
        }

        for title, requirements in sample_rfps.items():
            if title in existing_titles:
                continue

            db.add_all(
                [
                    RFP(
                        rfp_title=title,
                        requirement=requirement,
                        cisco_partner_response=response,
                    )
                    for requirement, response in requirements
                ]
            )

        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rfp/titles", response_model=list[str])
def get_rfp_titles(db: Session = Depends(get_db)):
    """Return distinct RFP titles for the frontend selection screen."""
    titles = (
        db.query(RFP.rfp_title)
        .filter(RFP.rfp_title.isnot(None))
        .distinct()
        .order_by(RFP.rfp_title)
        .all()
    )
    return [title[0] for title in titles]


@app.get("/rfp/{rfp_title}/requirements", response_model=list[RequirementOut])
def get_random_requirements_for_title(
    rfp_title: str,
    db: Session = Depends(get_db),
):
    """Return 10 random requirements belonging only to the selected RFP title."""
    query = db.query(RFP).filter(RFP.rfp_title == rfp_title)
    requirement_count = query.count()

    if requirement_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"RFP title not found: {rfp_title}",
        )

    if requirement_count < 10:
        raise HTTPException(
            status_code=400,
            detail=(
                f"RFP '{rfp_title}' has only {requirement_count} requirements; "
                "at least 10 are required."
            ),
        )

    return query.order_by(func.random()).limit(10).all()


# Backward-compatible endpoint: returns 10 random requirements from all RFPs.
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
    failed_requirements = []

    for item in payload.responses:
        record = record_by_id[item.id]
        expected = record.cisco_partner_response.upper()
        if item.response.upper() == expected:
            correct_answers += 1
        else:
            failed_requirements.append(record.requirement)

    incorrect_answers = 10 - correct_answers
    percentage = (correct_answers / 10) * 100
    recommendation_status = "not_needed"
    recommendations = []

    if percentage < 70:
        try:
            recommendations = recommend_training(failed_requirements)
            recommendation_status = (
                "recommendations_available" if recommendations else "no_relevant_training"
            )
        except Exception:
            # Scoring remains available even if the local training index is not ready.
            logger.exception("Training recommendation lookup failed")
            recommendation_status = "index_not_ready"

    return ScoreResult(
        total_questions=10,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        score=correct_answers * 10,
        percentage=percentage,
        training_recommendation_status=recommendation_status,
        training_recommendations=recommendations,
    )
