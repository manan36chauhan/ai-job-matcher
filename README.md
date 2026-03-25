AI Job Matcher is a machine learning-powered job recommendation system that matches candidates with relevant jobs based on their profile and preferences. It has a FastAPI backend, a PostgreSQL database with pgvector, and a Streamlit frontend.
The matching algorithm combines three signals: TF-IDF semantic similarity between candidate profiles and job descriptions (55% weight), skill keyword overlap (35%), and location matching (10%). There's also a feedback loop — candidates can like or dislike jobs, and the system learns from that to adjust future recommendations.
Tech stack: Python 3.13, FastAPI, SQLAlchemy, Alembic (migrations), scikit-learn (TF-IDF + cosine similarity), PostgreSQL + pgvector via Docker, and Streamlit for the UI.
How to run it:

Start the database: docker-compose up -d (spins up a pgvector-enabled PostgreSQL container)
Activate the virtual environment: source .venv/bin/activate
Run database migrations: alembic upgrade head
Start the API server: uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
Start the Streamlit frontend (separate terminal): streamlit run streamlit_app.py

The API will be at http://localhost:8000 and the UI at http://localhost:8501.
Key API endpoints include POST /jobs/import_csv for bulk importing jobs, POST /candidates to create profiles, POST /match/{candidate_id} to get ranked job matches, and POST /feedback for the like/dislike learning loop.
