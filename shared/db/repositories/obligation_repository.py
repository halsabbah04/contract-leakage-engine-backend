"""Repository for Obligation operations."""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from ...models.obligation import (
    Obligation,
    ObligationPriority,
    ObligationStatus,
    ObligationSummary,
    ObligationType,
)
from ...utils.logging import setup_logging
from .base_repository import BaseRepository

logger = setup_logging(__name__)


class ObligationRepository(BaseRepository[Obligation]):
    """Repository for Obligation CRUD operations."""

    def __init__(self, container):
        """Initialize obligation repository."""
        super().__init__(container, Obligation)

    def get_by_contract_id(self, contract_id: str) -> List[Obligation]:
        """
        Get all obligations for a specific contract.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of obligations for the contract
        """
        logger.info(f"Getting all obligations for contract {contract_id}")
        return self.get_all_by_partition(contract_id)

    def get_by_id_and_contract(self, obligation_id: str, contract_id: str) -> Optional[Obligation]:
        """
        Get a specific obligation by ID and contract ID.

        Args:
            obligation_id: Obligation identifier
            contract_id: Contract identifier (partition key)

        Returns:
            Obligation if found, None otherwise
        """
        return self.read(obligation_id, contract_id)

    def get_by_type(self, contract_id: str, obligation_type: ObligationType) -> List[Obligation]:
        """
        Get all obligations of a specific type.

        Args:
            contract_id: Contract identifier (partition key)
            obligation_type: Type to filter by

        Returns:
            List of obligations with the given type
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.obligation_type = @obligation_type
            AND c.type = 'obligation'
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@obligation_type", "value": obligation_type.value if hasattr(obligation_type, 'value') else obligation_type},
        ]

        logger.info(f"Getting {obligation_type} obligations for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_by_status(self, contract_id: str, status: ObligationStatus) -> List[Obligation]:
        """
        Get all obligations with a specific status.

        Args:
            contract_id: Contract identifier (partition key)
            status: Status to filter by

        Returns:
            List of obligations with the given status
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.status = @status
            AND c.type = 'obligation'
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@status", "value": status.value if hasattr(status, 'value') else status},
        ]

        logger.info(f"Getting {status} obligations for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_due_soon(self, contract_id: str, days: int = 30) -> List[Obligation]:
        """
        Get obligations due within a specified number of days.

        Args:
            contract_id: Contract identifier (partition key)
            days: Number of days to look ahead

        Returns:
            List of obligations due within the specified period
        """
        today = date.today()
        future_date = today + timedelta(days=days)

        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.due_date >= @today
            AND c.due_date <= @future_date
            AND c.status NOT IN ('completed', 'waived', 'not_applicable')
            AND c.type = 'obligation'
            ORDER BY c.due_date ASC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@today", "value": today.isoformat()},
            {"name": "@future_date", "value": future_date.isoformat()},
        ]

        logger.info(f"Getting obligations due within {days} days for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_overdue(self, contract_id: str) -> List[Obligation]:
        """
        Get overdue obligations.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of overdue obligations
        """
        today = date.today()

        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.due_date < @today
            AND c.status NOT IN ('completed', 'waived', 'not_applicable')
            AND c.type = 'obligation'
            ORDER BY c.due_date ASC
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@today", "value": today.isoformat()},
        ]

        logger.info(f"Getting overdue obligations for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_our_obligations(self, contract_id: str) -> List[Obligation]:
        """
        Get obligations where our organization is responsible.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of our obligations
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.responsible_party.is_our_organization = true
            AND c.type = 'obligation'
            ORDER BY c.due_date ASC
        """
        parameters = [{"name": "@contract_id", "value": contract_id}]

        logger.info(f"Getting our obligations for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_counterparty_obligations(self, contract_id: str) -> List[Obligation]:
        """
        Get obligations where the counterparty is responsible.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of counterparty obligations
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.responsible_party.is_our_organization = false
            AND c.type = 'obligation'
            ORDER BY c.due_date ASC
        """
        parameters = [{"name": "@contract_id", "value": contract_id}]

        logger.info(f"Getting counterparty obligations for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_payment_obligations(self, contract_id: str) -> List[Obligation]:
        """
        Get all payment obligations.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of payment obligations
        """
        return self.get_by_type(contract_id, ObligationType.PAYMENT)

    def update_status(
        self, obligation_id: str, contract_id: str, new_status: ObligationStatus, notes: Optional[str] = None
    ) -> Obligation:
        """
        Update the status of an obligation.

        Args:
            obligation_id: Obligation identifier
            contract_id: Contract identifier (partition key)
            new_status: New status to set
            notes: Optional notes about the status change

        Returns:
            Updated obligation
        """
        obligation = self.get_by_id_and_contract(obligation_id, contract_id)
        if not obligation:
            raise ValueError(f"Obligation {obligation_id} not found in contract {contract_id}")

        obligation.status = new_status
        if notes:
            obligation.notes = (obligation.notes or "") + f"\n[{date.today()}] Status changed to {new_status}: {notes}"

        logger.info(f"Updating status of obligation {obligation_id} to {new_status}")
        return self.update(obligation)

    def mark_completed(self, obligation_id: str, contract_id: str, notes: Optional[str] = None) -> Obligation:
        """
        Mark an obligation as completed.

        Args:
            obligation_id: Obligation identifier
            contract_id: Contract identifier (partition key)
            notes: Optional notes

        Returns:
            Updated obligation
        """
        return self.update_status(obligation_id, contract_id, ObligationStatus.COMPLETED, notes)

    def get_summary(self, contract_id: str) -> ObligationSummary:
        """
        Generate a summary of obligations for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            Obligation summary
        """
        obligations = self.get_by_contract_id(contract_id)

        # Initialize summary
        summary = ObligationSummary(
            contract_id=contract_id,
            total_obligations=len(obligations),
            by_type={},
            by_status={},
            by_responsible_party={},
        )

        # Calculate counts
        for obl in obligations:
            # By type
            obl_type = obl.obligation_type if isinstance(obl.obligation_type, str) else obl.obligation_type.value
            summary.by_type[obl_type] = summary.by_type.get(obl_type, 0) + 1

            # By status
            obl_status = obl.status if isinstance(obl.status, str) else obl.status.value
            summary.by_status[obl_status] = summary.by_status.get(obl_status, 0) + 1

            # By responsible party
            party_name = obl.responsible_party.party_name
            summary.by_responsible_party[party_name] = summary.by_responsible_party.get(party_name, 0) + 1

            # Status counts
            if obl_status == "upcoming":
                summary.upcoming_count += 1
            elif obl_status == "due_soon":
                summary.due_soon_count += 1
            elif obl_status == "overdue":
                summary.overdue_count += 1

            # Financial summary
            if obl_type == "payment" and obl.amount:
                summary.total_payment_obligations += obl.amount
                if obl.responsible_party.is_our_organization:
                    summary.our_payment_obligations += obl.amount
                else:
                    summary.their_payment_obligations += obl.amount

        # Find next obligation
        upcoming = [
            o for o in obligations
            if o.due_date and o.status not in [ObligationStatus.COMPLETED, ObligationStatus.WAIVED]
        ]
        if upcoming:
            upcoming.sort(key=lambda x: x.due_date)
            next_obl = upcoming[0]
            summary.next_due_date = next_obl.due_date
            summary.next_obligation_title = next_obl.title

        logger.info(f"Generated summary for contract {contract_id}: {summary.total_obligations} obligations")
        return summary

    def bulk_create(self, obligations: List[Obligation]) -> List[Obligation]:
        """
        Create multiple obligations efficiently.

        Args:
            obligations: List of obligations to create

        Returns:
            List of created obligations
        """
        created_obligations = []

        logger.info(f"Bulk creating {len(obligations)} obligations")

        for obligation in obligations:
            try:
                created = self.create(obligation)
                created_obligations.append(created)
            except Exception as e:
                logger.error(f"Failed to create obligation {obligation.id}: {str(e)}")
                # Continue with other obligations

        logger.info(f"Successfully created {len(created_obligations)}/{len(obligations)} obligations")
        return created_obligations

    def delete_by_contract(self, contract_id: str) -> int:
        """
        Delete all obligations for a contract (for re-extraction).

        Args:
            contract_id: Contract identifier

        Returns:
            Number of deleted obligations
        """
        obligations = self.get_by_contract_id(contract_id)
        count = 0

        for obl in obligations:
            try:
                self.delete(obl.id, contract_id)
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete obligation {obl.id}: {str(e)}")

        logger.info(f"Deleted {count} obligations for contract {contract_id}")
        return count
