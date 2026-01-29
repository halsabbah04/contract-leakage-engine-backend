"""Contract Risk Profile Service

Calculates dynamic risk factors based on contract characteristics.
Used to adjust impact calculations and assumptions per-contract.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from ..models.clause import Clause, ClauseType
from ..utils.logging import setup_logging

logger = setup_logging(__name__)


# Regional inflation rates (approximate annual rates)
REGIONAL_INFLATION_RATES = {
    "USD": 0.035,  # US - ~3.5%
    "EUR": 0.025,  # Eurozone - ~2.5%
    "GBP": 0.040,  # UK - ~4.0%
    "BHD": 0.020,  # Bahrain - ~2.0%
    "SAR": 0.025,  # Saudi Arabia - ~2.5%
    "AED": 0.030,  # UAE - ~3.0%
    "KWD": 0.035,  # Kuwait - ~3.5%
    "QAR": 0.030,  # Qatar - ~3.0%
    "OMR": 0.025,  # Oman - ~2.5%
}

# Contract value tiers affect risk assessment
VALUE_TIERS = {
    "small": (0, 100_000),           # < 100K
    "medium": (100_000, 1_000_000),  # 100K - 1M
    "large": (1_000_000, 10_000_000), # 1M - 10M
    "enterprise": (10_000_000, float('inf')),  # > 10M
}

# Risk multipliers based on contract characteristics
RISK_MULTIPLIERS = {
    # Contract duration risk (longer = more risk)
    "duration_short": 0.8,   # < 1 year
    "duration_medium": 1.0,  # 1-3 years
    "duration_long": 1.3,    # 3-5 years
    "duration_very_long": 1.5,  # > 5 years

    # Contract value risk (larger = more scrutiny needed)
    "value_small": 0.7,
    "value_medium": 1.0,
    "value_large": 1.2,
    "value_enterprise": 1.5,

    # Clause complexity (more clauses = more risk areas)
    "complexity_low": 0.8,    # < 10 clauses
    "complexity_medium": 1.0, # 10-30 clauses
    "complexity_high": 1.3,   # > 30 clauses
}


@dataclass
class ContractRiskProfile:
    """Dynamic risk profile for a specific contract."""

    # Contract identification
    contract_id: str

    # Financial characteristics
    contract_value: float
    currency: str
    value_tier: str

    # Temporal characteristics
    duration_years: float
    remaining_years: float
    start_date: Optional[str]
    end_date: Optional[str]

    # Complexity indicators
    total_clauses: int
    clause_types_found: List[str]
    complexity_level: str

    # Risk indicators found in contract
    risk_signals_count: int
    has_auto_renewal: bool
    has_price_escalation: bool
    has_liability_cap: bool
    has_termination_protection: bool

    # Calculated risk factors
    base_risk_multiplier: float
    inflation_rate: float

    # Dynamic probabilities
    pricing_leak_probability: float
    payment_leak_probability: float
    renewal_leak_probability: float
    termination_leak_probability: float
    liability_leak_probability: float
    service_level_leak_probability: float

    def get_risk_percentage(self, category: str) -> float:
        """Get dynamic risk percentage for a leakage category."""
        category_map = {
            "pricing": self.pricing_leak_probability,
            "payment": self.payment_leak_probability,
            "renewal": self.renewal_leak_probability,
            "termination": self.termination_leak_probability,
            "liability": self.liability_leak_probability,
            "service_level": self.service_level_leak_probability,
            "penalties": self.payment_leak_probability,  # Similar to payment
            "volume_commitment": self.pricing_leak_probability,  # Similar to pricing
            "compliance": 0.05,  # Fixed for compliance
            "other": 0.05,  # Default
        }
        return category_map.get(category.lower(), 0.05)

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/storage."""
        return {
            "contract_id": self.contract_id,
            "contract_value": self.contract_value,
            "currency": self.currency,
            "value_tier": self.value_tier,
            "duration_years": self.duration_years,
            "remaining_years": self.remaining_years,
            "total_clauses": self.total_clauses,
            "complexity_level": self.complexity_level,
            "base_risk_multiplier": self.base_risk_multiplier,
            "inflation_rate": self.inflation_rate,
            "risk_signals_count": self.risk_signals_count,
        }


