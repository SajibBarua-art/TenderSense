"""Base abstract class for all procurement portal ingestion adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.models.tender import NormalizedTender, PortalSource


class BaseIngestionAdapter(ABC):
    """Abstract base adapter for portal feeds (e-GP BD, World Bank, UNGM, ADB, Dataset)."""

    portal_name: PortalSource

    @abstractmethod
    def fetch_raw(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches raw JSON notices from the source portal or mock feed."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedTender:
        """Parses raw JSON data against specific schema and normalizes into common NormalizedTender."""
        pass

    def fetch_tenders(self, limit: int = 50) -> List[NormalizedTender]:
        """Convenience method to pull and normalize all tenders."""
        raw_items = self.fetch_raw(limit=limit)
        normalized_items = []
        for item in raw_items:
            try:
                norm = self.normalize(item)
                normalized_items.append(norm)
            except Exception as e:
                # Log parsing error and continue
                continue
        return normalized_items
