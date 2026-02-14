import re
from typing import Tuple, List

SKILLS = {
    "python", "sql", "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow",
    "docker", "git", "fastapi", "spark", "airflow", "dbt", "aws", "gcp", "azure",
    "nlp", "rag", "llm", "postgres", "etl", "data pipeline"
}

def extract_skills(text: str) -> set[str]:
    t = (text or "").lower()
    found: set[str] = set()
    for s in SKILLS:
        if re.search(r"\b" + re.escape(s) + r"\b", t):
            found.add(s)
    return found

def skill_overlap(candidate_text: str, job_text: str) -> Tuple[float, List[str]]:
    c = extract_skills(candidate_text)
    j = extract_skills(job_text)
    if not j:
        return 0.0, []
    inter = sorted(list(c.intersection(j)))
    score = len(inter) / max(1, len(j))
    return score, inter

def final_score(similarity: float, skill_score: float, location_bonus: float) -> float:
    return (0.55 * similarity) + (0.35 * skill_score) + (0.10 * location_bonus)

def build_reasons(similarity: float, skills: List[str], location_bonus: float) -> str:
    parts = [f"Semantic similarity: {similarity:.3f}"]
    parts.append("Skill overlap: " + (", ".join(skills[:12]) if skills else "low/none"))
    if location_bonus > 0:
        parts.append("Location matches preference")
    return " | ".join(parts)
