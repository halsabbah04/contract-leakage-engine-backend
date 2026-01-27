"""AI-powered leakage detection service using Azure OpenAI GPT 5.2."""

import json
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from ..db import ClauseRepository, get_cosmos_client
from ..models.finding import Assumptions, DetectionMethod, EstimatedImpact, LeakageCategory, LeakageFinding, Severity
from ..utils.config import get_settings
from ..utils.exceptions import AIDetectionError
from ..utils.logging import setup_logging
from .rag_service import RAGService

logger = setup_logging(__name__)
settings = get_settings()


class AIDetectionService:
    """Service for AI-powered leakage detection using GPT 5.2 and RAG."""

    def __init__(self):
        """Initialize AI detection service with Azure OpenAI GPT 5.2."""
        try:
            logger.info("Initializing AI detection service with GPT 5.2...")

            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )

            self.model_deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME
            self.rag_service = RAGService()

            logger.info(f"AI detection service initialized: model={self.model_deployment}")

        except Exception as e:
            logger.error(f"Failed to initialize AI detection service: {str(e)}")
            raise AIDetectionError(f"AI detection initialization failed: {str(e)}")

    def detect_leakage(self, contract_id: str, contract_metadata: Optional[Dict] = None) -> List[LeakageFinding]:
        """
        Detect commercial leakage using AI-powered analysis with RAG.

        Uses GPT 5.2 for:
        - Complex pattern detection that rules cannot catch
        - Contextual understanding across multiple clauses
        - Implicit risk identification
        - Cross-clause relationship analysis

        Args:
            contract_id: Contract identifier
            contract_metadata: Optional contract metadata

        Returns:
            List of AI-detected leakage findings
        """
        try:
            logger.info(f"Running AI leakage detection for contract {contract_id}")

            contract_metadata = contract_metadata or {}

            # Step 1: Index contract for RAG (if not already indexed)
            logger.info("Step 1: Ensuring RAG index is ready...")
            self.rag_service.index_contract_clauses(contract_id)

            # Step 2: Build RAG context with targeted queries
            logger.info("Step 2: Building RAG context...")
            rag_context = self._build_leakage_detection_context(contract_id)

            if not rag_context["retrieved_clauses"]:
                logger.warning("No clauses retrieved for AI analysis")
                return []

            # Step 3: Run AI analysis with GPT 5.2
            logger.info("Step 3: Running GPT 5.2 analysis...")
            ai_findings = self._analyze_with_gpt(
                contract_id=contract_id,
                rag_context=rag_context,
                contract_metadata=contract_metadata,
            )

            logger.info(f"AI detection complete: {len(ai_findings)} findings")

            return ai_findings

        except Exception as e:
            logger.error(f"AI leakage detection failed: {str(e)}")
            raise AIDetectionError(f"AI detection failed: {str(e)}")

    def _build_leakage_detection_context(self, contract_id: str) -> Dict[str, Any]:
        """
        Build RAG context focused on leakage detection.

        Uses targeted queries to retrieve relevant clauses.
        Reduced to 3 key queries to stay within timeout limits.
        """
        # Leakage detection queries - reduced to 3 most important patterns
        # This keeps AI detection fast while still catching key issues
        queries = [
            "pricing terms, payment conditions, fees, and financial obligations",
            "termination, renewal, liability caps, and indemnification provisions",
            "service levels, warranties, penalties, and performance guarantees",
        ]

        return self.rag_service.build_rag_context(
            queries=queries,
            contract_id=contract_id,
            max_clauses_per_query=5,
            max_total_clauses=12,
        )

    def _analyze_with_gpt(
        self, contract_id: str, rag_context: Dict[str, Any], contract_metadata: Dict
    ) -> List[LeakageFinding]:
        """
        Analyze contract using GPT 5.2 with RAG context.
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt()

            # Build user prompt with RAG context
            user_prompt = self._build_user_prompt(
                contract_id=contract_id,
                rag_context=rag_context,
                contract_metadata=contract_metadata,
            )

            # Call GPT 5.2
            logger.info("Calling GPT 5.2 for leakage analysis...")

            response = self.client.chat.completions.create(
                model=self.model_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Low temperature for consistent, focused analysis
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            # Parse response
            response_text = response.choices[0].message.content
            analysis_result = json.loads(response_text)

            # Convert to LeakageFinding objects
            findings = self._parse_ai_findings(
                contract_id=contract_id,
                analysis_result=analysis_result,
                contract_metadata=contract_metadata,
            )

            logger.info(f"GPT 5.2 identified {len(findings)} leakage issues")

            return findings

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"GPT analysis failed: {str(e)}")
            raise AIDetectionError(f"GPT analysis failed: {str(e)}")

    def _build_system_prompt(self) -> str:
        """Build system prompt for GPT 5.2."""
        return """You are an expert contract analyst specializing in commercial leakage detection.

