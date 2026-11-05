import re
from pypdf import PdfReader

QUALITY_KEYWORDS = ["project", "intern", "github", "experience", "education", "certif", "hackathon"]


def extract_resume_text(path: str) -> str:
    try:
        if path.lower().endswith(".pdf"):
            return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:  # noqa: BLE001
        return ""


def split_skills(s: str):
    return [x.strip().lower() for x in re.split(r"[,\n;]", s or "") if x.strip()]


def _has(text: str, skill: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def score_application(job, resume_text: str, declared_skills: str, a: dict) -> dict:
    required = split_skills(job.required_skills)
    declared = set(split_skills(declared_skills))

    # ---- resume + skills: 50 points ----
    verified = [s for s in required if _has(resume_text, s)]
    declared_only = [s for s in required if s not in verified and s in declared]
    missing = [s for s in required if s not in verified and s not in declared]
    skill_pts = 35 * (len(verified) + 0.5 * len(declared_only)) / len(required) if required else 17.5
    words = len(resume_text.split())
    hits = sum(1 for k in QUALITY_KEYWORDS if k in resume_text.lower())
    quality = min(words / 300, 1) * 7 + min(hits, 4) / 4 * 8
    resume_score = skill_pts + quality
    warnings = []
    if words < 30:
        warnings.append("Resume text could not be read (scanned PDF?) - review manually")

    # ---- screening answers: 50 points ----
    def wc(k):
        return len(str(a.get(k, "")).split())

    exp_text = str(a.get("experience", "")).lower()
    exp_cov = (sum(1 for s in required if _has(exp_text, s)) / len(required)) if required else 0.5
    terms = str(a.get("terms", "")).lower() == "yes"
    loc = str(a.get("location", "")).lower() == "yes"
    try:
        months = float(a.get("months", 0))
    except (TypeError, ValueError):
        months = 0
    pts = min(wc("intro") / 40, 1) * 8
    pts += exp_cov * 8 + min(wc("experience") / 50, 1) * 8
    pts += 10 if terms else 0
    pts += 4 if loc else 0
    pts += min(months / job.duration_months, 1) * 8
    pts += 4 if str(a.get("noc", "")).lower() in ("yes", "not required") else 0

    knockouts = []
    if not terms:
        knockouts.append("Not comfortable with working hours / stipend")
    if not loc and job.work_mode != "remote":
        knockouts.append("Not comfortable with location / work mode")
    if months < job.duration_months:
        knockouts.append(f"Cannot commit to the {job.duration_months}-month duration")

    return {
        "resume_score": round(resume_score, 1), "answer_score": round(pts, 1),
        "total": round(resume_score + pts, 1),
        "matched_skills": verified, "declared_only": declared_only, "missing_skills": missing,
        "knockouts": knockouts, "warnings": warnings,
    }