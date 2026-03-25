# AI Job Matcher

An ML-powered job recommendation system that matches candidates with relevant jobs based on their profile, skills, and location preferences. It learns from feedback to improve recommendations over time.

## What It Does

- **Candidate Profiles** — Create candidates with a name, CV/profile text, and location preference
- **Job Repository** — Add jobs individually via API or bulk import via CSV
- **Smart Matching** — Ranks jobs using TF-IDF semantic similarity, skill overlap, and location matching
- **Feedback Loop** — Like or dislike jobs to teach the system your preferences

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Database | PostgreSQL + pgvector (Docker) |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic |
| ML / Ranking | scikit-learn (TF-IDF + cosine similarity) |
| Frontend | Streamlit |
| Language | Python 3.13 |

## Project Structure
```
ai-job-matcher/
├── app/
│   ├── api/
│   │   └── main.py          # FastAPI endpoints
│   ├── core/
│   │   ├── scoring.py       # Skill-based scoring
│   │   ├── tfidf_ranker.py  # Semantic similarity ranking
│   │   └── preferences.py   # Preference learning from feedback
│   └── db/
│       ├── models.py        # ORM models (Job, Candidate, Feedback, Match)
│       └── session.py       # DB connection
├── alembic/                 # Database migrations
├── streamlit_app.py         # Frontend UI
├── docker-compose.yml       # PostgreSQL + pgvector setup
├── requirements.txt
└── .env                     # Environment config
```

## How to Run

### Prerequisites

- Python 3.13+
- Docker & Docker Compose

### 1. Start the Database
```bash
docker-compose up -d
```

This starts a pgvector-enabled PostgreSQL container on port `5432`.

### 2. Set Up Python Environment
```bash
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the root:
```
DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/jobmatcher
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Start the API Server
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`

### 6. Start the Frontend (separate terminal)
```bash
streamlit run streamlit_app.py
```

UI available at: `http://localhost:8501`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/jobs` | Add a single job |
| `POST` | `/jobs/import_csv` | Bulk import jobs from CSV |
| `POST` | `/candidates` | Create a candidate profile |
| `POST` | `/match/{candidate_id}` | Get top matching jobs for a candidate |
| `POST` | `/feedback` | Submit like (+1) or dislike (-1) on a job |

### CSV Import Format

Your CSV must include these columns:
```
title, company, location, url, description
```

## Matching Algorithm

Each job is scored using a weighted combination:
```
Final Score = (0.55 × semantic_similarity)
            + (0.35 × skill_overlap)
            + (0.10 × location_match)
            + preference_adjustment
```

- **Semantic Similarity** — TF-IDF vectors + cosine similarity between candidate profile and job description
- **Skill Overlap** — Detects shared skills (Python, SQL, Docker, AWS, PyTorch, pandas, etc.)
- **Location Match** — Binary bonus if candidate's preferred location matches the job
- **Preference Adjustment** — Boosts jobs with skills from liked jobs; penalizes skills from disliked ones

## Database Schema

- **Jobs** — `id`, `title`, `company`, `location`, `url`, `description`, `created_at`
- **Candidates** — `id`, `name`, `profile_text`, `location_pref`, `created_at`
- **Feedback** — `id`, `candidate_id`, `job_id`, `label` (+1 or -1), `created_at`
- **Matches** — `id`, `candidate_id`, `job_id`, `score`, `reasons`, `created_at`