Your role is to identify potential revenue leakage, unfavorable terms, and financial risks in business
contracts that may not be caught by simple rule-based systems.

Focus on:
1. **Implicit risks** - Issues not explicitly stated but implied by clause combinations
2. **Cross-clause conflicts** - Contradictions or gaps between different contract sections
3. **Complex patterns** - Sophisticated leakage mechanisms requiring contextual understanding
4. **Missing protections** - Absent clauses that create risk (e.g., no force majeure, inadequate IP protection)
5. **Unfair allocations** - One-sided terms that disadvantage one party
6. **Hidden escalations** - Terms that could lead to unexpected cost increases
7. **Weak enforcement** - Terms without proper remedies or consequences

**IMPORTANT CONSTRAINTS:**
- This is advisory-only, NOT legal advice
- Focus on financial and commercial risks, not legal compliance
- Only flag genuine issues with clear business impact
- Provide specific evidence from the contract text
- Quantify impact when possible
- Avoid duplicating obvious rule-based findings

**Output Format:**
Return a JSON object with this structure:
{
  "findings": [
    {
      "finding_id": "unique_id",
      "category": "pricing|payment|renewal|termination|service_level|liability|penalty|other",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "title": "Brief title",
      "explanation": "Detailed explanation of the issue",
      "business_impact": "Specific business impact",
      "affected_clause_ids": ["clause_id_1", "clause_id_2"],
      "recommended_action": "Specific recommendation",
      "estimated_impact_value": 0.0 (optional, numeric value if quantifiable),
      "estimated_impact_currency": "USD" (optional),
      "impact_calculation_method": "description of how impact was calculated" (optional),
      "assumptions": {
        "key": "value"
      }
    }
  ]
}"""

    def _build_user_prompt(self, contract_id: str, rag_context: Dict[str, Any], contract_metadata: Dict) -> str:
        """Build user prompt with RAG context."""

        # Format contract metadata
        metadata_text = f"""
**Contract Metadata:**
- Contract ID: {contract_id}
- Contract Value: ${contract_metadata.get('contract_value', 'Unknown'):,}
- Duration: {contract_metadata.get('duration_years', 'Unknown')} years
- Contract Type: {contract_metadata.get('contract_type', 'Unknown')}
"""

        # Format retrieved clauses
        clauses_text = rag_context["context_summary"]

        prompt = f"""Analyze the following contract for commercial leakage and financial risks.

{metadata_text}

**Retrieved Relevant Clauses:**
{clauses_text}

**Your Task:**
Identify any commercial leakage, unfavorable terms, or financial risks in these clauses. Focus on:
- Complex patterns that simple rules cannot detect
- Cross-clause relationships and conflicts
- Implicit risks and missing protections
- Contextual issues requiring deep understanding

