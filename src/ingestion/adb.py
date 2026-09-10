"""Asian Development Bank (ADB) Ingestion Adapter (Future feed ready)."""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from src.ingestion.base import BaseIngestionAdapter
from src.models.tender import NormalizedTender, PortalSource, UrgencyLevel

logger = logging.getLogger(__name__)


class ADBPortalAdapter(BaseIngestionAdapter):
    """Adapter for Asian Development Bank procurement notices."""

    portal_name = PortalSource.ADB

    def __init__(self, feed_url: Optional[str] = None):
        self.feed_url = feed_url

    def fetch_raw(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Placeholder for ADB procurement notice RSS / JSON integration."""
        return []

    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedTender:
        """Normalizes ADB notice into domain NormalizedTender."""
        now = datetime.utcnow()
        return NormalizedTender(
            tender_id=f"ADB-{raw_data.get('notice_id', '0')}",
            source_portal=PortalSource.ADB,
            title=raw_data.get("project_title", "ADB Project Notice"),
            description=raw_data.get("scope_of_work", ""),
            category=raw_data.get("sector", "International Development"),
            procurement_type="Consulting Services",
            currency="USD",
            days_until_deadline=21,
            urgency_flag=UrgencyLevel.NORMAL,
            country_name=raw_data.get("country", "Asia-Pacific"),
            raw_payload=raw_data
        )
