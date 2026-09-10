"""Unit tests for free open-source API providers (Groq and Hugging Face)."""
import pytest
from unittest.mock import MagicMock, patch

from src.matcher.huggingface_provider import HuggingFaceEmbeddingProvider
from src.models.matching import SemanticMatchResult
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation
from src.models.tender import NormalizedTender, PortalSource
from src.orchestration.engine import orchestrator
from src.summarizer.groq_writer import GroqSummaryWriter


def test_groq_summary_writer_payload_generation():
    """Tests that GroqSummaryWriter formats requests compatible with Llama 3.1 open source models."""
    writer = GroqSummaryWriter(api_key="gsk_mock_key", model="llama-3.1-8b-instant")
    assert writer.api_key == "gsk_mock_key"
    assert writer.model == "llama-3.1-8b-instant"

    profile = orchestrator.get_profile()
    tender = NormalizedTender(
        tender_id="TND-GROQ",
        source_portal=PortalSource.EGP_BANGLADESH,
        title="National Portal Development",
        description="Portal implementation",
        days_until_deadline=14
    )
    rules_eval = EligibilityEvaluation(is_eligible=True)
    semantic_result = SemanticMatchResult(
        similarity_score=0.85,
        domain_alignment="High",
        matched_services=["e-Governance & Public Sector Citizen Services"]
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "This tender aligns directly with BracIT's e-Governance practice and past government service bus projects."
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        summary = writer.generate_summary(tender, profile, rules_eval, semantic_result)
        assert "BracIT" in summary
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "llama-3.1-8b-instant"
        assert "Bearer gsk_mock_key" in call_kwargs["headers"]["Authorization"]


def test_huggingface_embedding_provider():
    """Tests Hugging Face serverless embedding provider."""
    hf_provider = HuggingFaceEmbeddingProvider(
        api_key="hf_mock_token",
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    assert hf_provider.api_key == "hf_mock_token"
    assert "all-MiniLM-L6-v2" in hf_provider.api_url

    mock_embeddings = [[0.1, 0.2, 0.3]]
    mock_response = MagicMock()
    mock_response.json.return_value = mock_embeddings
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = hf_provider.embed_text("Sample tender description")
        assert res == [0.1, 0.2, 0.3]
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert "Bearer hf_mock_token" in call_kwargs["headers"]["Authorization"]
