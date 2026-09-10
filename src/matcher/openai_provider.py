"""OpenAI text-embedding-3-small provider."""
import logging
from typing import List, Optional
import httpx
from config.settings import settings
from src.matcher.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using OpenAI API (text-embedding-3-small)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model
        self.api_url = "https://api.openai.com/v1/embeddings"

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string."""
        results = self.embed_batch([text])
        return results[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of strings."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": cleaned_texts,
            "model": self.model,
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # Sort by index to maintain ordering
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]
