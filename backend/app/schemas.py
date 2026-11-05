from typing import List, Literal
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str = ""
    role: Literal["student", "hr"]
    hr_code: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class JobIn(BaseModel):
    title: str
    description: str = ""
    required_skills: str
    location: str = ""
    work_mode: Literal["onsite", "hybrid", "remote"] = "onsite"
    stipend: str = ""
    duration_months: int = Field(3, ge=1, le=24)
    threshold: int = Field(60, ge=0, le=100)


class SlotsIn(BaseModel):
    slots: List[str]  # "YYYY-MM-DDTHH:MM" in IST


class DecisionIn(BaseModel):
    decision: Literal["shortlist", "reject"]

from typing import Dict


class QuestionIn(BaseModel):
    text: str = Field(min_length=3)
    options: List[str] = Field(min_length=2, max_length=6)
    correct: int = Field(ge=0)


class TestConfigIn(BaseModel):
    pass_percent: int = Field(60, ge=1, le=100)
    duration_min: int = Field(20, ge=5, le=180)


class SubmitIn(BaseModel):
    answers: Dict[str, int] = {}