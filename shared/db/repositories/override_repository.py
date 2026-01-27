"""Override repository for managing user overrides."""

from typing import Dict, List, Optional

from azure.cosmos import ContainerProxy

from ...models.override import OverrideAction, OverrideSummary, UserOverride
from ...utils.logging import setup_logging
from .base_repository import BaseRepository

logger = setup_logging(__name__)


class OverrideRepository(BaseRepository[UserOverride]):
    """Repository for user override operations."""

    def __init__(self, container: ContainerProxy):
        """
        Initialize override repository.

        Args:
            container: Cosmos DB container for overrides
        """
        super().__init__(container, UserOverride)

    def get_by_contract(self, contract_id: str) -> List[UserOverride]:
        """
        Get all overrides for a specific contract.

        Args:
            contract_id: Contract ID (partition key)

        Returns:
            List of overrides for the contract
        """
        query = "SELECT * FROM c WHERE c.contract_id = @contract_id ORDER BY c.timestamp DESC"
        parameters = [{"name": "@contract_id", "value": contract_id}]

        return self.query(query, parameters, partition_key=contract_id)

    def get_by_finding(self, contract_id: str, finding_id: str) -> List[UserOverride]:
        """
        Get all overrides for a specific finding.

        Args:
            contract_id: Contract ID (partition key)
            finding_id: Finding ID

        Returns:
            List of overrides for the finding
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.finding_id = @finding_id
            ORDER BY c.timestamp DESC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@finding_id", "value": finding_id},
        ]

        return self.query(query, parameters, partition_key=contract_id)

    def get_by_user(self, contract_id: str, user_email: str) -> List[UserOverride]:
        """
        Get all overrides by a specific user for a contract.

        Args:
            contract_id: Contract ID (partition key)
            user_email: User's email address

        Returns:
            List of overrides by the user
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.user_email = @user_email
            ORDER BY c.timestamp DESC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@user_email", "value": user_email},
        ]

        return self.query(query, parameters, partition_key=contract_id)

    def get_by_action(self, contract_id: str, action: OverrideAction) -> List[UserOverride]:
        """
        Get all overrides of a specific action type for a contract.

        Args:
            contract_id: Contract ID (partition key)
            action: Override action type

        Returns:
            List of overrides with the specified action
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.action = @action
            ORDER BY c.timestamp DESC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@action", "value": action.value},
        ]

        return self.query(query, parameters, partition_key=contract_id)

    def get_summary(self, contract_id: str) -> OverrideSummary:
        """
        Get summary statistics of all overrides for a contract.

        Args:
            contract_id: Contract ID (partition key)

        Returns:
            Override summary with counts by action type
        """
        overrides = self.get_by_contract(contract_id)

        # Count by action type
        by_action: Dict[str, int] = {}
        accepted_count = 0
        rejected_count = 0
        false_positive_count = 0
        severity_changes = 0

        for override in overrides:
            action_key = override.action.value
            by_action[action_key] = by_action.get(action_key, 0) + 1

            # Count specific action types
            if override.action == OverrideAction.ACCEPT:
                accepted_count += 1
            elif override.action == OverrideAction.REJECT:
                rejected_count += 1
            elif override.action == OverrideAction.MARK_FALSE_POSITIVE:
                false_positive_count += 1
            elif override.action == OverrideAction.CHANGE_SEVERITY:
                severity_changes += 1

        return OverrideSummary(
            contract_id=contract_id,
            total_overrides=len(overrides),
            by_action=by_action,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            false_positive_count=false_positive_count,
            severity_changes=severity_changes,
        )

    def get_latest_by_finding(self, contract_id: str, finding_id: str) -> Optional[UserOverride]:
        """
        Get the most recent override for a specific finding.

        Args:
            contract_id: Contract ID (partition key)
            finding_id: Finding ID

        Returns:
            Most recent override for the finding, or None
        """
        overrides = self.get_by_finding(contract_id, finding_id)
        return overrides[0] if overrides else None
