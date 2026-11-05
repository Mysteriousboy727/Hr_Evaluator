import io
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Question, User
from ..qparse import parse_questions
from ..security import require_role
from ..services import release_waiting
from .tests import _own_job, upload_questions as upload_csv

router = APIRouter(tags=["tests"])


@router.post("/jobs/{job_id}/test/upload-file")
def upload_file(job_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                hr: User = Depends(require_role("hr"))):
    ext = Path(file.filename or "").suffix.lower()
    if ext == ".csv":
        return upload_csv(job_id, file, db, hr)
    if ext not in (".pdf", ".txt"):
        raise HTTPException(400, "Upload a PDF, TXT or CSV file")
    _own_job(db, job_id, hr)
    data = file.file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "File must be under 5 MB")
    try:
        if ext == ".pdf":
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        else:
            text = data.decode("utf-8-sig", errors="ignore")
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Could not read this file. Is it a valid PDF without a password?")
    if len(text.strip()) < 20:
        raise HTTPException(400, "No text found. A scanned or image PDF cannot be read. "
                                 "Export the PDF from Word or Google Docs instead.")
    qs, errors = parse_questions(text)
    for q in qs:
        db.add(Question(job_id=job_id, text=q["text"], options=q["options"], correct=q["correct"]))
    db.flush()
    release_waiting(db, job_id)
    db.commit()
    if not qs and not errors:
        errors.append("No questions recognised. Number each question (1. 2. 3.) and start options with A) B) C) D).")
    return {"added": len(qs), "errors": errors}