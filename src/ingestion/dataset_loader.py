"""Dataset loader for the 40 labeled benchmark tenders."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from src.ingestion.base import BaseIngestionAdapter
from src.ingestion.egp_bangladesh import EGPBangladeshAdapter
from src.ingestion.wb_step import WorldBankStepAdapter
from src.models.tender import NormalizedTender, PortalSource

logger = logging.getLogger(__name__)


class TestDatasetLoader(BaseIngestionAdapter):
    """Loads, validates, and parses the 40 labeled tenders benchmark dataset."""

    portal_name = PortalSource.TEST_DATASET

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = dataset_path or settings.test_dataset_path
        self.egp_adapter = EGPBangladeshAdapter()
        self.wb_adapter = WorldBankStepAdapter()

    def fetch_raw(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads raw labeled dataset from JSON file."""
        path = Path(self.dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found at: {self.dataset_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data[:limit]

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedTender:
        """Normalizes an individual item from the benchmark dataset based on its declared format."""
        item_format = raw_data.get("format", "egp").lower()
        inner_data = raw_data.get("data", {})

        if item_format == "egp":
            tender = self.egp_adapter.normalize(inner_data)
        elif item_format in ("world_bank", "wb"):
            tender = self.wb_adapter.normalize(inner_data)
        else:
            raise ValueError(f"Unknown dataset item format: {item_format}")

        # Preserve benchmark metadata
        if "id" in raw_data:
            tender.tender_id = raw_data["id"]
        
        # Attach ground truth expectations in raw payload for test verification
        tender.raw_payload["_benchmark_meta"] = {
            "expected_eligible": raw_data.get("expected_eligible"),
            "expected_grade": raw_data.get("expected_grade"),
            "expected_recommendation": raw_data.get("expected_recommendation"),
            "notes": raw_data.get("notes")
        }

        return tender

    def load_labeled_dataset(self, limit: int = 50) -> List[Tuple[NormalizedTender, Dict[str, Any]]]:
        """Returns tuples of (NormalizedTender, ground_truth_dict)."""
        raw_items = self.fetch_raw(limit=limit)
        results = []
        for item in raw_items:
            norm_tender = self.normalize(item)
            meta = item.get("raw_payload", {}).get("_benchmark_meta", {})
            meta["expected_eligible"] = item.get("expected_eligible")
            meta["expected_grade"] = item.get("expected_grade")
            meta["expected_recommendation"] = item.get("expected_recommendation")
            meta["notes"] = item.get("notes")
            results.append((norm_tender, meta))
        return results


dataset_loader = TestDatasetLoader()
