"""Agent registry for registering and managing analysis agents."""

from typing import Any, Dict

from ..utils.logging import setup_logging
from .agent_orchestrator import AgentPhase, get_orchestrator

logger = setup_logging(__name__)


async def execute_rules_agent(context: Dict[str, Any]) -> Any:
    """
    Execute rules engine agent.

    Expected context keys:
    - contract_id: str
    - clauses: List[Clause]
    - contract_metadata: Dict[str, Any]
    - risk_profile: RiskProfile
    """
    from ..services.rules_engine import RulesEngine

    contract_id = context["contract_id"]
    clauses = context["clauses"]
    contract_metadata = context["contract_metadata"]
    risk_profile = context.get("risk_profile")

    rules_engine = RulesEngine()
    findings = rules_engine.detect_leakage(contract_id, clauses, contract_metadata, risk_profile)

    logger.info(f"Rules engine detected {len(findings)} potential issues")
    return {"findings": findings, "count": len(findings)}


async def execute_ai_detection_agent(context: Dict[str, Any]) -> Any:
    """
    Execute AI detection agent (GPT-based leakage detection).

    Expected context keys:
    - contract_id: str
    - contract_metadata: Dict[str, Any]
    - clause_count: int
    """
    from ..services.ai_detection_service import AIDetectionService

    contract_id = context["contract_id"]
    contract_metadata = context["contract_metadata"]
    clause_count = context.get("clause_count", 0)

    if clause_count > 50:
        logger.warning(f"Skipping AI detection: {clause_count} clauses exceeds limit of 50")
        return {"findings": [], "count": 0, "skipped": True}

    ai_service = AIDetectionService()
    findings = ai_service.detect_leakage(contract_id, contract_metadata)

    logger.info(f"AI detection found {len(findings)} findings")
    return {"findings": findings, "count": len(findings)}


async def execute_obligation_agent(context: Dict[str, Any]) -> Any:
    """
    Execute obligation extraction agent.

    Expected context keys:
    - contract_id: str
    - contract: Contract
    - clauses: List[Clause]
    - contract_metadata: Dict[str, Any]
    """
    from .obligation_agent import ObligationExtractionAgent
    from .base_agent import AgentStatus

    contract_id = context["contract_id"]
    contract = context.get("contract")
    clauses = context["clauses"]
    contract_metadata = context["contract_metadata"]

    # Extract party names from contract and clauses
    party_names = set()
    if contract and contract.counterparty:
        party_names.add(contract.counterparty)

    for clause in clauses:
        if clause.entities and clause.entities.parties:
            party_names.update(clause.entities.parties)

    # Create enriched metadata
    enriched_metadata = {
        **contract_metadata,
        "party_names": list(party_names),
        "counterparty": contract.counterparty if contract else None
    }

    logger.info(f"[OBLIGATION] Metadata: currency={contract_metadata.get('contract_currency')}, parties={list(party_names)}")

    obligation_agent = ObligationExtractionAgent(contract_id, contract, enriched_metadata)
    agent_result = await obligation_agent.run()

    if agent_result.status in [AgentStatus.COMPLETED, AgentStatus.PARTIAL] and agent_result.data:
        obligations_count = agent_result.data.summary.total_obligations
        logger.info(f"[OBLIGATION] Extracted {obligations_count} obligations")
        return {
            "count": obligations_count,
            "summary": agent_result.data.summary,
            "status": agent_result.status.value
        }
    else:
        logger.warning(f"[OBLIGATION] Extraction completed with issues")
        return {"count": 0, "error": agent_result.error}


def register_standard_agents():
    """Register all standard analysis agents."""
    orchestrator = get_orchestrator()

    # Phase 2: ANALYZE - Leakage Detection & Obligation Extraction
    orchestrator.register_agent(
        agent_id="rules_engine",
        agent_name="Rules Engine",
        phase=AgentPhase.ANALYZE,
        execute_func=execute_rules_agent,
        optional=False,
        timeout=60.0,
        description="YAML-based rule detection for common leakage patterns"
    )

    orchestrator.register_agent(
        agent_id="ai_detection",
        agent_name="AI Detection",
        phase=AgentPhase.ANALYZE,
        execute_func=execute_ai_detection_agent,
        optional=True,  # Optional because it's skipped for large contracts
        timeout=120.0,
        description="GPT-5.2 based leakage detection with RAG"
    )

    # Phase 3: ENRICH - Contextual Analysis
    orchestrator.register_agent(
        agent_id="obligation_extraction",
        agent_name="Obligation Extraction",
        phase=AgentPhase.ENRICH,
        execute_func=execute_obligation_agent,
        optional=True,  # Optional - failure doesn't stop analysis
        timeout=180.0,
        description="Extract contractual obligations with dates and responsible parties"
    )

    logger.info("Standard agents registered successfully")


# TODO: Register Phase 2 agents (to be implemented)
# def register_phase2_agents():
#     """Register Phase 2 agents (Comparison, Benchmark, Compliance)."""
#     orchestrator = get_orchestrator()
#
#     orchestrator.register_agent(
#         agent_id="contract_comparison",
#         agent_name="Contract Comparison",
#         phase=AgentPhase.ENRICH,
#         execute_func=execute_contract_comparison_agent,
#         optional=True,
#         timeout=90.0,
#         description="Compare contract versions and identify deviations from templates"
#     )
#
#     orchestrator.register_agent(
#         agent_id="benchmark",
#         agent_name="Benchmark Agent",
#         phase=AgentPhase.ENRICH,
#         execute_func=execute_benchmark_agent,
#         optional=True,
#         timeout=120.0,
#         description="Compare contract terms to industry standards and benchmarks"
#     )
#
#     orchestrator.register_agent(
#         agent_id="compliance",
#         agent_name="Compliance & Regulatory",
#         phase=AgentPhase.ENRICH,
#         execute_func=execute_compliance_agent,
#         optional=True,
#         timeout=120.0,
#         description="Check compliance with GDPR, HIPAA, SOX, and other regulations"
#     )
