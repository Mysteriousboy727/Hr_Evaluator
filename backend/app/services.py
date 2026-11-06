import secrets
from datetime import datetime, timedelta
from .models import Notification, Slot, Application, Job, User, TestConfig, Question, TestAttempt
from .email_service import send_mail, build_ics

MIN_QUESTIONS = 3
TEST_SETUP = "Shortlisted - Awaiting Test Setup"
TEST_PENDING = "Test Pending"
WAITING = "Test Passed - Awaiting Slot"
BOOKED = ("Interview Scheduled", "Interview Confirmed")


def now_ist() -> datetime:
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def notify(db, user, title, body, ics=None):
    db.add(Notification(user_id=user.id, title=title, body=body))
    send_mail(user.email, title, body, ics)


def get_cfg(db, job_id):
    c = db.get(TestConfig, job_id)
    if not c:
        c = TestConfig(job_id=job_id, pass_percent=60, duration_min=20)
        db.add(c)
        db.flush()
    return c


def _find_slot(db, app):
    busy = {a.slot_start for a in db.query(Application).filter(
        Application.student_id == app.student_id, Application.status.in_(BOOKED)).all()}
    slots = (db.query(Slot).filter(Slot.job_id == app.job_id, Slot.application_id.is_(None),
                                   Slot.start > now_ist()).order_by(Slot.start).all())
    return next((s for s in slots if s.start not in busy), None)


def book(db, app, slot):
    job = db.get(Job, app.job_id)
    student = db.get(User, app.student_id)
    hr = db.get(User, job.hr_id)
    slot.application_id = app.id
    app.slot_start = slot.start
    app.meeting_link = f"https://meet.jit.si/akshara-{job.id}-{app.id}-{secrets.token_hex(4)}"
    app.status = "Interview Scheduled"
    app.reminded = False
    when = slot.start.strftime("%d %b %Y, %I:%M %p IST")
    att = db.query(TestAttempt).filter(TestAttempt.application_id == app.id).first()
    test_line = f"\nTest score: {att.percent}%" if att and att.submitted_at else ""
    ics = build_ics(f"app{app.id}-{slot.id}@akshara-hr", slot.start, 30,
                    f"Interview - {job.title} - Akshara Enterprises", app.meeting_link)
    notify(db, student, f"Interview booked - {job.title}",
           f"Hi {student.name},\n\nYou are through to the interview round for {job.title}.{test_line}\n"
           f"When: {when}\nJoin: {app.meeting_link}\n\nPlease open My applications and confirm your attendance.",
           ics)
    notify(db, hr, f"Interview booked: {student.name} - {job.title}",
           f"{student.name} ({student.email}, {student.phone}) is ready for interview. Screening score {app.total_score}.{test_line}\n"
           f"When: {when}\nJoin: {app.meeting_link}", ics)
    db.flush()


def pass_test(db, app):
    job = db.get(Job, app.job_id)
    slot = _find_slot(db, app)
    if slot:
        book(db, app, slot)
        return
    app.status = WAITING
    notify(db, db.get(User, app.student_id), f"Test cleared - {job.title}",
           "You cleared the test. An interview slot has not been assigned yet; "
           "you will be notified as soon as one is booked.")
    notify(db, db.get(User, job.hr_id), f"No free slots for {job.title}",
           f"A candidate cleared the test and is waiting (screening score {app.total_score}). "
           "Add interview slots to auto-book them.")
    db.flush()


def open_test(db, app):
    job = db.get(Job, app.job_id)
    student = db.get(User, app.student_id)
    cfg = get_cfg(db, job.id)
    n = db.query(Question).filter(Question.job_id == job.id).count()
    app.status = TEST_PENDING
    notify(db, student, f"You are shortlisted - take the test for {job.title}",
           f"Hi {student.name},\n\nYou have been shortlisted for {job.title}. The next step is a short online test "
           f"({n} questions, {cfg.duration_min} minutes, pass mark {cfg.pass_percent}%).\n"
           "Log in, open My applications and click Take test. The timer starts when you click Start.\n"
           "If you pass, your interview call with HR is booked automatically.")
    db.flush()


def shortlist(db, app):
    att = db.query(TestAttempt).filter(TestAttempt.application_id == app.id).first()
    if att and att.submitted_at:
        # HR override after a failed test: skip the retake and go straight to scheduling
        pass_test(db, app)
        return
    job = db.get(Job, app.job_id)
    student = db.get(User, app.student_id)
    if db.query(Question).filter(Question.job_id == job.id).count() >= MIN_QUESTIONS:
        open_test(db, app)
        return
    first = db.query(Application).filter(Application.job_id == job.id, Application.status == TEST_SETUP,
                                         Application.id != app.id).count() == 0
    app.status = TEST_SETUP
    notify(db, student, f"You are shortlisted - {job.title}",
           "You have been shortlisted. Your test is being prepared and you will be notified as soon as it is ready.")
    if first:
        notify(db, db.get(User, job.hr_id), f"Upload test questions for {job.title}",
               f"{student.name} (score {app.total_score}) is shortlisted. Open the role and add at least "
               f"{MIN_QUESTIONS} test questions (type them or upload a CSV). Shortlisted candidates receive "
               "the test as soon as it is ready.")
    db.flush()


def release_waiting(db, job_id):
    if db.query(Question).filter(Question.job_id == job_id).count() < MIN_QUESTIONS:
        return
    waiting = (db.query(Application).filter(Application.job_id == job_id, Application.status == TEST_SETUP)
               .order_by(Application.total_score.desc()).all())
    for a in waiting:
        open_test(db, a)


def fill_pending(db, job_id):
    pending = (db.query(Application).filter(
        Application.job_id == job_id,
        Application.status.in_((WAITING, "Shortlisted - Awaiting Slot")))
        .order_by(Application.total_score.desc()).all())
    for a in pending:
        slot = _find_slot(db, a)
        if slot:
            book(db, a, slot)

AI_PENDING = "AI Interview Pending"


def ai_enabled():
    import os
    return bool(os.getenv("ANTHROPIC_API_KEY")) and os.getenv("AI_INTERVIEW", "on").lower() != "off"


def after_test(db, app):
    """Called when a candidate passes the test: AI interview first (if enabled), else book the slot."""
    if not ai_enabled():
        pass_test(db, app)
        return
    job = db.get(Job, app.job_id)
    app.status = AI_PENDING
    notify(db, db.get(User, app.student_id), f"Next step: AI interview - {job.title}",
           "You cleared the test. Next is a short AI-led interview in the language of your choice "
           "(about 10 minutes). Log in, open My applications and click Start AI interview. "
           "Your call with HR is booked after it.")
    db.flush()