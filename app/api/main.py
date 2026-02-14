from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Job, Candidate, Match
from app.core.scoring import skill_overlap, final_score, build_reasons
from app.core.tfidf_ranker import TfidfRanker

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
