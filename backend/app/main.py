import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, SessionLocal
from .models import Application, Job, User
from .routers import auth, jobs, applications, notifications, tests, qupload, interview
from .services import now_ist, notify, BOOKED

Base.metadata.create_all(bind=engine)


def send_due_reminders():
    db = SessionLocal()
    try:
        now = now_ist()
        due = db.query(Application).filter(
            Application.status.in_(BOOKED), Application.reminded.is_(False),
            Application.slot_start.isnot(None),
            Application.slot_start <= now + timedelta(hours=1),
            Application.slot_start > now - timedelta(minutes=30)).all()
        for a in due:
            job = db.get(Job, a.job_id)
            student = db.get(User, a.student_id)
            hr = db.get(User, job.hr_id)
            when = a.slot_start.strftime("%I:%M %p IST")
            extra = "" if a.status == "Interview Confirmed" else " Please confirm your attendance in the app."
            notify(db, student, f"Reminder: interview at {when}",
                   f"Your interview for {job.title} is at {when}.\nJoin: {a.meeting_link}{extra}")
            notify(db, hr, f"Reminder: interview with {student.name} at {when}",
                   f"{job.title}\nJoin: {a.meeting_link}\nStatus: {a.status}")
            a.reminded = True
        db.commit()
    finally:
        db.close()


async def reminder_loop():
    while True:
        try:
            await asyncio.to_thread(send_due_reminders)
        except Exception as e:  # noqa: BLE001
            print("reminder error:", e)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()


app = FastAPI(title="Akshara Hiring", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, jobs.router, applications.router, notifications.router, tests.router, qupload.router, interview.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}