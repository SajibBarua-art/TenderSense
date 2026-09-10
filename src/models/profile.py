"""Pydantic schemas for the BracIT Capability Profile."""
from typing import List, Optional
from pydantic import BaseModel, Field


class CompanyService(BaseModel):
    """A core capability or service offering of the company."""
    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service title (e.g., Cloud & DevOps Solutions)")
    description: str = Field(..., description="Detailed description of technical offerings")
    keywords: List[str] = Field(default_factory=list, description="Keywords and technology tags")


class PastProject(BaseModel):
    """Historical project completed by the company."""
    project_id: str = Field(..., description="Unique project ID")
    name: str = Field(..., description="Project name")
    client: str = Field(..., description="Client name (e.g., BRAC, Ministry of Health)")
    client_type: str = Field(default="Enterprise", description="Type of client: NGO, Government, Bank, Multilateral")
    description: str = Field(..., description="Scope of work, deliverables, and outcome")
    domain: str = Field(..., description="Domain: e-Governance, Fintech, Healthcare, Supply Chain, etc.")
    technologies: List[str] = Field(default_factory=list, description="Key tech stack used")
    value_bdt: float = Field(..., description="Contract value in BDT")
    value_usd: float = Field(..., description="Contract value in USD equivalent")
    completion_year: int = Field(..., description="Year project was successfully handed over")
    duration_months: int = Field(default=12, description="Project duration in months")


class Certification(BaseModel):
    """Official organizational certification."""
    name: str = Field(..., description="Certification title (e.g., ISO/IEC 27001:2022)")
    standard_code: str = Field(..., description="Standard code (e.g., ISO 27001, ISO 9001, CMMI-3)")
    issuing_body: str = Field(..., description="Auditing or issuing organization")
    valid_until: str = Field(..., description="Expiry date formatted as YYYY-MM-DD")
    status: str = Field(default="Active", description="Active or Expired")


class BracITProfile(BaseModel):
    """Full corporate capability profile schema for BracIT."""
    company_name: str = Field(default="BracIT Services Limited", description="Legal company name")
    tagline: str = Field(default="Empowering Global Growth Through Technology", description="Corporate tagline")
    country_of_incorporation: str = Field(default="Bangladesh", description="HQ Country")
    operating_regions: List[str] = Field(
        default_factory=lambda: ["Bangladesh", "South Asia", "East Asia And Pacific", "Sub-Saharan Africa", "Global"],
        description="Geographies where company is eligible and active"
    )
    annual_turnover_bdt: float = Field(default=650_000_000.0, description="Average annual turnover in BDT (650M BDT)")
    annual_turnover_usd: float = Field(default=5_416_667.0, description="Average annual turnover in USD (~$5.42M)")
    years_in_business: int = Field(default=15, description="Years of formal operations")
    total_staff: int = Field(default=250, description="Total full-time technical personnel")
    services: List[CompanyService] = Field(..., description="List of capability domains and services")
    past_projects: List[PastProject] = Field(..., description="Repository of 10+ completed projects")
    certifications: List[Certification] = Field(..., description="Accreditations and standard certifications")

    def get_summary_text(self) -> str:
        """Returns consolidated text representation of the profile for semantic vectorization."""
        services_text = " ".join([f"{s.name}: {s.description}" for s in self.services])
        projects_text = " ".join([f"{p.name} for {p.client} in {p.domain}: {p.description}" for p in self.past_projects])
        certs_text = " ".join([c.standard_code for c in self.certifications])
        return f"{self.company_name} provides {services_text}. Notable past projects include: {projects_text}. Certified in: {certs_text}."
