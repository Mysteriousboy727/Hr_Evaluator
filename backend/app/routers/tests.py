import csv
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Application, Job, Question, TestAttempt, User
from ..schemas import QuestionIn, SubmitIn, TestConfigIn
from ..security import require_role
from ..services import MIN_QUESTIONS, TEST_PENDING, get_cfg, notify, pass_test, after_test, release_waiting

router = APIRouter(tags=["tests"])


def _own_job(db, job_id, hr):
    job = db.get(Job, job_id)
    if not job or job.hr_id != hr.id:
        raise HTTPException(404, "Job not found")
    return job


def _clean_options(options):
    opts = [str(o).strip() for o in options]
    while opts and not opts[-1]:
        opts.pop()
    if len(opts) < 2 or any(not o for o in opts):
        raise ValueError("Give at least 2 options and no empty option in the middle")
    return opts


# ---------------- HR ----------------
@router.get("/jobs/{job_id}/test")
def get_test(job_id: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    _own_job(db, job_id, hr)
    cfg = get_cfg(db, job_id)
    db.commit()
    qs = db.query(Question).filter(Question.job_id == job_id).order_by(Question.id).all()
    return {"pass_percent": cfg.pass_percent, "duration_min": cfg.duration_min, "min_questions": MIN_QUESTIONS,
            "questions": [{"id": q.id, "text": q.text, "options": q.options, "correct": q.correct} for q in qs]}


@router.put("/jobs/{job_id}/test/config")
def set_config(job_id: int, p: TestConfigIn, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    _own_job(db, job_id, hr)
    cfg = get_cfg(db, job_id)
    cfg.pass_percent = p.pass_percent
    cfg.duration_min = p.duration_min
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/test/questions")
def add_question(job_id: int, p: QuestionIn, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    _own_job(db, job_id, hr)
    try:
        opts = _clean_options(p.options)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if p.correct >= len(opts):
        raise HTTPException(400, "The correct answer must be one of the options")
    db.add(Question(job_id=job_id, text=p.text.strip(), options=opts, correct=p.correct))
    db.flush()
    release_waiting(db, job_id)
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/test/upload")
def upload_questions(job_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                     hr: User = Depends(require_role("hr"))):
    _own_job(db, job_id, hr)
    raw = file.file.read().decode("utf-8-sig", errors="ignore")
    added, errors = 0, []
    for i, row in enumerate(csv.reader(io.StringIO(raw)), start=1):
        row = [c.strip() for c in row]
        if not any(row):
            continue
        if i == 1 and row[0].lower() in ("question", "questions"):
            continue
        if len(row) < 4:
            errors.append(f"Row {i}: need question, at least 2 options and the correct answer")
            continue
        text, correct_raw = row[0], row[-1].upper()
        try:
            opts = _clean_options(row[1:-1])
        except ValueError as e:
            errors.append(f"Row {i}: {e}")
            continue
        if len(correct_raw) == 1 and correct_raw in "ABCDEF":
            correct = ord(correct_raw) - 65
        elif correct_raw.isdigit():
            correct = int(correct_raw) - 1
        else:
            errors.append(f"Row {i}: correct answer must be A-F or a number")
            continue
        if not (0 <= correct < len(opts)):
            errors.append(f"Row {i}: correct answer does not match an option")
            continue
        db.add(Question(job_id=job_id, text=text, options=opts, correct=correct))
        added += 1
    db.flush()
    release_waiting(db, job_id)
    db.commit()
    return {"added": added, "errors": errors}


@router.delete("/questions/{qid}")
def delete_question(qid: int, db: Session = Depends(get_db), hr: User = Depends(require_role("hr"))):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404, "Question not found")
    _own_job(db, q.job_id, hr)
    db.delete(q)
    db.commit()
    return {"ok": True}


# ---------------- Student ----------------
def _my_app(db, app_id, student):
    a = db.get(Application, app_id)
    if not a or a.student_id != student.id:
        raise HTTPException(404, "Application not found")
    return a


def _attempt(db, app_id):
    return db.query(TestAttempt).filter(TestAttempt.application_id == app_id).first()


def _payload(db, att):
    qs = {q.id: q for q in db.query(Question).filter(Question.id.in_(att.question_ids)).all()}
    left = (att.started_at + timedelta(minutes=att.duration_min) - datetime.utcnow()).total_seconds()
    return {"duration_min": att.duration_min, "seconds_left": max(0, int(left)),
            "questions": [{"id": qs[i].id, "text": qs[i].text, "options": qs[i].options}
                          for i in att.question_ids if i in qs]}


@router.post("/applications/{app_id}/test/start")
def start_test(app_id: int, db: Session = Depends(get_db), student: User = Depends(require_role("student"))):
    a = _my_app(db, app_id, student)
    att = _attempt(db, a.id)
    if att and att.submitted_at:
        raise HTTPException(400, "You have already submitted this test")
    if not att:
        if a.status != TEST_PENDING:
            raise HTTPException(400, "No test is available for this application")
        qs = db.query(Question).filter(Question.job_id == a.job_id).order_by(Question.id).all()
        if len(qs) < MIN_QUESTIONS:
            raise HTTPException(400, "The test is not ready yet")
        cfg = get_cfg(db, a.job_id)
        att = TestAttempt(application_id=a.id, question_ids=[q.id for q in qs], started_at=datetime.utcnow(),
                          duration_min=cfg.duration_min, pass_percent=cfg.pass_percent)
        db.add(att)
        db.commit()
        db.refresh(att)
    return _payload(db, att)


@router.post("/applications/{app_id}/test/submit")
def submit_test(app_id: int, p: SubmitIn, db: Session = Depends(get_db),
                student: User = Depends(require_role("student"))):
    a = _my_app(db, app_id, student)
    att = _attempt(db, a.id)
    if not att:
        raise HTTPException(400, "Start the test first")
    if att.submitted_at:
        raise HTTPException(400, "You have already submitted this test")
    job = db.get(Job, a.job_id)
    hr = db.get(User, job.hr_id)
    late = datetime.utcnow() > att.started_at + timedelta(minutes=att.duration_min, seconds=60)
    answers = {} if late else p.answers
    qs = {q.id: q for q in db.query(Question).filter(Question.id.in_(att.question_ids)).all()}
    total = len(qs)
    correct = sum(1 for qid, q in qs.items() if answers.get(str(qid)) == q.correct)
    percent = round(100 * correct / total, 1) if total else 0.0
    passed = percent >= att.pass_percent
    att.submitted_at = datetime.utcnow()
    att.correct, att.total, att.percent, att.passed = correct, total, percent, passed
    if passed:
        after_test(db, a)
    else:
        a.status = "Test Failed"
        notify(db, student, f"Test result - {job.title}",
               f"You scored {percent}% (pass mark {att.pass_percent}%). Thank you for your effort; "
               "HR may still review your application.")
        notify(db, hr, f"Test failed: {student.name} - {job.title}",
               f"Scored {percent}% (pass mark {att.pass_percent}%). Open the applicants list and press "
               "Shortlist if you want to schedule the interview anyway.")
    db.commit()
    return {"status": a.status, "passed": passed, "percent": percent, "correct": correct,
            "total": total, "late": late}