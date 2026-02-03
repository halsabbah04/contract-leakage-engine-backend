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

    def _normalize_and_consolidate_party_names(self, party_names: List[str]) -> Dict[str, str]:
        """
        Create a mapping of party name variations to their canonical form.

        For example: "Bahrain Economic Development Board" -> "EDB"
                    "EDB" -> "EDB"

        Args:
            party_names: List of all party names found in obligations

        Returns:
            Dictionary mapping original names to canonical names
        """
        import re

        # Step 1: Identify abbreviations (all caps, 2+ letters)
        abbreviations = [name for name in party_names if re.match(r'^[A-Z]{2,}$', name)]

        logger.info(f"Found abbreviations: {abbreviations}")

        # Step 2: Build mapping
        consolidated = {}

        for name in party_names:
            # Extract abbreviation from parentheses if present
            paren_match = re.search(r'\(([A-Z]{2,})\)\s*$', name)

            if paren_match:
                # "Bahrain Economic Development Board (EDB)" -> "EDB"
                consolidated[name] = paren_match.group(1)
            elif re.match(r'^[A-Z]{2,}$', name):
                # Already an abbreviation: "EDB" -> "EDB"
                consolidated[name] = name
            else:
                # Check if this full name matches any known abbreviation
                matched_abbrev = None

                for abbrev in abbreviations:
                    # Get all words from the full name
                    words = [w for w in name.split() if w and w[0].isalpha()]

                    # Strategy 1: Check if abbrev matches full initials
                    all_initials = ''.join([w[0].upper() for w in words])
                    if abbrev == all_initials:
                        matched_abbrev = abbrev
                        break

                    # Strategy 2: Check if abbrev matches initials of last N words (where N = len(abbrev))
                    # e.g., "EDB" matches last 3 words of "Bahrain Economic Development Board"
                    if len(words) >= len(abbrev):
                        last_n_initials = ''.join([w[0].upper() for w in words[-len(abbrev):]])
                        if abbrev == last_n_initials:
                            matched_abbrev = abbrev
                            logger.info(f"Matched '{name}' to '{abbrev}' using last {len(abbrev)} words")
                            break

                    # Strategy 3: Skip location/country prefixes and try again
                    # Common prefixes: country names, states, etc.
                    if len(words) > len(abbrev):
                        # Try skipping first word (often location)
                        words_without_first = words[1:]
                        initials_without_first = ''.join([w[0].upper() for w in words_without_first])
                        if abbrev == initials_without_first:
                            matched_abbrev = abbrev
                            logger.info(f"Matched '{name}' to '{abbrev}' by skipping first word")
                            break

                        # Try last N words after skipping first
                        if len(words_without_first) >= len(abbrev):
                            last_n_without_first = ''.join([w[0].upper() for w in words_without_first[-len(abbrev):]])
                            if abbrev == last_n_without_first:
                                matched_abbrev = abbrev
                                logger.info(f"Matched '{name}' to '{abbrev}' using last {len(abbrev)} words after skipping first")
                                break

                consolidated[name] = matched_abbrev if matched_abbrev else name

        return consolidated

    def get_summary(self, contract_id: str, counterparty: Optional[str] = None) -> ObligationSummary:
        """
        Generate a summary of obligations for a contract.

        Args:
            contract_id: Contract identifier
            counterparty: Optional counterparty name (not used)

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

        # Collect all unique party names first
        all_party_names = list(set(obl.responsible_party.party_name for obl in obligations))

        # Create mapping to consolidate party name variations
        party_name_mapping = self._normalize_and_consolidate_party_names(all_party_names)

        logger.info(f"Party name consolidation mapping: {party_name_mapping}")

        # Track currency usage to determine primary currency
        currency_amounts: Dict[str, float] = {}

        # Track party payment amounts (for third-party analysis tool)
        party_payments: Dict[str, float] = {}
        generic_party_names = {"both parties", "either party", "each party", "all parties", "the parties", "unknown party"}

        # Calculate counts
        for obl in obligations:
            # By type
            obl_type = obl.obligation_type if isinstance(obl.obligation_type, str) else obl.obligation_type.value
            summary.by_type[obl_type] = summary.by_type.get(obl_type, 0) + 1

            # By status
            obl_status = obl.status if isinstance(obl.status, str) else obl.status.value
            summary.by_status[obl_status] = summary.by_status.get(obl_status, 0) + 1

            # By responsible party (use consolidated name)
            original_party_name = obl.responsible_party.party_name
            consolidated_party_name = party_name_mapping.get(original_party_name, original_party_name)
            summary.by_responsible_party[consolidated_party_name] = summary.by_responsible_party.get(consolidated_party_name, 0) + 1

            # Status counts
            if obl_status == "upcoming":
                summary.upcoming_count += 1
            elif obl_status == "due_soon":
                summary.due_soon_count += 1
            elif obl_status == "overdue":
                summary.overdue_count += 1

            # Financial summary - collect all payment obligations by party (consolidated)
            if obl_type == "payment" and obl.amount:
                currency = obl.currency or "USD"
                currency_amounts[currency] = currency_amounts.get(currency, 0) + obl.amount
                summary.total_payment_obligations += obl.amount

                # Track payment amounts by party (exclude generic names, use consolidated name)
                if consolidated_party_name.lower() not in generic_party_names:
                    party_payments[consolidated_party_name] = party_payments.get(consolidated_party_name, 0) + obl.amount

        # Determine primary currency (the one with the highest total amount)
        if currency_amounts:
            primary_currency = max(currency_amounts.keys(), key=lambda c: currency_amounts[c])
            summary.currency = primary_currency

        logger.info(f"Consolidated party payments: {party_payments}")

        # Identify the two main payment parties by amount
        if len(party_payments) >= 2:
            # Sort parties by payment amount (descending)
            sorted_parties = sorted(party_payments.items(), key=lambda x: x[1], reverse=True)

            # Assign top 2 parties
            summary.our_organization_name = sorted_parties[0][0]
            summary.our_payment_obligations = sorted_parties[0][1]
            summary.counterparty_name = sorted_parties[1][0]
            summary.their_payment_obligations = sorted_parties[1][1]

            logger.info(f"Parties identified: {summary.our_organization_name} ({summary.currency} {summary.our_payment_obligations:.2f}), {summary.counterparty_name} ({summary.currency} {summary.their_payment_obligations:.2f})")
        elif len(party_payments) == 1:
            # Only one party with payments
            party = list(party_payments.keys())[0]
            amount = party_payments[party]
            summary.our_organization_name = party
            summary.our_payment_obligations = amount
            logger.info(f"Single payment party: {party} ({summary.currency} {amount:.2f})")

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
