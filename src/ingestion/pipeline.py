"""Data collection pipeline coordinating all portal adapters."""
import logging
from typing import Dict, List, Optional

from src.ingestion.base import BaseIngestionAdapter
from src.ingestion.dataset_loader import TestDatasetLoader
from src.ingestion.egp_bangladesh import EGPBangladeshAdapter
from src.ingestion.wb_step import WorldBankStepAdapter
from src.ingestion.ungm import UNGMPortalAdapter
from src.ingestion.adb import ADBPortalAdapter
from src.models.tender import NormalizedTender

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Coordinates automated ingestion across multiple procurement portals and datasets."""

    def __init__(self):
        self._adapters: Dict[str, BaseIngestionAdapter] = {
            "test_dataset": TestDatasetLoader(),
            "egp_bd": EGPBangladeshAdapter(),
            "world_bank": WorldBankStepAdapter(),
            "ungm": UNGMPortalAdapter(),
            "adb": ADBPortalAdapter(),
        }

    def register_adapter(self, source_key: str, adapter: BaseIngestionAdapter):
        """Allows dynamic registration of future feeds (e.g. UNGM, ADB, regional portals)."""
        self._adapters[source_key.lower()] = adapter
        logger.info("Registered new ingestion adapter: %s (%s)", source_key, adapter.portal_name)

    def get_registered_sources(self) -> List[str]:
        """Lists all registered ingestion sources."""
        return list(self._adapters.keys())

    def ingest(self, source: str = "test_dataset", limit: Optional[int] = None) -> List[NormalizedTender]:
        """Ingests tenders from a specific source or 'all' registered sources."""
        source_key = source.lower()
        limit_val = limit if limit is not None else 100

        if source_key == "all":
            all_tenders: List[NormalizedTender] = []
            for key, adapter in self._adapters.items():
                if key == "test_dataset":
                    continue  # Skip test dataset when pulling live/all portals
                try:
                    tenders = adapter.fetch_tenders(limit=limit_val)
                    all_tenders.extend(tenders)
                except Exception as e:
                    logger.error("Failed pulling from %s: %s", key, e)
            return all_tenders[:limit_val]

        if source_key not in self._adapters:
            raise ValueError(f"Unknown ingestion source '{source}'. Available: {list(self._adapters.keys())}")

        adapter = self._adapters[source_key]
        return adapter.fetch_tenders(limit=limit_val)


ingestion_pipeline = IngestionPipeline()