class RiskProfileService:
    """Service to build dynamic risk profiles for contracts."""

    def __init__(self):
        self.inflation_rates = REGIONAL_INFLATION_RATES
        self.value_tiers = VALUE_TIERS
        self.risk_multipliers = RISK_MULTIPLIERS

    def build_profile(
        self,
        contract_id: str,
        clauses: List[Clause],
        contract_value: float,
        currency: str,
        duration_years: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ContractRiskProfile:
        """
        Build a dynamic risk profile for a contract.

        Args:
            contract_id: Contract identifier
            clauses: List of extracted clauses
            contract_value: Total contract value
            currency: Contract currency code
            duration_years: Contract duration in years
            start_date: Contract start date (ISO format)
            end_date: Contract end date (ISO format)

        Returns:
            ContractRiskProfile with dynamic risk factors
        """
        logger.info(f"Building risk profile for contract {contract_id}")

        # Analyze clauses for risk indicators
        clause_analysis = self._analyze_clauses(clauses)

        # Determine value tier
        value_tier = self._get_value_tier(contract_value)

        # Determine complexity level
        complexity_level = self._get_complexity_level(len(clauses))

        # Calculate remaining years
        remaining_years = self._calculate_remaining_years(
            duration_years, start_date, end_date
        )

        # Get regional inflation rate
        inflation_rate = self.inflation_rates.get(currency, 0.03)

        # Calculate base risk multiplier
        base_risk_multiplier = self._calculate_base_multiplier(
            value_tier, complexity_level, duration_years
        )

        # Calculate category-specific probabilities
        probabilities = self._calculate_probabilities(
            clause_analysis, base_risk_multiplier, contract_value
        )

        profile = ContractRiskProfile(
            contract_id=contract_id,
            contract_value=contract_value,
            currency=currency,
            value_tier=value_tier,
            duration_years=duration_years,
            remaining_years=remaining_years,
            start_date=start_date,
            end_date=end_date,
            total_clauses=len(clauses),
            clause_types_found=clause_analysis["clause_types"],
            complexity_level=complexity_level,
            risk_signals_count=clause_analysis["risk_signal_count"],
            has_auto_renewal=clause_analysis["has_auto_renewal"],
            has_price_escalation=clause_analysis["has_price_escalation"],
            has_liability_cap=clause_analysis["has_liability_cap"],
            has_termination_protection=clause_analysis["has_termination_protection"],
            base_risk_multiplier=base_risk_multiplier,
            inflation_rate=inflation_rate,
            **probabilities
        )

        logger.info(
            f"Risk profile built: value_tier={value_tier}, "
            f"complexity={complexity_level}, base_multiplier={base_risk_multiplier:.2f}"
        )

        return profile

    def _analyze_clauses(self, clauses: List[Clause]) -> Dict:
        """Analyze clauses for risk indicators."""
        clause_types = set()
        risk_signal_count = 0

        has_auto_renewal = False
        has_price_escalation = False
        has_liability_cap = False
        has_termination_protection = False

        for clause in clauses:
            # Track clause types
            if clause.clause_type:
                clause_types.add(str(clause.clause_type))

            # Count risk signals
            if clause.risk_signals:
                risk_signal_count += len(clause.risk_signals)

                # Check for specific signals
                signals_lower = [s.lower() for s in clause.risk_signals]
                if "auto_renewal" in signals_lower:
                    has_auto_renewal = True
                if "price_escalation" in signals_lower:
                    has_price_escalation = True

            # Check clause text for protective provisions
            if clause.original_text:
                text_lower = clause.original_text.lower()

                if any(term in text_lower for term in ["liability cap", "limited to", "not exceed"]):
                    has_liability_cap = True

                if any(term in text_lower for term in ["termination fee", "early termination penalty"]):
                    has_termination_protection = True

                if any(term in text_lower for term in ["price adjustment", "escalation", "cpi"]):
                    has_price_escalation = True

        return {
            "clause_types": list(clause_types),
            "risk_signal_count": risk_signal_count,
            "has_auto_renewal": has_auto_renewal,
            "has_price_escalation": has_price_escalation,
            "has_liability_cap": has_liability_cap,
            "has_termination_protection": has_termination_protection,
        }

    def _get_value_tier(self, contract_value: float) -> str:
        """Determine contract value tier."""
        for tier_name, (min_val, max_val) in self.value_tiers.items():
            if min_val <= contract_value < max_val:
                return tier_name
        return "medium"

    def _get_complexity_level(self, clause_count: int) -> str:
        """Determine contract complexity based on clause count."""
        if clause_count < 10:
            return "low"
        elif clause_count <= 30:
            return "medium"
        else:
            return "high"

    def _calculate_remaining_years(
        self,
        duration_years: float,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> float:
        """Calculate remaining contract years."""
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                now = datetime.now(end.tzinfo) if end.tzinfo else datetime.now()
                remaining_days = (end - now).days
                if remaining_days > 0:
                    return remaining_days / 365.25
            except (ValueError, TypeError):
                pass

        # Fall back to duration
        return duration_years

    def _calculate_base_multiplier(
        self,
        value_tier: str,
        complexity_level: str,
        duration_years: float,
    ) -> float:
        """Calculate base risk multiplier from contract characteristics."""
        # Get value multiplier
        value_mult = self.risk_multipliers.get(f"value_{value_tier}", 1.0)

        # Get complexity multiplier
        complexity_mult = self.risk_multipliers.get(f"complexity_{complexity_level}", 1.0)

        # Get duration multiplier
        if duration_years < 1:
            duration_mult = self.risk_multipliers["duration_short"]
        elif duration_years <= 3:
            duration_mult = self.risk_multipliers["duration_medium"]
        elif duration_years <= 5:
            duration_mult = self.risk_multipliers["duration_long"]
        else:
            duration_mult = self.risk_multipliers["duration_very_long"]

        # Combine multipliers (geometric mean to avoid extreme values)
        import math
        base = math.pow(value_mult * complexity_mult * duration_mult, 1/3)

        # Cap between 0.5 and 2.0
        return max(0.5, min(2.0, base))

    def _calculate_probabilities(
        self,
        clause_analysis: Dict,
        base_multiplier: float,
        contract_value: float,
    ) -> Dict[str, float]:
        """Calculate category-specific leak probabilities."""

        # Base probabilities for each category
        base_probs = {
            "pricing": 0.08,
            "payment": 0.06,
            "renewal": 0.10,
            "termination": 0.07,
            "liability": 0.05,
            "service_level": 0.08,
        }

        # Adjust based on what's missing
        adjustments = {}

        # If no price escalation, increase pricing risk
        if not clause_analysis["has_price_escalation"]:
            adjustments["pricing"] = 1.5
            adjustments["renewal"] = 1.3

        # If no liability cap, increase liability risk significantly
        if not clause_analysis["has_liability_cap"]:
            adjustments["liability"] = 2.0

        # If no termination protection, increase termination risk
        if not clause_analysis["has_termination_protection"]:
            adjustments["termination"] = 1.4

        # If has auto-renewal without protection, increase renewal risk
        if clause_analysis["has_auto_renewal"] and not clause_analysis["has_price_escalation"]:
            adjustments["renewal"] = adjustments.get("renewal", 1.0) * 1.5

        # Calculate final probabilities
        result = {}
        for category, base_prob in base_probs.items():
            adjustment = adjustments.get(category, 1.0)
            final_prob = base_prob * base_multiplier * adjustment

            # Cap between 0.01 (1%) and 0.30 (30%)
            final_prob = max(0.01, min(0.30, final_prob))

            result[f"{category}_leak_probability"] = round(final_prob, 4)

        return result
