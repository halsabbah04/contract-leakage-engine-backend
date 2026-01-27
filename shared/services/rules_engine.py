"""Rules engine for detecting commercial leakage based on YAML rules."""

import uuid
from typing import Dict, List, Optional

import yaml

from ..models.clause import Clause
from ..models.finding import Assumptions, DetectionMethod, EstimatedImpact, LeakageCategory, LeakageFinding, Severity
from ..utils.config import get_settings
from ..utils.exceptions import RulesEngineError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings()


class RulesEngine:
    """Engine for executing leakage detection rules."""

    def __init__(self, rules_file_path: Optional[str] = None):
        """
        Initialize rules engine.

        Args:
            rules_file_path: Path to YAML rules file (optional)
        """
        if rules_file_path is None:
            rules_file_path = settings.RULES_FILE_PATH

        try:
            logger.info(f"Loading rules from: {rules_file_path}")
            with open(rules_file_path, "r", encoding="utf-8") as f:
                rules_data = yaml.safe_load(f)

            self.rules = rules_data.get("rules", [])
            self.config = rules_data.get("config", {})

            # Filter enabled rules
            self.rules = [r for r in self.rules if r.get("enabled", True)]

            logger.info(f"Loaded {len(self.rules)} enabled rules")

        except FileNotFoundError:
            logger.error(f"Rules file not found: {rules_file_path}")
            raise RulesEngineError(f"Rules file not found: {rules_file_path}")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in rules file: {str(e)}")
            raise RulesEngineError(f"Invalid rules file: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load rules: {str(e)}")
            raise RulesEngineError(f"Failed to load rules: {str(e)}")

    def detect_leakage(
        self,
        contract_id: str,
        clauses: List[Clause],
        contract_metadata: Optional[Dict] = None,
    ) -> List[LeakageFinding]:
        """
        Run all rules against contract clauses.

        Args:
            contract_id: Contract identifier
            clauses: List of extracted clauses
            contract_metadata: Optional contract metadata (value, duration, etc.)

        Returns:
            List of detected leakage findings
        """
        logger.info(f"Running rules engine on contract {contract_id} ({len(clauses)} clauses)")

        findings = []
        contract_metadata = contract_metadata or {}

        for rule in self.rules:
            try:
                rule_findings = self._execute_rule(rule, contract_id, clauses, contract_metadata)
                findings.extend(rule_findings)
            except Exception as e:
                logger.error(f"Error executing rule {rule.get('rule_id')}: {str(e)}")
                # Continue with other rules

        logger.info(f"Rules engine detected {len(findings)} potential leakage issues")

        return findings

    def _execute_rule(
        self,
        rule: Dict,
        contract_id: str,
        clauses: List[Clause],
        contract_metadata: Dict,
    ) -> List[LeakageFinding]:
        """
        Execute a single rule against clauses.

        Args:
            rule: Rule definition
            contract_id: Contract identifier
            clauses: Contract clauses
            contract_metadata: Contract metadata

        Returns:
            List of findings (if rule matches) - ONE finding per rule
        """
        rule_id = rule.get("rule_id")
        logger.debug(f"Executing rule: {rule_id}")

        findings = []
        conditions = rule.get("conditions", {})

        # Find matching clauses
        matching_clauses = self._find_matching_clauses(clauses, conditions, contract_metadata)

        if matching_clauses:
            logger.info(f"Rule {rule_id} matched {len(matching_clauses)} clauses")

            # Create ONE finding per rule (aggregate all matching clauses)
            # Use the first matching clause as the primary reference
            finding = self._create_finding(
                rule, contract_id, matching_clauses[0], contract_metadata, all_matching_clauses=matching_clauses
            )
            findings.append(finding)

        return findings

    def _find_matching_clauses(self, clauses: List[Clause], conditions: Dict, contract_metadata: Dict) -> List[Clause]:
        """
        Find clauses matching rule conditions.

        Args:
            clauses: All clauses
            conditions: Rule conditions
            contract_metadata: Contract metadata

        Returns:
            List of matching clauses
        """
        matching = []

        for clause in clauses:
            if self._clause_matches_conditions(clause, conditions, contract_metadata):
                matching.append(clause)

        return matching

    def _clause_matches_conditions(self, clause: Clause, conditions: Dict, contract_metadata: Dict) -> bool:
        """
        Check if a clause matches rule conditions.

        Args:
            clause: Clause to check
            conditions: Rule conditions
            contract_metadata: Contract metadata

        Returns:
            True if clause matches all conditions
        """
        # Check clause type
        if "clause_type" in conditions:
            if clause.clause_type != conditions["clause_type"]:
                return False

        # Check risk signals
        if "risk_signals" in conditions:
            required_signals = conditions["risk_signals"]
            if not any(signal in clause.risk_signals for signal in required_signals):
                return False

        # Check keywords (contains)
        if "contains" in conditions:
            keywords = conditions["contains"]
            if isinstance(keywords, str):
                keywords = [keywords]

            clause_text_lower = clause.original_text.lower()
            if not any(kw.lower() in clause_text_lower for kw in keywords):
                return False

        # Check keywords (not_contains)
        if "not_contains" in conditions:
            keywords = conditions["not_contains"]
            if isinstance(keywords, str):
                keywords = [keywords]

            clause_text_lower = clause.original_text.lower()
            if any(kw.lower() in clause_text_lower for kw in keywords):
                return False

        # Check keywords (must contain all)
        if "keywords" in conditions:
            keywords = conditions["keywords"]
            clause_text_lower = clause.original_text.lower()
            if not all(kw.lower() in clause_text_lower for kw in keywords):
                return False

        # Check contract-level conditions
        if "min_contract_years" in conditions:
            contract_years = contract_metadata.get("duration_years", 0)
            if contract_years < conditions["min_contract_years"]:
                return False

        return True

    def _create_finding(
        self,
        rule: Dict,
        contract_id: str,
        clause: Clause,
        contract_metadata: Dict,
        all_matching_clauses: Optional[List[Clause]] = None,
    ) -> LeakageFinding:
        """
        Create a LeakageFinding from a matched rule.

        Args:
            rule: Rule definition
            contract_id: Contract identifier
            clause: Primary matched clause (for impact calculation reference)
            contract_metadata: Contract metadata
            all_matching_clauses: All clauses that matched this rule

        Returns:
            LeakageFinding object
        """
        # Generate finding ID
        finding_id = f"finding_{contract_id}_{uuid.uuid4().hex[:8]}"

        # Map category
        category = self._map_category(rule.get("category", "other"))

        # Map severity
        severity = self._map_severity(rule.get("severity", "medium"))

        # Calculate impact
        impact_calc = rule.get("impact_calculation", {})
        estimated_impact, assumptions = self._calculate_impact(impact_calc, contract_metadata, clause)

        # Build explanation
        explanation = rule.get("explanation", "").strip()
        if rule.get("business_impact"):
            explanation += f"\n\nBusiness Impact: {rule.get('business_impact')}"

        # Collect all matching clause IDs
        if all_matching_clauses:
            clause_ids = [c.id for c in all_matching_clauses]
        else:
            clause_ids = [clause.id]

        # Create finding
        finding = LeakageFinding(
            id=finding_id,
            contract_id=contract_id,
            partition_key=contract_id,
            clause_ids=clause_ids,
            leakage_category=category,
            risk_type=rule.get("rule_id", "unknown"),
            detection_method=DetectionMethod.RULE,
            rule_id=rule.get("rule_id"),
            severity=severity,
            confidence=0.95,  # Rules have high confidence
            explanation=explanation,
            business_impact_summary=rule.get("business_impact"),
            recommended_action=rule.get("recommended_action"),
            assumptions=assumptions,
            estimated_impact=estimated_impact,
            embedding=None,
            user_notes=None,
        )

        logger.debug(f"Created finding: {finding_id} ({severity}) with {len(clause_ids)} clauses")

        return finding

    def _map_category(self, category_str: str) -> LeakageCategory:
        """Map rule category string to LeakageCategory enum."""
        mapping = {
            "pricing": LeakageCategory.PRICING,
            "payment": LeakageCategory.PAYMENT_TERMS,
            "renewal": LeakageCategory.RENEWAL,
            "auto_renewal": LeakageCategory.AUTO_RENEWAL,
            "termination": LeakageCategory.TERMINATION,
            "service_level": LeakageCategory.SERVICE_CREDIT,
            "liability": LeakageCategory.LIABILITY_CAP,
            "penalties": LeakageCategory.PENALTY,
            "volume_commitment": LeakageCategory.VOLUME_DISCOUNT,
            "delivery": LeakageCategory.DELIVERY,
        }

        return mapping.get(category_str, LeakageCategory.OTHER)

    def _map_severity(self, severity_str: str) -> Severity:
        """Map rule severity string to Severity enum."""
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }

        return mapping.get(severity_str.lower(), Severity.MEDIUM)

    def _calculate_impact(
        self, impact_calc: Dict, contract_metadata: Dict, clause: Clause
    ) -> tuple[EstimatedImpact, Assumptions]:
        """
        Calculate estimated financial impact based on rule parameters.

        Args:
            impact_calc: Impact calculation config from rule
            contract_metadata: Contract metadata
            clause: Matched clause

        Returns:
            Tuple of (EstimatedImpact, Assumptions)
        """
        method = impact_calc.get("method", "none")
        parameters = impact_calc.get("parameters", {})

        contract_value = contract_metadata.get("contract_value", 0)
        duration_years = contract_metadata.get("duration_years", 1)

        # Default assumptions
        assumptions = Assumptions(
            inflation_rate=self.config.get("impact_defaults", {}).get("inflation_rate", 0.03),
            remaining_years=duration_years,
            annual_volume=None,
            probability=None,
        )

        estimated_impact = EstimatedImpact(
            currency="USD",
            value=0.0,
            value_min=None,
            value_max=None,
            calculation_method=None,
            confidence=0.0,
        )

        # Calculate based on method
        if method == "inflation_based":
            inflation_rate = parameters.get("inflation_rate", 0.03)
            remaining_years = parameters.get("time_period", duration_years)

            # Calculate cumulative loss from inflation
            impact_value = contract_value * inflation_rate * remaining_years

            assumptions.inflation_rate = inflation_rate
            assumptions.remaining_years = remaining_years

            estimated_impact.value = impact_value
            estimated_impact.calculation_method = "inflation_based"

        elif method == "percentage_of_value":
            risk_percentage = parameters.get("risk_percentage", 0.10)
            impact_value = contract_value * risk_percentage

            assumptions.probability = risk_percentage

            estimated_impact.value = impact_value
            estimated_impact.calculation_method = "percentage_of_value"

        elif method == "renewal_based":
            expected_increase = parameters.get("expected_increase", 0.05)
            renewal_probability = parameters.get("renewal_probability", 0.8)

            impact_value = contract_value * expected_increase * renewal_probability

            assumptions.probability = renewal_probability
            assumptions.custom_parameters = {"expected_increase": expected_increase}

            estimated_impact.value = impact_value
            estimated_impact.calculation_method = "renewal_based"

        elif method == "opportunity_cost":
            months_at_risk = parameters.get("months_at_risk", 6)
            monthly_value = contract_value / 12 if contract_value else 0

            impact_value = monthly_value * months_at_risk

            assumptions.custom_parameters = {"months_at_risk": months_at_risk}

            estimated_impact.value = impact_value
            estimated_impact.calculation_method = "opportunity_cost"

        # Set confidence based on data availability
        if contract_value > 0:
            estimated_impact.confidence = 0.7
        else:
            estimated_impact.confidence = 0.3

        return estimated_impact, assumptions

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Get rule definition by ID."""
        for rule in self.rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None

    def get_rules_by_category(self, category: str) -> List[Dict]:
        """Get all rules in a category."""
        return [r for r in self.rules if r.get("category") == category]

    def get_enabled_rules_count(self) -> int:
        """Get count of enabled rules."""
        return len(self.rules)
