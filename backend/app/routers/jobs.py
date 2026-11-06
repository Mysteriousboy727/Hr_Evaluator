from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job, Slot, Application, User
from ..schemas import JobIn, SlotsIn
from ..security import current_user, require_role
from ..services import now_ist, fill_pending

router = APIRouter(tags=["jobs"])


def _own_job(db, job_id, hr):
    job = db.get(Job, job_id)
    if not job or job.hr_id != hr.id:
        raise HTTPException(404, "Job not found")
    return job


def _job_out(j, db, user):
    d = {"id": j.id, "title": j.title, "description": j.description, "required_skills": j.required_skills,
         "location": j.location, "work_mode": j.work_mode, "stipend": j.stipend,
         "duration_months": j.duration_months, "threshold": j.threshold, "status": j.status}
    if user.role == "hr":
        apps = db.query(Application).filter(Application.job_id == j.id).all()
        d["applicants"] = len(apps)
        d["shortlisted"] = sum(1 for a in apps if a.status.startswith(("Shortlisted", "Test Pending", "Test Passed", "AI Interview", "Interview")))
        d["free_slots"] = db.query(Slot).filter(Slot.job_id == j.id, Slot.application_id.is_(None),
                                                Slot.start > now_ist()).count()
    else:
        d["applied"] = db.query(Application).filter(Application.job_id == j.id,
                                                    Application.student_id == user.id).first() is not None
    return d


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Job)
    q = q.filter(Job.hr_id == user.id) if user.role == "hr" else q.filter(Job.status == "open")
    return [_job_out(j, db, user) for j in q.order_by(Job.id.desc()).all()]


@router.post("/jobs")
def create_job(p: JobIn, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    job = Job(hr_id=hr.id, **p.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_out(job, db, hr)


@router.post("/jobs/{job_id}/close")
def close_job(job_id: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    job = _own_job(db, job_id, hr)
    job.status = "closed"
    db.commit()
    return {"status": "closed"}


@router.get("/jobs/{job_id}/slots")
def get_slots(job_id: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    _own_job(db, job_id, hr)
    out = []
    for s in db.query(Slot).filter(Slot.job_id == job_id).order_by(Slot.start).all():
        who = ""
        if s.application_id:
            a = db.get(Application, s.application_id)
            who = db.get(User, a.student_id).name if a else ""
        out.append({"id": s.id, "start": s.start.isoformat(timespec="minutes"),
                    "booked": s.application_id is not None, "student": who})
    return out


@router.post("/jobs/{job_id}/slots")
def add_slots(job_id: int, p: SlotsIn, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    job = _own_job(db, job_id, hr)
    added = skipped = 0
    now = now_ist()
    for raw in p.slots:
        try:
            start = datetime.fromisoformat(raw).replace(tzinfo=None)
        except ValueError:
            skipped += 1
            continue
        clash = db.query(Slot).filter(Slot.hr_id == hr.id, Slot.start > start - timedelta(minutes=30),
                                      Slot.start < start + timedelta(minutes=30)).first()
        if start <= now or clash:
            skipped += 1
            continue
        db.add(Slot(job_id=job.id, hr_id=hr.id, start=start))
        db.flush()
        added += 1
    fill_pending(db, job.id)
    db.commit()
    return {"added": added, "skipped": skipped}