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
        """Ingests tenders from a specific source or 'all' registered sources.
        
        When source='all', distributes the quota evenly (half-and-half round-robin)
        across live portals (e.g. World Bank STEP and e-GP Bangladesh).
        Defaults to limit=50 if not specified.
        """
        source_key = source.lower()
        limit_val = limit if limit is not None else 50

        if source_key == "all":
            # Collect results from all external/live feeds (exclude test_dataset)
            active_feeds = [k for k in self._adapters.keys() if k != "test_dataset"]
            feed_results: Dict[str, List[NormalizedTender]] = {}

            # Fetch enough from each feed to allow balanced interleaving
            fetch_per_feed = max(5, limit_val)
            for key in active_feeds:
                adapter = self._adapters[key]
                try:
                    tenders = adapter.fetch_tenders(limit=fetch_per_feed)
                    if tenders:
                        feed_results[key] = tenders
                except Exception as e:
                    logger.error("Failed pulling from %s: %s", key, e)

            # Round-robin / interleaved fair distribution (half-and-half across portals)
            balanced_tenders: List[NormalizedTender] = []
            max_len = max((len(t_list) for t_list in feed_results.values()), default=0)

            for i in range(max_len):
                for key in feed_results:
                    if i < len(feed_results[key]):
                        balanced_tenders.append(feed_results[key][i])
                        if len(balanced_tenders) >= limit_val:
                            return balanced_tenders

            return balanced_tenders[:limit_val]

        if source_key not in self._adapters:
            raise ValueError(f"Unknown ingestion source '{source}'. Available: {list(self._adapters.keys())}")

        adapter = self._adapters[source_key]
        return adapter.fetch_tenders(limit=limit_val)


ingestion_pipeline = IngestionPipeline()
