from typing import List, Literal

from pydantic import BaseModel, Field


class RequirementResponse(BaseModel):
    id: int
    response: Literal["YES", "NO"]


class ScoreRequest(BaseModel):
    responses: List[RequirementResponse] = Field(..., min_length=1, max_length=5)


class RequirementOut(BaseModel):
    id: int
    requirement: str

    class Config:
        from_attributes = True


class ScoreResult(BaseModel):
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    score: float
    percentage: float
