"""Hugging Face Serverless Inference API Embedding Provider (100% Free Open-Source)."""
import logging
from typing import List, Optional
import httpx

from config.settings import settings
from src.matcher.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using Hugging Face's free Serverless Inference API.
    
    Default model: sentence-transformers/all-MiniLM-L6-v2 (or BAAI/bge-small-en-v1.5)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.huggingface_embedding_model or "BAAI/bge-small-en-v1.5"
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.model}"

    def embed_text(self, text: str) -> List[float]:
        """Embeds single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds list of strings using free Hugging Face Inference API."""
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": texts,
            "options": {"wait_for_model": True}
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            embeddings = resp.json()
            return embeddings
