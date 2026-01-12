"""Repository for AnalysisSession operations."""

from typing import Optional
from datetime import datetime

from .base_repository import BaseRepository
from ...models.session import AnalysisSession, FindingOverride
from ...utils.logging import setup_logging

logger = setup_logging(__name__)


class SessionRepository(BaseRepository[AnalysisSession]):
    """Repository for AnalysisSession CRUD operations."""

    def __init__(self, container):
        """Initialize session repository."""
        super().__init__(container, AnalysisSession)

    def get_by_contract_id(self, contract_id: str) -> Optional[AnalysisSession]:
        """
        Get the analysis session for a contract.

        Note: Typically one session per contract, but ID might differ from contract_id.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            Session if found, None otherwise
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.type = 'session'
        """
        parameters = [{"name": "@contract_id", "value": contract_id}]

        sessions = self.query(query, parameters, partition_key=contract_id)

        if sessions:
            logger.info(f"Found session for contract {contract_id}")
            return sessions[0]  # Return first (should be only one)

        logger.info(f"No session found for contract {contract_id}")
        return None

    def get_or_create_session(self, contract_id: str, user_role: Optional[str] = None) -> AnalysisSession:
        """
        Get existing session or create new one for contract.

        Args:
            contract_id: Contract identifier
            user_role: Optional user role

        Returns:
            Existing or newly created session
        """
        existing = self.get_by_contract_id(contract_id)

        if existing:
            logger.info(f"Returning existing session for contract {contract_id}")
            return existing

        # Create new session
        session = AnalysisSession(
            id=f"session_{contract_id}",
            contract_id=contract_id,
            partition_key=contract_id,
            user_role=user_role
        )

        logger.info(f"Creating new session for contract {contract_id}")
        return self.create(session)

    def add_override(self, contract_id: str, override: FindingOverride) -> AnalysisSession:
        """
        Add a user override to the session.

        Args:
            contract_id: Contract identifier
            override: Finding override to add

        Returns:
            Updated session
        """
        session = self.get_or_create_session(contract_id)
        session.add_override(override)

        logger.info(f"Adding override to session for contract {contract_id}: {override.finding_id}")
        return self.update(session)

    def record_export(self, contract_id: str, export_format: str, export_uri: Optional[str] = None) -> AnalysisSession:
        """
        Record an export action in the session.

        Args:
            contract_id: Contract identifier
            export_format: Format of export (pdf, excel, etc.)
            export_uri: Optional URI to exported file

        Returns:
            Updated session
        """
        session = self.get_or_create_session(contract_id)
        session.add_export(export_format, export_uri)

        logger.info(f"Recording {export_format} export for contract {contract_id}")
        return self.update(session)

    def update_custom_assumptions(self, contract_id: str, assumptions: dict) -> AnalysisSession:
        """
        Update custom assumptions in the session.

        Args:
            contract_id: Contract identifier
            assumptions: Dictionary of custom assumptions

        Returns:
            Updated session
        """
        session = self.get_or_create_session(contract_id)
        session.custom_assumptions.update(assumptions)
        session.last_activity_at = datetime.utcnow()

        logger.info(f"Updating custom assumptions for contract {contract_id}")
        return self.update(session)

    def update_session_duration(self, contract_id: str) -> AnalysisSession:
        """
        Calculate and update session duration.

        Args:
            contract_id: Contract identifier

        Returns:
            Updated session
        """
        session = self.get_or_create_session(contract_id)

        duration = (datetime.utcnow() - session.created_at).total_seconds()
        session.session_duration_seconds = duration
        session.last_activity_at = datetime.utcnow()

        logger.info(f"Updating session duration for contract {contract_id}: {duration}s")
        return self.update(session)
