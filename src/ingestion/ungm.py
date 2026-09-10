"""United Nations Global Marketplace (UNGM) Ingestion Adapter (Future feed ready)."""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from src.ingestion.base import BaseIngestionAdapter
from src.models.tender import NormalizedTender, PortalSource, UrgencyLevel

logger = logging.getLogger(__name__)


class UNGMPortalAdapter(BaseIngestionAdapter):
    """Adapter for United Nations Global Marketplace procurement notices."""

    portal_name = PortalSource.UNGM

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def fetch_raw(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Placeholder for UNGM API / XML feed integration."""
        return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedTender:
        """Normalizes UNGM notice into domain NormalizedTender."""
        now = datetime.utcnow()
        return NormalizedTender(
            tender_id=f"UNGM-{raw_data.get('id', '0')}",
            source_portal=PortalSource.UNGM,
            title=raw_data.get("title", "UN Procurement Notice"),
            description=raw_data.get("description", ""),
            category=raw_data.get("unspsc_code", "UN Procurement"),
            procurement_type="Services",
            currency="USD",
            days_until_deadline=14,
            urgency_flag=UrgencyLevel.NORMAL,
            country_name=raw_data.get("beneficiary_country", "Global"),
            raw_payload=raw_data
        )
