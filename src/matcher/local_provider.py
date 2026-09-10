"""Local Semantic Vector Embedding Provider.

Uses sentence-transformers if available, or scikit-learn vector semantics with
n-gram contextual weighting and cosine similarity.
"""
import logging
from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.matcher.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class LocalVectorProvider(BaseEmbeddingProvider):
    """Generates normalized vector representations using semantic n-gram weighting or sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.st_model = None
        self.vectorizer = None
        self._init_model()

    def _init_model(self):
        """Attempts to load sentence-transformers; falls back gracefully to scikit-learn TF-IDF."""
        try:
            from sentence_transformers import SentenceTransformer
            self.st_model = SentenceTransformer(self.model_name)
            logger.info("SentenceTransformer '%s' loaded successfully.", self.model_name)
        except ImportError:
            logger.info("SentenceTransformers not installed. Utilizing Scikit-Learn semantic vectorizer.")
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english",
                min_df=1
            )

    def fit_corpus(self, corpus: List[str]):
        """Fits vocabulary on domain knowledge base (profile, services, projects)."""
        if self.st_model is not None:
            return
        logger.info("Fitting LocalVectorProvider vocabulary on %d documents.", len(corpus))
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
            token_pattern=r"(?u)\b\w[\w\-]+\b",
            min_df=1
        )
        self.vectorizer.fit(corpus)
        self._corpus_fitted = True

    def embed_text(self, text: str) -> List[float]:
        """Embeds single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds list of strings into dense vector representations."""
        if self.st_model is not None:
            embeddings = self.st_model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        if not getattr(self, "_corpus_fitted", False):
            self.fit_corpus(texts)

        batch_matrix = self.vectorizer.transform(texts).toarray()

        # Normalize rows to unit vectors
        norms = np.linalg.norm(batch_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = batch_matrix / norms
        return normalized.tolist()

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates cosine similarity between two vector embeddings."""
        a = np.array(vec_a).reshape(1, -1)
        b = np.array(vec_b).reshape(1, -1)
        sim = float(cosine_similarity(a, b)[0][0])
        return max(0.0, min(1.0, sim))
