"""Ingestion module for TenderSense."""
from src.ingestion.base import BaseIngestionAdapter
from src.ingestion.egp_bangladesh import EGPBangladeshAdapter
from src.ingestion.wb_step import WorldBankStepAdapter
from src.ingestion.ungm import UNGMPortalAdapter
from src.ingestion.adb import ADBPortalAdapter
from src.ingestion.dataset_loader import TestDatasetLoader, dataset_loader
from src.ingestion.pipeline import IngestionPipeline, ingestion_pipeline

__all__ = [
    "BaseIngestionAdapter",
    "EGPBangladeshAdapter",
    "WorldBankStepAdapter",
    "UNGMPortalAdapter",
    "ADBPortalAdapter",
    "TestDatasetLoader",
    "dataset_loader",
    "IngestionPipeline",
    "ingestion_pipeline",
]
