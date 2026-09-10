"""Tests for Data Collection Pipeline, adapters, and benchmark dataset loader."""
import pytest
from src.ingestion.dataset_loader import dataset_loader
from src.ingestion.egp_bangladesh import EGPBangladeshAdapter
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.wb_step import WorldBankStepAdapter
from src.ingestion.ungm import UNGMPortalAdapter
from src.ingestion.adb import ADBPortalAdapter
from src.models.tender import PortalSource


def test_egp_adapter_fetch_and_normalize():
    """Tests e-GP Bangladesh adapter parsing and normalization."""
    adapter = EGPBangladeshAdapter()
    tenders = adapter.fetch_tenders(limit=5)
    assert len(tenders) > 0
    t = tenders[0]
    assert t.source_portal == PortalSource.EGP_BANGLADESH
    assert t.tender_id.startswith("EGP-")
    assert t.currency == "BDT"
    assert t.country_name == "Bangladesh"
    assert t.closing_date is not None


def test_world_bank_adapter_fetch_and_normalize():
    """Tests World Bank STEP adapter parsing and normalization."""
    adapter = WorldBankStepAdapter()
    tenders = adapter.fetch_tenders(limit=5)
    assert len(tenders) > 0
    t = tenders[0]
    assert t.source_portal == PortalSource.WORLD_BANK_STEP
    assert t.tender_id.startswith("WB-")
    assert t.currency == "USD"
    assert len(t.country_code) == 2
    assert t.closing_date is not None


def test_test_dataset_loader_40_tenders():
    """Tests that the benchmark dataset contains exactly 40 labeled tenders and loads cleanly."""
    tenders = dataset_loader.fetch_tenders(limit=100)
    assert len(tenders) == 40, f"Expected 40 labeled benchmark tenders, found {len(tenders)}"

    # Check format balance
    egp_tenders = [t for t in tenders if t.source_portal == PortalSource.EGP_BANGLADESH]
    wb_tenders = [t for t in tenders if t.source_portal == PortalSource.WORLD_BANK_STEP]
    assert len(egp_tenders) >= 15
    assert len(wb_tenders) >= 10

    # Ensure all have benchmark metadata
    for t in tenders:
        meta = t.raw_payload.get("_benchmark_meta")
        assert meta is not None
        assert "expected_eligible" in meta
        assert "expected_grade" in meta
        assert "expected_recommendation" in meta


def test_ingestion_pipeline_extensibility():
    """Tests that future feeds (like UNGM and ADB) plug into the pipeline seamlessly."""
    pipeline = IngestionPipeline()
    sources = pipeline.get_registered_sources()
    assert "egp_bd" in sources
    assert "world_bank" in sources
    assert "ungm" in sources
    assert "adb" in sources
    assert "test_dataset" in sources

    # Test dynamic registration of custom future adapter
    class CustomRegionalPortal(EGPBangladeshAdapter):
        portal_name = PortalSource.TEST_DATASET

    pipeline.register_adapter("regional_bd", CustomRegionalPortal())
    assert "regional_bd" in pipeline.get_registered_sources()


def test_ingestion_pipeline_fair_distribution_and_default_limit():
    """Verifies that source='all' balances portals half-and-half and defaults to limit=20."""
    pipeline = IngestionPipeline()

    # 1. Test limit=5: Must have representation from both portals (e.g. 3 and 2)
    tenders_5 = pipeline.ingest(source="all", limit=5)
    assert len(tenders_5) == 5
    portals_5 = {t.source_portal for t in tenders_5}
    assert PortalSource.EGP_BANGLADESH in portals_5
    assert PortalSource.WORLD_BANK_STEP in portals_5
    egp_count = sum(1 for t in tenders_5 if t.source_portal == PortalSource.EGP_BANGLADESH)
    wb_count = sum(1 for t in tenders_5 if t.source_portal == PortalSource.WORLD_BANK_STEP)
    assert abs(egp_count - wb_count) <= 1, "Must be balanced half-and-half"

    # 2. Test default limit (None): Must default to 20 tenders
    tenders_def = pipeline.ingest(source="all", limit=None)
    assert len(tenders_def) == 20
    egp_def = sum(1 for t in tenders_def if t.source_portal == PortalSource.EGP_BANGLADESH)
    wb_def = sum(1 for t in tenders_def if t.source_portal == PortalSource.WORLD_BANK_STEP)
    assert egp_def == 10 and wb_def == 10, "Expected exactly 10 from e-GP and 10 from World Bank"
