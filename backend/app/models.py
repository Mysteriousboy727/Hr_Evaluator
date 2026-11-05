from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Float
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, default="")
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student | hr
    created_at = Column(DateTime, default=datetime.utcnow)


class Token(Base):
    __tablename__ = "tokens"
    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    hr_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    required_skills = Column(String, default="")  # comma separated
    location = Column(String, default="")
    work_mode = Column(String, default="onsite")
    stipend = Column(String, default="")
    duration_months = Column(Integer, default=3)
    threshold = Column(Integer, default=60)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)


class Slot(Base):
    __tablename__ = "slots"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    hr_id = Column(Integer, ForeignKey("users.id"))
    start = Column(DateTime, nullable=False)  # naive, IST
    application_id = Column(Integer, nullable=True)


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    college = Column(String, default="")
    skills = Column(Text, default="")
    resume_name = Column(String, default="")
    resume_path = Column(String, default="")
    resume_text = Column(Text, default="")
    resume_score = Column(Float, default=0)
    answer_score = Column(Float, default=0)
    total_score = Column(Float, default=0)
    breakdown = Column(JSON, default=dict)
    answers = Column(JSON, default=dict)
    status = Column(String, default="Applied")
    slot_start = Column(DateTime, nullable=True)
    meeting_link = Column(String, default="")
    reminded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String)
    body = Column(Text)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TestConfig(Base):
    __tablename__ = "test_configs"
    job_id = Column(Integer, ForeignKey("jobs.id"), primary_key=True)
    pass_percent = Column(Integer, default=60)
    duration_min = Column(Integer, default=20)


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    text = Column(Text, nullable=False)
    options = Column(JSON, default=list)
    correct = Column(Integer, default=0)


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, index=True)
    question_ids = Column(JSON, default=list)
    started_at = Column(DateTime, default=datetime.utcnow)
    duration_min = Column(Integer, default=20)
    pass_percent = Column(Integer, default=60)
    submitted_at = Column(DateTime, nullable=True)
    correct = Column(Integer, default=0)
    total = Column(Integer, default=0)
    percent = Column(Float, default=0)
    passed = Column(Boolean, default=False)