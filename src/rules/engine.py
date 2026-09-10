"""Hard-Logic Rules-Based Eligibility Engine (No AI)."""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from config.settings import settings
from src.models.profile import BracITProfile
from src.models.rules import EligibilityEvaluation, RuleCheckDetail
from src.models.tender import NormalizedTender
from src.rules.currency import currency_normalizer


class RulesEngine:
    """Fixed deterministic rules engine implementing hard logic for tender qualification.
    
    Evaluates:
      1. Minimum annual turnover criteria with currency conversion.
      2. Required organizational certifications (e.g. ISO standards, CMMI level).
      3. Allowed geographical regions and country restrictions.
      4. Deadline validity (not expired).
      5. Procurement nature boundary checks.
    """

    KNOWN_CERT_PATTERNS = [
        (r"\biso\s*27001\b", "ISO 27001"),
        (r"\biso\s*9001\b", "ISO 9001"),
        (r"\biso\s*20000\b", "ISO 20000"),
        (r"\biso\s*14001\b", "ISO 14001"),
        (r"\biso\s*13485\b", "ISO 13485"),
        (r"\bcmmi(?:\-dev)?\s*(?:level\s*)?5\b", "CMMI Level 5"),
        (r"\bcmmi(?:\-dev)?\s*(?:level\s*)?3\b", "CMMI Level 3"),
    ]

    EXCLUDED_NATURE_KEYWORDS = [
        "bridge over", "asphalt", "excavator", "road roller", "speed boat", "patrol inshore boat",
        "diesel generator", "substation transformer", "office furniture", "teak wood",
        "stationery", "surgical gloves", "reagents", "tubewell", "civil engineering work"
    ]

    def evaluate_tender(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> EligibilityEvaluation:
        """Executes all deterministic rule checks and produces an EligibilityEvaluation."""
        checks: List[RuleCheckDetail] = []
        failure_reasons: List[str] = []
        passed_rules: List[str] = []

        # 1. Deadline Check
        deadline_passed, deadline_msg, req_val, comp_val = self._check_deadline(tender)
        checks.append(RuleCheckDetail(
            rule_name="deadline_validity",
            passed=deadline_passed,
            required_value=req_val,
            company_value=comp_val,
            message=deadline_msg
        ))
        if deadline_passed:
            passed_rules.append("deadline_validity")
        else:
            failure_reasons.append(deadline_msg)

        # 2. Turnover Check
        turnover_passed, turnover_msg, req_turn, comp_turn = self._check_turnover(tender, profile)
        checks.append(RuleCheckDetail(
            rule_name="minimum_turnover",
            passed=turnover_passed,
            required_value=req_turn,
            company_value=comp_turn,
            message=turnover_msg
        ))
        if turnover_passed:
            passed_rules.append("minimum_turnover")
        else:
            failure_reasons.append(turnover_msg)

        # 3. Certification Check
        certs_passed, certs_msg, req_certs, comp_certs = self._check_certifications(tender, profile)
        checks.append(RuleCheckDetail(
            rule_name="mandatory_certifications",
            passed=certs_passed,
            required_value=req_certs,
            company_value=comp_certs,
            message=certs_msg
        ))
        if certs_passed:
            passed_rules.append("mandatory_certifications")
        else:
            failure_reasons.append(certs_msg)

        # 4. Geography Check
        geo_passed, geo_msg, req_geo, comp_geo = self._check_geography(tender, profile)
        checks.append(RuleCheckDetail(
            rule_name="geographical_eligibility",
            passed=geo_passed,
            required_value=req_geo,
            company_value=comp_geo,
            message=geo_msg
        ))
        if geo_passed:
            passed_rules.append("geographical_eligibility")
        else:
            failure_reasons.append(geo_msg)

        # 5. Core Procurement Nature Boundary Check
        nature_passed, nature_msg, req_nat, comp_nat = self._check_procurement_nature(tender)
        checks.append(RuleCheckDetail(
            rule_name="procurement_nature_boundary",
            passed=nature_passed,
            required_value=req_nat,
            company_value=comp_nat,
            message=nature_msg
        ))
        if nature_passed:
            passed_rules.append("procurement_nature_boundary")
        else:
            failure_reasons.append(nature_msg)

        is_eligible = len(failure_reasons) == 0
        return EligibilityEvaluation(
            is_eligible=is_eligible,
            failure_reasons=failure_reasons,
            passed_rules=passed_rules,
            checks=checks
        )

    def _check_deadline(self, tender: NormalizedTender) -> Tuple[bool, str, Any, Any]:
        """Verifies if the tender closing deadline has not expired."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if tender.closing_date:
            # Strip timezone for comparison if needed
            closing_naive = tender.closing_date.replace(tzinfo=None)
            if closing_naive < now:
                days_expired = (now - closing_naive).days
                return (
                    False,
                    f"Submission deadline expired {days_expired} day(s) ago on {tender.closing_date.strftime('%d-%b-%Y')}.",
                    tender.closing_date.strftime("%Y-%m-%d"),
                    now.strftime("%Y-%m-%d")
                )
        if tender.days_until_deadline < 0:
            return (
                False,
                f"Submission deadline expired on {tender.closing_date or 'past date'}.",
                "Active deadline",
                "Expired"
            )
        return True, "Submission deadline is active.", "Future Date", f"{tender.days_until_deadline} days remaining"

    def _check_turnover(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> Tuple[bool, str, Any, Any]:
        """Extracts and verifies required annual turnover against company turnover."""
        required_turnover = tender.required_turnover
        currency = tender.currency or "BDT"

        # If not explicitly provided on the model, attempt regex extraction from text
        combined_text = f"{tender.title} {tender.description}"
        if required_turnover is None:
            extracted_turnover, extracted_curr = self._extract_turnover_from_text(combined_text)
            if extracted_turnover:
                required_turnover = extracted_turnover
                currency = extracted_curr or currency

        if required_turnover is None or required_turnover <= 0:
            return True, "No minimum turnover constraint specified in tender.", None, f"{profile.annual_turnover_bdt:,.0f} BDT"

        satisfies = currency_normalizer.compare_turnover(
            required_turnover=required_turnover,
            tender_currency=currency,
            company_turnover_bdt=profile.annual_turnover_bdt,
            company_turnover_usd=profile.annual_turnover_usd
        )

        if satisfies:
            return (
                True,
                f"Company turnover satisfies requirement ({required_turnover:,.0f} {currency}).",
                f"{required_turnover:,.0f} {currency}",
                f"{profile.annual_turnover_bdt:,.0f} BDT (~${profile.annual_turnover_usd:,.0f} USD)"
            )
        else:
            return (
                False,
                f"Turnover requirement of {required_turnover:,.0f} {currency} exceeds BracIT annual capacity of {profile.annual_turnover_bdt:,.0f} BDT (~${profile.annual_turnover_usd:,.0f} USD).",
                f"{required_turnover:,.0f} {currency}",
                f"{profile.annual_turnover_bdt:,.0f} BDT (~${profile.annual_turnover_usd:,.0f} USD)"
            )

    def _extract_turnover_from_text(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Heuristic regex parser for turnover figures like '900 Million BDT' or '$10M'."""
        # e.g., 'Turnover Required: 900 Million BDT'
        match = re.search(r"(?:turnover|revenue)\s*(?:required|of|minimum)?[:\s]*(\d+(?:\.\d+)?)\s*(million|crore|m|b)?\s*(bdt|usd|\$)?", text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            multiplier = (match.group(2) or "").lower()
            curr = (match.group(3) or "").upper()
            if curr == "$":
                curr = "USD"
            elif not curr:
                curr = "BDT" if "bdt" in text.lower() else "USD"

            if multiplier in ("million", "m"):
                val *= 1_000_000
            elif multiplier == "crore":
                val *= 10_000_000
            elif multiplier == "b":
                val *= 1_000_000_000
            return val, curr
        return None, None

    def _check_certifications(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> Tuple[bool, str, Any, Any]:
        """Detects required certifications and checks against profile's active certifications."""
        company_certs: Set[str] = {c.standard_code.upper() for c in profile.certifications if c.status == "Active"}
        
        # Combine explicit requirements and detected requirements
        required_certs: Set[str] = set(tender.required_certifications)
        combined_text = f"{tender.title} {tender.description}"
        
        for pattern, cert_code in self.KNOWN_CERT_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                # If tender mentions "mandatory requirement: ISO 14001" or similar
                if any(w in combined_text.lower() for w in ["mandatory", "required", "certified", "requirement", "must possess"]):
                    required_certs.add(cert_code)

        if not required_certs:
            return True, "No specific certifications mandated.", [], list(company_certs)

        missing_certs = []
        for req in required_certs:
            req_upper = req.upper()
            # Special check for CMMI Level
            if "CMMI LEVEL 5" in req_upper:
                if not any("CMMI LEVEL 5" in c for c in company_certs):
                    missing_certs.append("CMMI Level 5 (BracIT has CMMI Level 3)")
            elif not any(req_upper in c or c in req_upper for c in company_certs):
                missing_certs.append(req)

        if missing_certs:
            return (
                False,
                f"Missing mandatory certification(s): {', '.join(missing_certs)}.",
                list(required_certs),
                list(company_certs)
            )
        return True, "All mandatory certifications verified.", list(required_certs), list(company_certs)

    def _check_geography(
        self,
        tender: NormalizedTender,
        profile: BracITProfile
    ) -> Tuple[bool, str, Any, Any]:
        """Validates country and regional operating permissions."""
        country = tender.country_name or "Bangladesh"
        region = getattr(tender, "region", None)
        operating_geos = {g.lower() for g in profile.operating_regions}
        operating_geos.add("global")
        operating_geos.add("worldwide")

        # Explicitly allowed tender geographies
        if tender.allowed_geographies:
            geo_overlap = any(g.lower() in operating_geos for g in tender.allowed_geographies)
            if not geo_overlap:
                return (
                    False,
                    f"Geographical restriction: Tender allowed geographies ({', '.join(tender.allowed_geographies)}) do not match BracIT operational regions.",
                    tender.allowed_geographies,
                    profile.operating_regions
                )

        # Check country & region
        c_lower = country.lower()
        if c_lower in ("bangladesh", "bd"):
            return True, "Domestic tender within Bangladesh.", "Bangladesh", profile.operating_regions

        # Check if country or region is covered
        is_covered = (
            c_lower in operating_geos or
            (region and region.lower() in operating_geos) or
            "global" in operating_geos
        )

        # Check for domestic restrictions in non-eligible countries
        text_lower = f"{tender.title} {tender.description}".lower()
        if any(term in text_lower for term in ["national competitive bidding", "domestic bidders only", "local bidders only"]):
            if c_lower not in ("bangladesh", "bd"):
                return (
                    False,
                    f"Geographical exclusion: Tender in {country} specifies National Competitive Bidding restricted to domestic entities.",
                    f"Domestic entities of {country}",
                    profile.operating_regions
                )

        if not is_covered:
            return (
                False,
                f"Geographical exclusion: Country '{country}' is outside BracIT's target operational geographies.",
                country,
                profile.operating_regions
            )

        return True, f"Eligible geography: {country}.", country, profile.operating_regions

    def _check_procurement_nature(self, tender: NormalizedTender) -> Tuple[bool, str, Any, Any]:
        """Checks for non-applicable pure civil works, physical commodities, or heavy machinery."""
        text = f"{tender.title} {tender.description} {tender.category or ''}".lower()
        for kw in self.EXCLUDED_NATURE_KEYWORDS:
            if kw in text:
                # If the tender is clearly pure civil engineering or physical commodities
                if tender.procurement_type in ("Works", "Goods") and not any(it in text for it in ["software", "cloud", "mis", "portal", "digital", "data", "it equipment", "server"]):
                    return (
                        False,
                        f"Out of scope procurement nature: Tender contains physical/civil works commodity '{kw}'.",
                        "IT / Software / Systems / Consulting",
                        tender.procurement_type or "Goods/Works"
                    )
        return True, "Procurement nature is within acceptable scope.", "IT/Software/Consulting", tender.procurement_type


rules_engine = RulesEngine()
