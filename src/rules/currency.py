"""Currency conversion and financial normalization utility."""
from typing import Dict, Optional
from config.settings import settings


class CurrencyNormalizer:
    """Normalizes financial values across different currencies (BDT, USD, EUR, GBP)."""

    def __init__(self, exchange_rates_to_usd: Optional[Dict[str, float]] = None):
        self.rates_to_usd = exchange_rates_to_usd or settings.exchange_rates_to_usd

    def convert_to_usd(self, amount: float, currency: str) -> float:
        """Converts an amount in a given currency to USD."""
        curr = currency.upper().strip()
        rate = self.rates_to_usd.get(curr)
        if rate is None:
            # Fallback if unknown currency, assume 1:1 or log warning
            return amount
        return amount * rate

    def convert_to_bdt(self, amount: float, currency: str) -> float:
        """Converts an amount in a given currency to BDT."""
        amount_usd = self.convert_to_usd(amount, currency)
        bdt_rate = self.rates_to_usd.get("BDT", 0.00833)
        return amount_usd / bdt_rate if bdt_rate > 0 else amount_usd * 120.0

    def compare_turnover(
        self,
        required_turnover: float,
        tender_currency: str,
        company_turnover_bdt: float,
        company_turnover_usd: float
    ) -> bool:
        """Compares required turnover against company turnover in a common currency.
        Returns True if company satisfies turnover (company >= required).
        """
        curr = tender_currency.upper().strip()
        if curr == "BDT":
            return company_turnover_bdt >= required_turnover
        elif curr == "USD":
            return company_turnover_usd >= required_turnover
        else:
            required_in_usd = self.convert_to_usd(required_turnover, curr)
            return company_turnover_usd >= required_in_usd


currency_normalizer = CurrencyNormalizer()
