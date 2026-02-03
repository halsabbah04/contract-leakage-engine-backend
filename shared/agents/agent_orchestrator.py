"""Agent Orchestrator for managing multiple AI agents in parallel."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..utils.logging import setup_logging
from ..utils.async_helpers import gather_with_progress

logger = setup_logging(__name__)


class AgentPhase(Enum):
    """Analysis phases for agent execution ordering."""
    INGEST = "ingest"          # Stage 1: Document ingestion & text extraction
    ANALYZE = "analyze"        # Stage 2: Clause extraction & leakage detection
    ENRICH = "enrich"          # Stage 3: Contextual analysis (benchmarks, obligations, compliance)
    ADVISE = "advise"          # Stage 4: Strategic recommendations


@dataclass
class AgentRegistration:
    """Registration information for an agent."""
    agent_id: str
    agent_name: str
    phase: AgentPhase
    execute_func: Callable
    dependencies: Set[str] = field(default_factory=set)
    optional: bool = False  # If True, failure doesn't stop pipeline
    timeout: float = 180.0
    description: str = ""


@dataclass
class AgentResult:
    """Result from agent execution."""
    agent_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    warnings: List[str] = field(default_factory=list)


class AgentOrchestrator:
    """
    Orchestrates execution of multiple AI agents in parallel.

    Features:
    - Phase-based execution (INGEST → ANALYZE → ENRICH → ADVISE)
    - Parallel execution within phases
    - Dependency management
    - Optional agents (graceful degradation)
    - Result aggregation
    """

    def __init__(self):
        """Initialize orchestrator."""
        self._agents: Dict[str, AgentRegistration] = {}
        self._results: Dict[str, AgentResult] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        phase: AgentPhase,
        execute_func: Callable,
        dependencies: Optional[List[str]] = None,
        optional: bool = False,
        timeout: float = 180.0,
        description: str = ""
    ):
        """
        Register an agent for execution.

        Args:
            agent_id: Unique identifier for the agent
            agent_name: Display name for logging
            phase: Execution phase (INGEST, ANALYZE, ENRICH, ADVISE)
            execute_func: Async function to execute
            dependencies: List of agent IDs that must complete first
            optional: If True, failure doesn't stop pipeline
            timeout: Timeout in seconds
            description: Agent description for logging
        """
        registration = AgentRegistration(
            agent_id=agent_id,
            agent_name=agent_name,
            phase=phase,
            execute_func=execute_func,
            dependencies=set(dependencies or []),
            optional=optional,
            timeout=timeout,
            description=description
        )

        self._agents[agent_id] = registration
        logger.info(f"Registered agent: {agent_name} (phase={phase.value}, optional={optional})")

    def get_agents_by_phase(self, phase: AgentPhase) -> List[AgentRegistration]:
        """Get all agents for a specific phase."""
        return [agent for agent in self._agents.values() if agent.phase == phase]

    def check_dependencies_met(self, agent: AgentRegistration) -> bool:
        """Check if all dependencies for an agent are met."""
        for dep_id in agent.dependencies:
            if dep_id not in self._results:
                return False
            if not self._results[dep_id].success:
                return False
        return True

    async def execute_agent(self, agent: AgentRegistration, context: Dict[str, Any]) -> AgentResult:
        """
        Execute a single agent with timeout and error handling.

        Args:
            agent: Agent registration
            context: Execution context with inputs

        Returns:
            AgentResult with success/failure status
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"[{agent.agent_name}] Starting execution...")

            # Execute with timeout
            result_data = await asyncio.wait_for(
                agent.execute_func(context),
                timeout=agent.timeout
            )

            duration = time.time() - start_time
            logger.info(f"[{agent.agent_name}] Completed in {duration:.2f}s")

            return AgentResult(
                agent_id=agent.agent_id,
                success=True,
                data=result_data,
                duration=duration
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error_msg = f"Timed out after {agent.timeout}s"
            logger.error(f"[{agent.agent_name}] {error_msg}")

            return AgentResult(
                agent_id=agent.agent_id,
                success=False,
                error=error_msg,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"[{agent.agent_name}] Failed: {error_msg}", exc_info=True)

            return AgentResult(
                agent_id=agent.agent_id,
                success=False,
                error=error_msg,
                duration=duration
            )

    async def execute_phase(self, phase: AgentPhase, context: Dict[str, Any]) -> Dict[str, AgentResult]:
        """
        Execute all agents in a phase in parallel (where dependencies allow).

        Args:
            phase: Phase to execute
            context: Execution context

        Returns:
            Dictionary of agent_id -> AgentResult
        """
        agents = self.get_agents_by_phase(phase)

        if not agents:
            logger.info(f"No agents registered for phase: {phase.value}")
            return {}

        logger.info(f"=== Executing Phase: {phase.value.upper()} ({len(agents)} agents) ===")

        # Execute agents in parallel
        tasks = []
        task_names = []

        for agent in agents:
            # Check dependencies
            if not self.check_dependencies_met(agent):
                logger.warning(f"[{agent.agent_name}] Skipping - dependencies not met")
                self._results[agent.agent_id] = AgentResult(
                    agent_id=agent.agent_id,
                    success=False,
                    error="Dependencies not met"
                )
                continue

            tasks.append(self.execute_agent(agent, context))
            task_names.append(agent.agent_name)

        if not tasks:
            logger.warning(f"No agents ready to execute in phase: {phase.value}")
            return {}

        # Execute all agents in parallel
        results = await gather_with_progress(
            tasks,
            task_names=task_names,
            return_exceptions=True
        )

        # Store results
        phase_results = {}
        for i, agent in enumerate([a for a in agents if self.check_dependencies_met(a)]):
            result = results[i] if not isinstance(results[i], Exception) else AgentResult(
                agent_id=agent.agent_id,
                success=False,
                error=str(results[i])
            )

            self._results[agent.agent_id] = result
            phase_results[agent.agent_id] = result

            # Check if critical agent failed
            if not result.success and not agent.optional:
                logger.error(f"[{agent.agent_name}] Critical agent failed - may affect dependent agents")

        # Phase summary
        success_count = sum(1 for r in phase_results.values() if r.success)
        logger.info(
            f"=== Phase {phase.value.upper()} Complete: "
            f"{success_count}/{len(phase_results)} agents succeeded ==="
        )

        return phase_results

    async def execute_all(self, context: Dict[str, Any]) -> Dict[str, AgentResult]:
        """
        Execute all registered agents across all phases.

        Args:
            context: Execution context with inputs

        Returns:
            Dictionary of agent_id -> AgentResult for all agents
        """
        logger.info("====== Starting Agent Orchestration ======")
        logger.info(f"Total agents registered: {len(self._agents)}")

        # Execute phases in order
        for phase in AgentPhase:
            await self.execute_phase(phase, context)

        # Final summary
        total_success = sum(1 for r in self._results.values() if r.success)
        total_agents = len(self._results)

        logger.info("====== Agent Orchestration Complete ======")
        logger.info(f"Results: {total_success}/{total_agents} agents succeeded")

        return self._results

    def get_result(self, agent_id: str) -> Optional[AgentResult]:
        """Get result for a specific agent."""
        return self._results.get(agent_id)

    def get_successful_results(self) -> Dict[str, AgentResult]:
        """Get all successful agent results."""
        return {
            agent_id: result
            for agent_id, result in self._results.items()
            if result.success
        }

    def get_failed_agents(self) -> List[str]:
        """Get list of failed agent IDs."""
        return [
            agent_id
            for agent_id, result in self._results.items()
            if not result.success
        ]

    def clear(self):
        """Clear all results (for reuse)."""
        self._results.clear()


# Global orchestrator instance
_orchestrator = AgentOrchestrator()


def get_orchestrator() -> AgentOrchestrator:
    """Get the global agent orchestrator instance."""
    return _orchestrator
