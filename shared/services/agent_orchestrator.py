"""Agent Orchestrator service for coordinating AI agent execution."""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from ..agents import AgentResult, AgentStatus, BaseAgent, ObligationExtractionAgent
from ..db import ContractRepository, get_cosmos_client
from ..models.contract import Contract
from ..utils.logging import setup_logging

logger = setup_logging(__name__)


class AgentType(str, Enum):
    """Available agent types."""

    OBLIGATION = "obligation"
    # Future agents:
    # PARTY_INTELLIGENCE = "party_intelligence"
    # BENCHMARK = "benchmark"
    # COMPLIANCE = "compliance"
    # CONTRACT_COMPARISON = "contract_comparison"
    # RISK_FORECAST = "risk_forecast"
    # NEGOTIATION = "negotiation"


class OrchestratorConfig(BaseModel):
    """Configuration for agent orchestration."""

    agents_to_run: List[AgentType] = Field(
        default_factory=lambda: [AgentType.OBLIGATION],
        description="List of agents to run",
    )
    run_parallel: bool = Field(default=True, description="Whether to run agents in parallel")
    continue_on_failure: bool = Field(default=True, description="Whether to continue if an agent fails")
    timeout_seconds: int = Field(default=300, description="Timeout for agent execution")


class OrchestrationResult(BaseModel):
    """Result of orchestrated agent execution."""

    contract_id: str = Field(..., description="Contract ID processed")
    started_at: datetime = Field(..., description="Orchestration start time")
    completed_at: datetime = Field(..., description="Orchestration end time")
    duration_ms: float = Field(..., description="Total duration in milliseconds")

    # Agent results
    agent_results: Dict[str, Any] = Field(default_factory=dict, description="Results by agent type")
    agent_statuses: Dict[str, str] = Field(default_factory=dict, description="Status by agent type")

    # Summary
    total_agents: int = Field(default=0, description="Total agents run")
    successful_agents: int = Field(default=0, description="Number of successful agents")
    failed_agents: int = Field(default=0, description="Number of failed agents")
    partial_agents: int = Field(default=0, description="Number of agents with partial results")

    # Errors
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class AgentOrchestrator:
    """
    Orchestrator for coordinating AI agent execution.

    Supports:
    - Parallel agent execution
    - Sequential agent execution
    - Graceful degradation on failures
    - Result aggregation
    """

    # Registry of agent types to their implementation classes
    AGENT_REGISTRY: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.OBLIGATION: ObligationExtractionAgent,
    }

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Optional orchestration configuration
        """
        self.config = config or OrchestratorConfig()
        self._contract_repo: Optional[ContractRepository] = None

    @property
    def contract_repo(self) -> ContractRepository:
        """Get or create contract repository."""
        if self._contract_repo is None:
            cosmos_client = get_cosmos_client()
            self._contract_repo = ContractRepository(cosmos_client.contracts_container)
        return self._contract_repo

    async def run_agents(
        self,
        contract_id: str,
        agent_types: Optional[List[AgentType]] = None,
    ) -> OrchestrationResult:
        """
        Run specified agents for a contract.

        Args:
            contract_id: Contract to process
            agent_types: Optional list of agents to run (defaults to config)

        Returns:
            OrchestrationResult with all agent results
        """
        started_at = datetime.utcnow()
        agents_to_run = agent_types or self.config.agents_to_run

        logger.info(
            f"[Orchestrator] Starting orchestration for contract {contract_id} "
            f"with agents: {[a.value for a in agents_to_run]}"
        )

        # Get contract metadata
        contract = self._get_contract(contract_id)

        # Initialize result
        result = OrchestrationResult(
            contract_id=contract_id,
            started_at=started_at,
            completed_at=started_at,  # Will be updated
            duration_ms=0,
            total_agents=len(agents_to_run),
        )

        try:
            if self.config.run_parallel:
                agent_results = await self._run_parallel(contract_id, contract, agents_to_run)
            else:
                agent_results = await self._run_sequential(contract_id, contract, agents_to_run)

            # Process results
            for agent_type, agent_result in agent_results.items():
                result.agent_results[agent_type] = (
                    agent_result.data.model_dump() if agent_result.data else None
                )
                result.agent_statuses[agent_type] = agent_result.status

                if agent_result.status == AgentStatus.COMPLETED:
                    result.successful_agents += 1
                elif agent_result.status == AgentStatus.PARTIAL:
                    result.partial_agents += 1
                    result.warnings.extend(agent_result.warnings)
                elif agent_result.status == AgentStatus.FAILED:
                    result.failed_agents += 1
                    if agent_result.error:
                        result.errors.append(f"{agent_type}: {agent_result.error}")

        except Exception as e:
            logger.error(f"[Orchestrator] Critical failure: {str(e)}")
            result.errors.append(f"Orchestration failed: {str(e)}")

        # Finalize result
        result.completed_at = datetime.utcnow()
        result.duration_ms = (result.completed_at - started_at).total_seconds() * 1000

        logger.info(
            f"[Orchestrator] Completed: {result.successful_agents}/{result.total_agents} successful, "
            f"{result.failed_agents} failed, {result.duration_ms:.0f}ms"
        )

        return result

    async def _run_parallel(
        self,
        contract_id: str,
        contract: Optional[Contract],
        agent_types: List[AgentType],
    ) -> Dict[str, AgentResult]:
        """
        Run agents in parallel.

        Args:
            contract_id: Contract ID
            contract: Contract object
            agent_types: Agents to run

        Returns:
            Dictionary of agent type to result
        """
        logger.info(f"[Orchestrator] Running {len(agent_types)} agents in parallel")

        # Create tasks
        tasks = []
        agent_type_map = {}

        for agent_type in agent_types:
            agent = self._create_agent(agent_type, contract_id, contract)
            if agent:
                task = asyncio.create_task(
                    asyncio.wait_for(
                        agent.run(),
                        timeout=self.config.timeout_seconds,
                    )
                )
                tasks.append(task)
                agent_type_map[id(task)] = agent_type.value

        # Run all tasks
        results = {}

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)

            for task, result in zip(tasks, completed):
                agent_type = agent_type_map[id(task)]

                if isinstance(result, asyncio.TimeoutError):
                    logger.error(f"[Orchestrator] Agent {agent_type} timed out")
                    results[agent_type] = self._create_timeout_result(agent_type, contract_id)
                elif isinstance(result, Exception):
                    logger.error(f"[Orchestrator] Agent {agent_type} failed: {str(result)}")
                    results[agent_type] = self._create_error_result(agent_type, contract_id, result)
                else:
                    results[agent_type] = result

        return results

    async def _run_sequential(
        self,
        contract_id: str,
        contract: Optional[Contract],
        agent_types: List[AgentType],
    ) -> Dict[str, AgentResult]:
        """
        Run agents sequentially.

        Args:
            contract_id: Contract ID
            contract: Contract object
            agent_types: Agents to run

        Returns:
            Dictionary of agent type to result
        """
        logger.info(f"[Orchestrator] Running {len(agent_types)} agents sequentially")

        results = {}

        for agent_type in agent_types:
            try:
                agent = self._create_agent(agent_type, contract_id, contract)
                if agent:
                    result = await asyncio.wait_for(
                        agent.run(),
                        timeout=self.config.timeout_seconds,
                    )
                    results[agent_type.value] = result
                else:
                    logger.warning(f"[Orchestrator] Unknown agent type: {agent_type}")

            except asyncio.TimeoutError:
                logger.error(f"[Orchestrator] Agent {agent_type} timed out")
                results[agent_type.value] = self._create_timeout_result(agent_type.value, contract_id)

                if not self.config.continue_on_failure:
                    break

            except Exception as e:
                logger.error(f"[Orchestrator] Agent {agent_type} failed: {str(e)}")
                results[agent_type.value] = self._create_error_result(agent_type.value, contract_id, e)

                if not self.config.continue_on_failure:
                    break

        return results

    def _create_agent(
        self,
        agent_type: AgentType,
        contract_id: str,
        contract: Optional[Contract],
    ) -> Optional[BaseAgent]:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            contract_id: Contract ID
            contract: Contract object

        Returns:
            Agent instance or None if type not supported
        """
        agent_class = self.AGENT_REGISTRY.get(agent_type)

        if not agent_class:
            logger.warning(f"[Orchestrator] No implementation for agent type: {agent_type}")
            return None

        # Create agent with appropriate constructor
        if agent_type == AgentType.OBLIGATION:
            return agent_class(contract_id=contract_id, contract=contract)
        else:
            return agent_class(contract_id=contract_id)

    def _get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get contract metadata."""
        try:
            return self.contract_repo.read(contract_id, contract_id)
        except Exception as e:
            logger.warning(f"[Orchestrator] Could not get contract metadata: {str(e)}")
            return None

    def _create_timeout_result(self, agent_name: str, contract_id: str) -> AgentResult:
        """Create a timeout result."""
        return AgentResult(
            agent_name=agent_name,
            status=AgentStatus.FAILED,
            contract_id=contract_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error="Agent execution timed out",
        )

    def _create_error_result(self, agent_name: str, contract_id: str, error: Exception) -> AgentResult:
        """Create an error result."""
        return AgentResult(
            agent_name=agent_name,
            status=AgentStatus.FAILED,
            contract_id=contract_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error=str(error),
        )

    async def run_obligation_agent(self, contract_id: str) -> AgentResult:
        """
        Convenience method to run just the obligation extraction agent.

        Args:
            contract_id: Contract to process

        Returns:
            AgentResult from the obligation agent
        """
        result = await self.run_agents(contract_id, [AgentType.OBLIGATION])
        return result.agent_results.get(AgentType.OBLIGATION.value)


# Singleton orchestrator with default config
_default_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator(config: Optional[OrchestratorConfig] = None) -> AgentOrchestrator:
    """
    Get orchestrator instance.

    Args:
        config: Optional configuration (creates new orchestrator if provided)

    Returns:
        AgentOrchestrator instance
    """
    global _default_orchestrator

    if config:
        return AgentOrchestrator(config)

    if _default_orchestrator is None:
        _default_orchestrator = AgentOrchestrator()

    return _default_orchestrator
