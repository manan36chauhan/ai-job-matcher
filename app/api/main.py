from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Job, Candidate, Match, Feedback
from app.db.session import SessionLocal
from app.db.models import Job, Candidate, Match
from app.core.scoring import skill_overlap, final_score, build_reasons
from app.core.tfidf_ranker import TfidfRanker
from app.core.preferences import build_skill_preferences, preference_adjustment
import csv
import io


app = FastAPI(title="AI Job Matcher (TF-IDF MVP)")

ranker = TfidfRanker()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JobIn(BaseModel):
    title: str
    company: str
    location: str
    url: str
    description: str

class FeedbackIn(BaseModel):
    candidate_id: int
    job_id: int
    label: int  # 1 or -1



class CandidateIn(BaseModel):
    name: str
    profile_text: str
    location_pref: str = "Berlin"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs")
def add_job(payload: JobIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(Job).where(Job.url == payload.url))
    if existing:
        raise HTTPException(status_code=409, detail="Job URL already exists")

    j = Job(**payload.model_dump())
    db.add(j)
    db.commit()
    db.refresh(j)
    return {"id": j.id}

@app.post("/feedback")
def add_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    if payload.label not in (1, -1):
        raise HTTPException(status_code=400, detail="label must be 1 (relevant) or -1 (not relevant)")

    # upsert-like: prevent duplicates
    existing = db.scalar(
        select(Feedback).where(
            Feedback.candidate_id == payload.candidate_id,
            Feedback.job_id == payload.job_id
        )
    )
    if existing:
        existing.label = payload.label
        db.commit()
        return {"status": "updated"}

    fb = Feedback(candidate_id=payload.candidate_id, job_id=payload.job_id, label=payload.label)
    db.add(fb)
    db.commit()
    return {"status": "created"}


@app.post("/jobs/import_csv")
def import_jobs_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))

    required = {"title", "company", "location", "url", "description"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {sorted(list(required))}")

    inserted = 0
    skipped = 0

    for row in reader:
        url = (row.get("url") or "").strip()
        if not url:
            skipped += 1
            continue

        exists = db.scalar(select(Job).where(Job.url == url))
        if exists:
            skipped += 1
            continue

        job = Job(
            title=(row.get("title") or "").strip(),
            company=(row.get("company") or "").strip(),
            location=(row.get("location") or "").strip(),
            url=url,
            description=(row.get("description") or "").strip(),
        )
        db.add(job)
        inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped}


@app.post("/candidates")
def add_candidate(payload: CandidateIn, db: Session = Depends(get_db)):
    c = Candidate(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id}





@app.post("/match/{candidate_id}")
def match(candidate_id: int, top_k: int = 10, db: Session = Depends(get_db)):
    cand = db.get(Candidate, candidate_id)
    # Load feedback
    fb_rows = db.scalars(
        select(Feedback).where(Feedback.candidate_id == candidate_id)
    ).all()

    liked_ids = [f.job_id for f in fb_rows if f.label == 1]
    disliked_ids = [f.job_id for f in fb_rows if f.label == -1]

    liked_jobs = db.scalars(select(Job).where(Job.id.in_(liked_ids))).all() if liked_ids else []
    disliked_jobs = db.scalars(select(Job).where(Job.id.in_(disliked_ids))).all() if disliked_ids else []

    liked_texts = [f"{j.title}\n{j.description}" for j in liked_jobs]
    disliked_texts = [f"{j.title}\n{j.description}" for j in disliked_jobs]

    pref_weights, liked_skills, disliked_skills = build_skill_preferences(
        cand.profile_text, liked_texts, disliked_texts
    )

    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    jobs = db.scalars(select(Job).limit(500)).all()
    if not jobs:
        return {"candidate_id": candidate_id, "results": []}

    job_texts = [(j.id, f"{j.title}\n{j.description}") for j in jobs]
    ranked = ranker.rank(cand.profile_text, job_texts)[:50]

    job_by_id = {j.id: j for j in jobs}
    results = []

    for r in ranked:
        job = job_by_id.get(r.job_id)
        if not job:
            continue

        similarity = r.similarity
        s_score, s_list = skill_overlap(cand.profile_text, f"{job.title}\n{job.description}")
        cand_loc = str(cand.location_pref or "")
        job_loc = str(job.location or "")
        location_bonus = 1.0 if (cand_loc.lower() in job_loc.lower()) else 0.0

        score = final_score(similarity, s_score, location_bonus)
        reasons = build_reasons(similarity, s_list, location_bonus)

        pref_adj = preference_adjustment(f"{job.title}\n{job.description}", pref_weights)
        score = score + pref_adj

        if pref_adj != 0:
            reasons = reasons + f" | Preference adj: {pref_adj:+.3f}"

        results.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "score": round(score, 4),
            "reasons": reasons
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:top_k]

    for r in top:
        db.add(Match(candidate_id=candidate_id, job_id=r["job_id"], score=r["score"], reasons=r["reasons"]))
    db.commit()

    return {"candidate_id": candidate_id, "results": top}
