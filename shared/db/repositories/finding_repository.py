"""Repository for LeakageFinding operations."""

from typing import List, Optional

from .base_repository import BaseRepository
from ...models.finding import LeakageFinding, Severity, LeakageCategory
from ...utils.logging import setup_logging

logger = setup_logging(__name__)


class FindingRepository(BaseRepository[LeakageFinding]):
    """Repository for LeakageFinding CRUD operations."""

    def __init__(self, container):
        """Initialize finding repository."""
        super().__init__(container, LeakageFinding)

    def get_by_contract_id(self, contract_id: str) -> List[LeakageFinding]:
        """
        Get all findings for a specific contract.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of findings for the contract
        """
        logger.info(f"Getting all findings for contract {contract_id}")
        return self.get_all_by_partition(contract_id)

    def get_by_id_and_contract(self, finding_id: str, contract_id: str) -> Optional[LeakageFinding]:
        """
        Get a specific finding by ID and contract ID.

        Args:
            finding_id: Finding identifier
            contract_id: Contract identifier (partition key)

        Returns:
            Finding if found, None otherwise
        """
        return self.read(finding_id, contract_id)

    def get_by_severity(self, contract_id: str, severity: Severity) -> List[LeakageFinding]:
        """
        Get all findings of a specific severity level.

        Args:
            contract_id: Contract identifier (partition key)
            severity: Severity level to filter by

        Returns:
            List of findings with the given severity
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.severity = @severity
            AND c.type = 'finding'
            AND c.user_dismissed = false
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@severity", "value": severity.value}
        ]

        logger.info(f"Getting {severity.value} severity findings for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_by_category(self, contract_id: str, category: LeakageCategory) -> List[LeakageFinding]:
        """
        Get all findings in a specific leakage category.

        Args:
            contract_id: Contract identifier (partition key)
            category: Leakage category to filter by

        Returns:
            List of findings in the category
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.leakage_category = @category
            AND c.type = 'finding'
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@category", "value": category.value}
        ]

        logger.info(f"Getting {category.value} findings for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_active_findings(self, contract_id: str) -> List[LeakageFinding]:
        """
        Get all active (non-dismissed) findings for a contract.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of active findings
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.user_dismissed = false
            AND c.type = 'finding'
            ORDER BY c.severity DESC
        """
        parameters = [{"name": "@contract_id", "value": contract_id}]

        logger.info(f"Getting active findings for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_high_impact_findings(self, contract_id: str, min_impact: float = 10000.0) -> List[LeakageFinding]:
        """
        Get findings with estimated impact above a threshold.

        Args:
            contract_id: Contract identifier (partition key)
            min_impact: Minimum impact value in USD

        Returns:
            List of high-impact findings
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.estimated_impact.value >= @min_impact
            AND c.user_dismissed = false
            AND c.type = 'finding'
            ORDER BY c.estimated_impact.value DESC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@min_impact", "value": min_impact}
        ]

        logger.info(f"Getting findings with impact >= ${min_impact} for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def dismiss_finding(self, finding_id: str, contract_id: str, user_notes: Optional[str] = None) -> LeakageFinding:
        """
        Mark a finding as dismissed by the user.

        Args:
            finding_id: Finding identifier
            contract_id: Contract identifier (partition key)
            user_notes: Optional notes from user

        Returns:
            Updated finding
        """
        finding = self.get_by_id_and_contract(finding_id, contract_id)
        if not finding:
            raise ValueError(f"Finding {finding_id} not found in contract {contract_id}")

        finding.user_dismissed = True
        if user_notes:
            finding.user_notes = user_notes

        logger.info(f"Dismissing finding {finding_id} for contract {contract_id}")
        return self.update(finding)

    def add_embedding(self, finding_id: str, contract_id: str, embedding: List[float]) -> LeakageFinding:
        """
        Add vector embedding to a finding (for similarity search).

        Args:
            finding_id: Finding identifier
            contract_id: Contract identifier (partition key)
            embedding: Vector embedding

        Returns:
            Updated finding
        """
        finding = self.get_by_id_and_contract(finding_id, contract_id)
        if not finding:
            raise ValueError(f"Finding {finding_id} not found in contract {contract_id}")

        finding.embedding = embedding

        logger.info(f"Adding embedding to finding {finding_id} (dim={len(embedding)})")
        return self.update(finding)

    def bulk_create(self, findings: List[LeakageFinding]) -> List[LeakageFinding]:
        """
        Create multiple findings efficiently.

        Args:
            findings: List of findings to create

        Returns:
            List of created findings
        """
        created_findings = []

        logger.info(f"Bulk creating {len(findings)} findings")

        for finding in findings:
            try:
                created = self.create(finding)
                created_findings.append(created)
            except Exception as e:
                logger.error(f"Failed to create finding {finding.id}: {str(e)}")
                # Continue with other findings

        logger.info(f"Successfully created {len(created_findings)}/{len(findings)} findings")
        return created_findings
