"""Pydantic schemas for tender payloads (e-GP Bangladesh, World Bank STEP, and Normalized domain model)."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, AliasChoices
from dateutil import parser as date_parser


class PortalSource(str, Enum):
    """Supported and future procurement portal sources."""
    EGP_BANGLADESH = "e-GP Bangladesh"
    WORLD_BANK_STEP = "World Bank STEP"
    UNGM = "UNGM"
    ADB = "ADB"
    TEST_DATASET = "Test Dataset"


class UrgencyLevel(str, Enum):
    """Urgency categorization based on days until submission deadline."""
    CRITICAL = "CRITICAL"   # <= 3 days
    URGENT = "URGENT"       # <= 7 days
    NORMAL = "NORMAL"       # > 7 days
    EXPIRED = "EXPIRED"     # <= 0 days


class EGPBangladeshTender(BaseModel):
    """Resilient schema for Bangladesh e-GP (eprocure.gov.bd) tender notices."""
    slNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("slNo", "sl_no", "slno"))
    tenderId: str = Field(..., validation_alias=AliasChoices("tenderId", "tender_id", "tenderid", "id"))
    refNo: Optional[str] = Field(default=None, validation_alias=AliasChoices("refNo", "ref_no", "refno"))
    status: Optional[str] = Field(default="Live")
    nature: Optional[str] = Field(default="Goods", validation_alias=AliasChoices("nature", "procurement_nature"))
    title: str = Field(..., validation_alias=AliasChoices("title", "tender_title", "description"))
    ministry: Optional[str] = Field(default=None)
    division: Optional[str] = Field(default=None)
    organization: Optional[str] = Field(default=None)
    peName: Optional[str] = Field(default="", validation_alias=AliasChoices("peName", "pe_name"))
    tenderType: Optional[str] = Field(default="NCT", validation_alias=AliasChoices("tenderType", "tender_type"))
    method: Optional[str] = Field(default="OTM", validation_alias=AliasChoices("method", "procurement_method"))
    publishingDate: Optional[str] = Field(default=None, validation_alias=AliasChoices("publishingDate", "publishing_date"))
    closingDate: Optional[str] = Field(default=None, validation_alias=AliasChoices("closingDate", "closing_date", "submission_deadline"))
    district: Optional[str] = Field(default="Dhaka")
    category: Optional[str] = Field(default=None)
    budgetType: Optional[str] = Field(default="Revenue", validation_alias=AliasChoices("budgetType", "budget_type"))
    sourceOfFunds: Optional[str] = Field(default="Government", validation_alias=AliasChoices("sourceOfFunds", "source_of_funds"))
    projectName: Optional[str] = Field(default="Not applicable", validation_alias=AliasChoices("projectName", "project_name"))
    documentPriceBDT: Optional[str] = Field(default="500", validation_alias=AliasChoices("documentPriceBDT", "document_price_bdt"))
    officialName: Optional[str] = Field(default=None, validation_alias=AliasChoices("officialName", "official_name"))
    officialDesignation: Optional[str] = Field(default=None, validation_alias=AliasChoices("officialDesignation", "official_designation"))
    meetingStartDate: Optional[str] = Field(default=None, validation_alias=AliasChoices("meetingStartDate", "meeting_start_date"))
    lastSellingDate: Optional[str] = Field(default=None, validation_alias=AliasChoices("lastSellingDate", "last_selling_date"))


class WorldBankNotice(BaseModel):
    """Resilient schema for World Bank STEP notices (supports exact schema & live API)."""
    id: Any = Field(..., description="Notice ID", validation_alias=AliasChoices("id", "notice_id", "noticeid"))
    bid_description: str = Field(
        default="World Bank Procurement Package",
        description="Description of the bid",
        validation_alias=AliasChoices("bid_description", "notice_title", "project_name", "description")
    )
    country_name: str = Field(
        default="Global",
        description="Country name",
        validation_alias=AliasChoices("country_name", "project_ctry_name", "countryname", "country")
    )
    country_code: Optional[str] = Field(
        default="GL",
        description="Two-letter country code",
        validation_alias=AliasChoices("country_code", "countrycode", "project_ctry_code")
    )
    deadline_date: Optional[str] = Field(
        default=None,
        description="Deadline date format",
        validation_alias=AliasChoices("submission_deadline_date", "deadline_date", "deadline")
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Publication date format",
        validation_alias=AliasChoices("publication_date", "noticedate", "published_date", "submission_date")
    )
    notice_type: Optional[str] = Field(default=None, validation_alias=AliasChoices("notice_type", "noticetype"))
    procurement_category: Optional[str] = Field(
        default="Consulting Services",
        validation_alias=AliasChoices("procurement_category", "procurement_group", "category")
    )
    procurement_method: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("procurement_method", "procurement_method_name")
    )
    project_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("project_id", "projectid"))
    region: Optional[str] = Field(default=None, validation_alias=AliasChoices("region", "region_name"))
    sector: Optional[str] = Field(default=None, validation_alias=AliasChoices("sector", "majorsector_percent"))
    url: Optional[str] = Field(default=None, validation_alias=AliasChoices("url", "notice_url"))
    publication___fiscal_year: Optional[int] = Field(default=None, validation_alias=AliasChoices("publication___fiscal_year", "fiscal_year"))
    publication___calendar_year: Optional[int] = Field(default=None, validation_alias=AliasChoices("publication___calendar_year", "calendar_year"))


class NormalizedTender(BaseModel):
    """Unified normalized domain model representing any tender across any portal."""
    tender_id: str = Field(..., description="Unique identifier for the tender")
    source_portal: PortalSource = Field(..., description="Source portal or feed name")
    title: str = Field(..., description="Cleaned title or summary of procurement")
    description: str = Field(..., description="Full text scope of work / deliverables")
    category: Optional[str] = Field(default="General", description="Category or sector")
    procurement_type: Optional[str] = Field(default="Goods", description="Goods, Works, Consulting, Non-consulting Services")
    procurement_method: Optional[str] = Field(default=None, description="OTM, RFQ, QCBS, etc.")
    
    # Financial & Requirements
    estimated_value: Optional[float] = Field(default=None, description="Estimated contract value")
    currency: str = Field(default="BDT", description="Currency (BDT, USD, EUR, etc.)")
    required_turnover: Optional[float] = Field(default=None, description="Extracted or declared required annual turnover")
    required_certifications: List[str] = Field(default_factory=list, description="Extracted required certifications")
    allowed_geographies: List[str] = Field(default_factory=list, description="Allowed countries / regions")
    
    # Dates & Deadlines
    publication_date: Optional[datetime] = Field(default=None, description="Parsed publication timestamp")
    closing_date: Optional[datetime] = Field(default=None, description="Parsed deadline timestamp")
    days_until_deadline: int = Field(default=0, description="Calculated days until deadline from current time")
    urgency_flag: UrgencyLevel = Field(default=UrgencyLevel.NORMAL, description="Urgency categorization")
    
    # Metadata
    issuing_entity: Optional[str] = Field(default=None, description="Ministry, Agency, or Department")
    country_code: Optional[str] = Field(default="BD", description="Two-letter ISO country code")
    country_name: Optional[str] = Field(default="Bangladesh", description="Full country name")
    source_url: Optional[str] = Field(default=None, description="Link to online notice")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Raw source JSON document")

    @classmethod
    def calculate_urgency(cls, days: int) -> UrgencyLevel:
        """Calculates urgency classification from remaining days."""
        if days <= 0:
            return UrgencyLevel.EXPIRED
        elif days <= 3:
            return UrgencyLevel.CRITICAL
        elif days <= 7:
            return UrgencyLevel.URGENT
        return UrgencyLevel.NORMAL

    @classmethod
    def parse_date_safely(cls, date_str: Optional[str]) -> Optional[datetime]:
        """Safely parses a variety of procurement portal date strings."""
        if not date_str or date_str.strip() in ("", "Not applicable", "N/A"):
            return None
        try:
            return date_parser.parse(date_str)
        except Exception:
            return None
