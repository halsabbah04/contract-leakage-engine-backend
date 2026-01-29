"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

from ..utils.logging import setup_logging

logger = setup_logging(__name__)

T = TypeVar("T")


class AgentStatus(str, Enum):
    """Status of agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some data retrieved, but with errors


class AgentResult(BaseModel, Generic[T]):
    """Result wrapper for agent execution."""

    agent_name: str = Field(..., description="Name of the agent")
    agent_version: str = Field(default="1.0", description="Version of the agent")
    status: AgentStatus = Field(..., description="Execution status")
    contract_id: str = Field(..., description="Contract ID processed")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution end time")
    duration_ms: Optional[float] = Field(None, description="Execution duration in milliseconds")
    data: Optional[Any] = Field(None, description="Agent-specific output data")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    All agents must implement:
    - execute(): The main logic of the agent
    - get_required_inputs(): List of data types needed (e.g., ['clauses', 'findings'])

    Agents can optionally override:
    - validate_inputs(): Custom input validation
    - on_success(): Called after successful execution
    - on_failure(): Called after failed execution
    """

    agent_name: str = "base_agent"
    agent_version: str = "1.0"

    def __init__(self, contract_id: str):
        """Initialize the agent with a contract ID."""
        self.contract_id = contract_id
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status: AgentStatus = AgentStatus.PENDING
        self.error: Optional[str] = None
        self.warnings: List[str] = []
        self._result_data: Optional[Any] = None

    @abstractmethod
    async def execute(self) -> Any:
        """
        Execute the agent's main logic.

        Must be implemented by subclasses.
        Should return the agent-specific output data.

        Raises:
            Exception: If execution fails
        """
        pass

    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """
        Return list of required input data types.

        Examples: ['clauses', 'findings', 'contract']

        Returns:
            List of required input types
        """
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate that required inputs are present and valid.

        Can be overridden by subclasses for custom validation.

        Args:
            inputs: Dictionary of input data

        Returns:
            True if inputs are valid

        Raises:
            ValueError: If inputs are invalid
        """
        required = self.get_required_inputs()
        for req in required:
            if req not in inputs or inputs[req] is None:
                raise ValueError(f"Missing required input: {req}")
        return True

    def add_warning(self, warning: str) -> None:
        """Add a non-fatal warning message."""
        self.warnings.append(warning)
        logger.warning(f"[{self.agent_name}] {warning}")

    async def on_success(self, result: Any) -> None:
        """
        Called after successful execution.

        Can be overridden for post-processing, notifications, etc.
        """
        logger.info(f"[{self.agent_name}] Execution completed successfully for contract {self.contract_id}")

    async def on_failure(self, error: Exception) -> None:
        """
        Called after failed execution.

        Can be overridden for error handling, notifications, etc.
        """
        logger.error(f"[{self.agent_name}] Execution failed for contract {self.contract_id}: {str(error)}")

    async def run(self, inputs: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Run the agent with error handling, timing, and result wrapping.

        Args:
            inputs: Optional dictionary of input data (for validation)

        Returns:
            AgentResult containing status, data, and metadata
        """
        self.started_at = datetime.utcnow()
        self.status = AgentStatus.RUNNING

        logger.info(f"[{self.agent_name}] Starting execution for contract {self.contract_id}")

        try:
            # Validate inputs if provided
            if inputs is not None:
                self.validate_inputs(inputs)

            # Execute main logic
            result_data = await self.execute()
            self._result_data = result_data

            # Determine status based on warnings
            self.status = AgentStatus.PARTIAL if self.warnings else AgentStatus.COMPLETED
            self.completed_at = datetime.utcnow()

            # Call success hook
            await self.on_success(result_data)

            duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.agent_version,
                status=self.status,
                contract_id=self.contract_id,
                started_at=self.started_at,
                completed_at=self.completed_at,
                duration_ms=duration_ms,
                data=result_data,
                warnings=self.warnings,
            )

        except Exception as e:
            self.status = AgentStatus.FAILED
            self.error = str(e)
            self.completed_at = datetime.utcnow()

            # Call failure hook
            await self.on_failure(e)

            duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

            logger.error(f"[{self.agent_name}] Error: {str(e)}", exc_info=True)

            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.agent_version,
                status=self.status,
                contract_id=self.contract_id,
                started_at=self.started_at,
                completed_at=self.completed_at,
                duration_ms=duration_ms,
                error=str(e),
                warnings=self.warnings,
            )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<{self.__class__.__name__}(contract_id={self.contract_id}, status={self.status})>"
