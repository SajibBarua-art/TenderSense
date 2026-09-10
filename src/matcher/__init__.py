"""AI Semantic Matcher package."""
from src.matcher.base import BaseEmbeddingProvider
from src.matcher.local_provider import LocalVectorProvider
from src.matcher.openai_provider import OpenAIEmbeddingProvider
from src.matcher.semantic_matcher import semantic_matcher, SemanticMatcher

__all__ = [
    "BaseEmbeddingProvider",
    "LocalVectorProvider",
    "OpenAIEmbeddingProvider",
    "semantic_matcher",
    "SemanticMatcher",
]
