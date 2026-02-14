from collections import Counter
from typing import Tuple, Dict, Set

from app.core.scoring import extract_skills


def build_skill_preferences(
    candidate_text: str,
    liked_job_texts: list[str],
    disliked_job_texts: list[str],
) -> Tuple[Dict[str, float], Set[str], Set[str]]:
    """
    Returns:
      weights: skill -> boost weight in [-0.15, +0.15]
      liked_skills: set of common liked skills
      disliked_skills: set of common disliked skills
    """
    base_skills = extract_skills(candidate_text)

    liked = Counter()
    for t in liked_job_texts:
        liked.update(extract_skills(t))

    disliked = Counter()
    for t in disliked_job_texts:
        disliked.update(extract_skills(t))

    # skills the user explicitly likes/dislikes (excluding what already in CV)
    liked_skills = {s for s, c in liked.items() if c >= 1 and s not in base_skills}
    disliked_skills = {s for s, c in disliked.items() if c >= 1 and s not in base_skills}

    weights: Dict[str, float] = {}

    # boost liked skills, penalize disliked skills
    for s in liked_skills:
        weights[s] = min(0.15, 0.05 + 0.02 * liked[s])
    for s in disliked_skills:
        weights[s] = max(-0.15, -0.05 - 0.02 * disliked[s])

    return weights, liked_skills, disliked_skills


def preference_adjustment(job_text: str, weights: Dict[str, float]) -> float:
    job_skills = extract_skills(job_text)
    return sum(weights.get(s, 0.0) for s in job_skills)
