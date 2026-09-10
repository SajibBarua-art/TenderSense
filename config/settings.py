"""Configuration settings for TenderSense."""
import os
from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General App Info
    app_name: str = "TenderSense"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Debug mode")
    database_url: str = Field(default="sqlite:///./tendersense.db", description="Database connection URL")

    # API Keys & Open-Source Free Providers
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key (Paid)")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API Key (Paid)")
    groq_api_key: Optional[str] = Field(default=None, description="Groq API Key (100% Free, runs Llama 3.3 / 3.1)")
    huggingface_api_key: Optional[str] = Field(default=None, description="Hugging Face User Access Token (Free)")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", description="Local Ollama base URL")

    # Semantic Matcher Settings
    embedding_provider: str = Field(default="local", description="Embedding provider: 'local', 'huggingface', 'openai', or 'sentence-transformers'")
    openai_embedding_model: str = "text-embedding-3-small"
    huggingface_embedding_model: str = "BAAI/bge-small-en-v1.5"
    semantic_similarity_threshold: float = Field(default=0.60, description="Baseline semantic similarity threshold")

    # LLM Summary Writer Settings
    llm_provider: str = Field(default="mock", description="LLM provider: 'groq', 'huggingface', 'mock', 'openai', 'anthropic', or 'ollama'")
    groq_model: str = "groq/compound-mini"
    openai_summary_model: str = "gpt-4o-mini"
    anthropic_summary_model: str = "claude-3-5-haiku-20241022"

    # Rules Engine Defaults
    default_allowed_geographies: List[str] = Field(
        default=["Bangladesh", "South Asia", "Global", "East Asia And Pacific", "Worldwide"],
        description="Default allowed geographies if none explicitly required"
    )

    # Multi-currency Exchange Rates normalized to USD
    # Rates: 1 unit of Currency = X USD
    exchange_rates_to_usd: Dict[str, float] = Field(
        default={
            "USD": 1.0,
            "BDT": 0.00833,   # ~120 BDT per USD
            "EUR": 1.08,
            "GBP": 1.28,
            "INR": 0.012,
            "AUD": 0.65,
        }
    )

    # Ranking Thresholds
    score_grade_s_threshold: float = 0.82
    score_grade_a_threshold: float = 0.68
    score_grade_b_threshold: float = 0.50

    # Paths
    profile_data_path: str = "data/bracit_profile.json"
    test_dataset_path: str = "data/test_tenders_40.json"


# Global cached settings instance
settings = Settings()
