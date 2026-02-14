from dataclasses import dataclass
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RankedJob:
    job_id: int
    similarity: float


class TfidfRanker:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=None,
            ngram_range=(1, 2),
            max_features=50000,
        )

    def rank(self, candidate_text: str, job_texts: List[Tuple[int, str]]) -> List[RankedJob]:
        candidate_text = (candidate_text or "").strip()
        if not candidate_text or not job_texts:
            return []

        docs = [candidate_text] + [t for _, t in job_texts]
        X = self.vectorizer.fit_transform(docs)
        sims = cosine_similarity(X[0:1], X[1:]).flatten()

        ranked = [RankedJob(job_id=job_id, similarity=float(s)) for (job_id, _), s in zip(job_texts, sims)]
        ranked.sort(key=lambda x: x.similarity, reverse=True)
        return ranked