Provide your analysis in the specified JSON format. Include only genuine issues with clear business impact."""

        return prompt

    def _parse_ai_findings(
        self, contract_id: str, analysis_result: Dict, contract_metadata: Dict
    ) -> List[LeakageFinding]:
        """Parse GPT response into LeakageFinding objects."""
        findings = []

        for item in analysis_result.get("findings", []):
            try:
                # Map category
                category = self._map_category(item.get("category", "other"))

                # Map severity
                severity = self._map_severity(item.get("severity", "medium"))

                # Build estimated impact
                estimated_impact = EstimatedImpact(
                    value=item.get("estimated_impact_value", 0.0),
                    currency=item.get("estimated_impact_currency", "USD"),
                    value_min=None,
                    value_max=None,
                    calculation_method=item.get("impact_calculation_method", "ai_estimated"),
                    confidence=item.get("confidence", 0.5),
                )

                # Build assumptions
                assumptions = Assumptions(
                    inflation_rate=None,
                    remaining_years=None,
                    annual_volume=None,
                    probability=None,
                    custom_parameters=item.get("assumptions", {}),
                )

                # Create finding
                finding = LeakageFinding(
                    id=f"ai_{contract_id}_{item.get('finding_id', 'unknown')}",
                    contract_id=contract_id,
                    partition_key=contract_id,
                    clause_ids=item.get("affected_clause_ids", []),
                    leakage_category=category,
                    risk_type=item.get("title", "AI-detected risk"),
                    detection_method=DetectionMethod.AI,
                    rule_id=None,
                    severity=severity,
                    confidence=item.get("confidence", 0.7),
                    explanation=item.get("explanation", ""),
                    business_impact_summary=item.get("business_impact", ""),
                    recommended_action=item.get("recommended_action", ""),
                    assumptions=assumptions,
                    estimated_impact=estimated_impact,
                    embedding=None,
                    user_notes=None,
                )

                findings.append(finding)

            except Exception as e:
                logger.error(f"Failed to parse AI finding: {str(e)}")
                continue

        return findings

    def _map_category(self, category_str: str) -> LeakageCategory:
        """Map category string to enum."""
        mapping = {
            "pricing": LeakageCategory.PRICING,
            "payment": LeakageCategory.PAYMENT_TERMS,
            "renewal": LeakageCategory.RENEWAL,
            "termination": LeakageCategory.TERMINATION,
            "service_level": LeakageCategory.SERVICE_CREDIT,
            "liability": LeakageCategory.LIABILITY_CAP,
            "penalty": LeakageCategory.PENALTY,
        }
        return mapping.get(category_str.lower(), LeakageCategory.OTHER)

    def _map_severity(self, severity_str: str) -> Severity:
        """Map severity string to enum."""
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        return mapping.get(severity_str.lower(), Severity.MEDIUM)

    def analyze_specific_clauses(self, contract_id: str, clause_ids: List[str], analysis_focus: str) -> Dict[str, Any]:
        """
        Analyze specific clauses with a particular focus.

        Useful for:
        - Deep-dive analysis of flagged clauses
        - User-requested clause examination
        - Follow-up analysis

        Args:
            contract_id: Contract identifier
            clause_ids: List of clause IDs to analyze
            analysis_focus: What to focus on (e.g., "pricing risk", "termination fairness")

        Returns:
            Analysis results dictionary
        """
        try:
            logger.info(f"Analyzing {len(clause_ids)} specific clauses")

            # Get clauses
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)

            clauses = []
            for clause_id in clause_ids:
                clause = clause_repo.read(clause_id, contract_id)
                if clause:
                    clauses.append(clause)

            if not clauses:
                return {"analysis": "No clauses found", "findings": []}

            # Build context
            clauses_text = "\n\n".join(
                [f"[{c.clause_type}] {c.normalized_summary or c.original_text[:500]}" for c in clauses]
            )

            # Build prompt
            prompt = f"""Analyze these specific contract clauses with focus on: {analysis_focus}

**Clauses:**
{clauses_text}

Provide detailed analysis in JSON format with findings array."""

            # Call GPT 5.2
            response = self.client.chat.completions.create(
                model=self.model_deployment,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            logger.info("Specific clause analysis complete")

            return result

        except Exception as e:
            logger.error(f"Specific clause analysis failed: {str(e)}")
            return {"error": str(e), "findings": []}
