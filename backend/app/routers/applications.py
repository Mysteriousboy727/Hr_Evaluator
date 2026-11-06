import json
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Application, Job, Slot, User
from ..questions import QUESTIONS
from ..schemas import DecisionIn
from ..scoring import extract_resume_text, score_application
from ..security import current_user, require_role
from ..services import notify, shortlist, fill_pending

router = APIRouter(tags=["applications"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _app_out(a, job, student=None, hr_view=False):
    d = {"id": a.id, "job_id": a.job_id, "job_title": job.title, "status": a.status,
         "total_score": a.total_score, "resume_score": a.resume_score, "answer_score": a.answer_score,
         "slot_start": a.slot_start.isoformat(timespec="minutes") if a.slot_start else "",
         "meeting_link": a.meeting_link, "created_at": a.created_at.isoformat(timespec="minutes")}
    if hr_view:
        d.update({"student": student.name, "email": student.email, "phone": student.phone,
                  "college": a.college, "skills": a.skills, "breakdown": a.breakdown, "answers": a.answers,
                  "resume_name": a.resume_name})
    return d


def _owned(db, app_id, hr):
    a = db.get(Application, app_id)
    job = db.get(Job, a.job_id) if a else None
    if not a or job.hr_id != hr.id:
        raise HTTPException(404, "Application not found")
    return a, job


@router.get("/questions")
def questions(user: User = Depends(current_user)):
    return QUESTIONS


@router.post("/jobs/{job_id}/apply")
def apply(job_id: int, college: str = Form(...), skills: str = Form(...), answers: str = Form(...),
          resume: UploadFile = File(...), db: Session = Depends(get_db),
          student: User = Depends(require_role("student"))):
    job = db.get(Job, job_id)
    if not job or job.status != "open":
        raise HTTPException(404, "This role is not open")
    if db.query(Application).filter(Application.job_id == job_id, Application.student_id == student.id).first():
        raise HTTPException(400, "You already applied for this role")
    ext = Path(resume.filename or "").suffix.lower()
    if ext not in (".pdf", ".txt"):
        raise HTTPException(400, "Resume must be a PDF or TXT file")
    data = resume.file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Resume must be under 5 MB")
    try:
        ans = json.loads(answers)
    except ValueError:
        raise HTTPException(400, "Bad answers payload")
    if any(not q.get("optional") and not str(ans.get(q["key"], "")).strip() for q in QUESTIONS):
        raise HTTPException(400, "Please answer all required questions")

    path = UPLOAD_DIR / f"{secrets.token_hex(8)}{ext}"
    path.write_bytes(data)
    text = extract_resume_text(str(path))
    res = score_application(job, text, skills, ans)

    if res["knockouts"]:
        status = "Not Shortlisted"
    elif res["total"] >= job.threshold:
        status = "Shortlisted"
    elif res["total"] >= job.threshold - 15:
        status = "Under HR Review"
    else:
        status = "Not Shortlisted"

    a = Application(job_id=job.id, student_id=student.id, college=college, skills=skills,
                    resume_name=resume.filename, resume_path=str(path), resume_text=text[:20000],
                    resume_score=res["resume_score"], answer_score=res["answer_score"],
                    total_score=res["total"], breakdown=res, answers=ans, status=status)
    db.add(a)
    db.flush()
    hr = db.get(User, job.hr_id)
    if status == "Shortlisted":
        shortlist(db, a)
    elif status == "Under HR Review":
        notify(db, student, f"Application received - {job.title}",
               "Your application is under review by our HR team. You will be notified of the outcome.")
        notify(db, hr, f"Needs review: {student.name} - {job.title}",
               f"Score {res['total']} is just below the shortlist threshold ({job.threshold}). Open the applicants list to decide.")
    else:
        notify(db, student, f"Application update - {job.title}",
               "Thank you for applying. Based on your skills match and screening answers, "
               "we are not moving forward with this role right now.")
    db.commit()
    return {"status": a.status, "total": a.total_score, "breakdown": res}


@router.get("/my/applications")
def my_applications(db: Session = Depends(get_db), student: User = Depends(require_role("student"))):
    rows = db.query(Application).filter(Application.student_id == student.id).order_by(Application.id.desc()).all()
    return [_app_out(a, db.get(Job, a.job_id)) for a in rows]


@router.get("/jobs/{job_id}/applications")
def job_applications(job_id: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    job = db.get(Job, job_id)
    if not job or job.hr_id != hr.id:
        raise HTTPException(404, "Job not found")
    rows = db.query(Application).filter(Application.job_id == job_id).order_by(Application.total_score.desc()).all()
    return [_app_out(a, job, db.get(User, a.student_id), hr_view=True) for a in rows]


@router.post("/applications/{app_id}/decision")
def decide(app_id: int, p: DecisionIn, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    a, job = _owned(db, app_id, hr)
    student = db.get(User, a.student_id)
    if p.decision == "shortlist":
        if a.status not in ("Under HR Review", "Not Shortlisted", "Rejected by HR", "Test Failed", "AI Interview Pending"):
            raise HTTPException(400, f"Already: {a.status}")
        shortlist(db, a)
    else:
        slot = db.query(Slot).filter(Slot.application_id == a.id).first()
        if slot:
            slot.application_id = None
        a.slot_start = None
        a.meeting_link = ""
        a.status = "Rejected by HR"
        notify(db, student, f"Application update - {job.title}",
               "Thank you for your interest. We will not be moving forward with your application.")
        db.flush()
        fill_pending(db, job.id)
    db.commit()
    return {"status": a.status}


@router.post("/applications/{app_id}/confirm")
def confirm(app_id: int, db: Session = Depends(get_db), student: User = Depends(require_role("student"))):
    a = db.get(Application, app_id)
    if not a or a.student_id != student.id:
        raise HTTPException(404, "Application not found")
    if a.status != "Interview Scheduled":
        raise HTTPException(400, "Nothing to confirm")
    job = db.get(Job, a.job_id)
    a.status = "Interview Confirmed"
    notify(db, db.get(User, job.hr_id), f"Attendance confirmed: {student.name}",
           f"{student.name} confirmed the interview for {job.title} on {a.slot_start:%d %b %Y, %I:%M %p} IST.")
    db.commit()
    return {"status": a.status}


@router.get("/applications/{app_id}/resume")
def resume(app_id: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    a, _ = _owned(db, app_id, hr)
    return FileResponse(a.resume_path, filename=a.resume_name or "resume")