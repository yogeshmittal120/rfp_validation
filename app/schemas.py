from typing import List, Literal

from pydantic import BaseModel, Field


class RequirementResponse(BaseModel):
    id: int
    response: Literal["YES", "NO"]


class ScoreRequest(BaseModel):
    responses: List[RequirementResponse] = Field(..., min_length=10, max_length=10)


class RequirementOut(BaseModel):
    id: int
    rfp_title: str
    requirement: str

    class Config:
        from_attributes = True


class TrainingRecommendation(BaseModel):
    series_name: str
    description: str
    series_url: str = ""
    stage: str = ""
    architecture: str = ""
    program_track: str = ""
    track: str = ""
    role: str = ""
    language: str = ""
    learning_plan_type: str = ""
    business_entity: str = ""
    matched_requirement: str
    relevance_score: float


class ScoreResult(BaseModel):
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    score: float
    percentage: float
    training_recommendation_status: str = "not_needed"
    training_recommendations: List[TrainingRecommendation] = Field(default_factory=list)
