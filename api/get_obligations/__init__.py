"""Azure Function: Get Obligations

Retrieves extracted obligations for a contract.
"""

import json
from typing import Optional

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.db.repositories.obligation_repository import ObligationRepository
from shared.models.obligation import ObligationStatus, ObligationType
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get obligations for a contract.

    Route: GET /api/obligations/{contract_id}

    Query Parameters:
        type: Filter by obligation type (payment, delivery, notice, etc.)
        status: Filter by status (upcoming, due_soon, overdue, completed, waived)
        responsible: Filter by responsible party ("our" or "counterparty")
        include_summary: Include summary statistics (default: true)

    Returns:
        200: List of obligations
        404: Contract not found
        500: Server error
    """
    logger.info("get_obligations function triggered")

    try:
        # Get contract_id from route parameter
        contract_id = req.route_params.get("contract_id")

        if not contract_id:
            logger.warning("No contract_id provided")
            return func.HttpResponse(
                json.dumps({"error": "contract_id is required"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Getting obligations for contract: {contract_id}")

        # Initialize repositories
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        obligation_repo = ObligationRepository(cosmos_client.obligations_container)

        # Verify contract exists
        contract = contract_repo.get_by_contract_id(contract_id)
        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Get filter parameters
        type_filter = req.params.get("type")
        status_filter = req.params.get("status")
        responsible_filter = req.params.get("responsible")
        include_summary = req.params.get("include_summary", "true").lower() == "true"

        # Retrieve obligations based on filters
        if type_filter:
            try:
                obligation_type = ObligationType(type_filter.lower())
                obligations = obligation_repo.get_by_type(contract_id, obligation_type)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid obligation type: {type_filter}"}),
                    status_code=400,
                    mimetype="application/json",
                )
        elif status_filter:
            try:
                status = ObligationStatus(status_filter.lower())
                obligations = obligation_repo.get_by_status(contract_id, status)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid status: {status_filter}"}),
                    status_code=400,
                    mimetype="application/json",
                )
        elif responsible_filter:
            if responsible_filter.lower() == "our":
                obligations = obligation_repo.get_our_obligations(contract_id)
            elif responsible_filter.lower() == "counterparty":
                obligations = obligation_repo.get_counterparty_obligations(contract_id)
            else:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid responsible filter: {responsible_filter}. Use 'our' or 'counterparty'"}),
                    status_code=400,
                    mimetype="application/json",
                )
        else:
            # Get all obligations
            obligations = obligation_repo.get_by_contract_id(contract_id)

        logger.info(f"Retrieved {len(obligations)} obligations for contract {contract_id}")

        # Convert obligations to dict
        obligations_data = [_obligation_to_dict(obl) for obl in obligations]

        # Build response
        response_data = {
            "contract_id": contract_id,
            "total": len(obligations_data),
            "obligations": obligations_data,
        }

        # Include summary if requested
        if include_summary:
            # Pass counterparty to help identify party names
            summary = obligation_repo.get_summary(contract_id, counterparty=contract.counterparty)
            response_data["summary"] = {
                "total_obligations": summary.total_obligations,
                "by_type": summary.by_type,
                "by_status": summary.by_status,
                "by_responsible_party": summary.by_responsible_party,
                "upcoming_count": summary.upcoming_count,
                "due_soon_count": summary.due_soon_count,
                "overdue_count": summary.overdue_count,
                "total_payment_obligations": summary.total_payment_obligations,
                "our_payment_obligations": summary.our_payment_obligations,
                "their_payment_obligations": summary.their_payment_obligations,
                "currency": summary.currency,
                "our_organization_name": summary.our_organization_name,
                "counterparty_name": summary.counterparty_name,
                "next_due_date": summary.next_due_date.isoformat() if summary.next_due_date else None,
                "next_obligation_title": summary.next_obligation_title,
            }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json",
        )

    except DatabaseError as e:
        error_str = str(e)
        logger.error(f"Database error: {error_str}")

        # Handle container not found - return empty results instead of error
        if "NotFound" in error_str and "obligations" in error_str:
            logger.warning("Obligations container not found - returning empty results")
            return func.HttpResponse(
                json.dumps({
                    "contract_id": req.route_params.get("contract_id"),
                    "total": 0,
                    "obligations": [],
                    "summary": {
                        "total_obligations": 0,
                        "by_type": {},
                        "by_status": {},
                        "by_responsible_party": {},
                        "upcoming_count": 0,
                        "due_soon_count": 0,
                        "overdue_count": 0,
                        "total_payment_obligations": 0,
                        "our_payment_obligations": 0,
                        "their_payment_obligations": 0,
                        "next_due_date": None,
                        "next_obligation_title": None,
                    },
                    "_warning": "Obligations container not configured. Please create the 'obligations' container in Cosmos DB."
                }),
                status_code=200,
                mimetype="application/json",
            )

        return func.HttpResponse(
            json.dumps({"error": "Database error occurred", "details": error_str}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_obligations: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


def _obligation_to_dict(obligation) -> dict:
    """Convert an Obligation object to a dictionary for JSON response."""
    return {
        "id": obligation.id,
        "contract_id": obligation.contract_id,
        "obligation_type": obligation.obligation_type if isinstance(obligation.obligation_type, str) else obligation.obligation_type.value,
        "title": obligation.title,
        "description": obligation.description,
        "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
        "effective_date": obligation.effective_date.isoformat() if obligation.effective_date else None,
        "end_date": obligation.end_date.isoformat() if obligation.end_date else None,
        "is_recurring": obligation.is_recurring,
        "recurrence_pattern": obligation.recurrence_pattern if isinstance(obligation.recurrence_pattern, str) else obligation.recurrence_pattern.value,
        "recurrence_end_date": obligation.recurrence_end_date.isoformat() if obligation.recurrence_end_date else None,
        "next_occurrence": obligation.next_occurrence.isoformat() if obligation.next_occurrence else None,
        "responsible_party": {
            "party_name": obligation.responsible_party.party_name,
            "party_role": obligation.responsible_party.party_role,
            "is_our_organization": obligation.responsible_party.is_our_organization,
        },
        "amount": obligation.amount,
        "currency": obligation.currency,
        "status": obligation.status if isinstance(obligation.status, str) else obligation.status.value,
        "priority": obligation.priority if isinstance(obligation.priority, str) else obligation.priority.value,
        "clause_ids": obligation.clause_ids,
        "extracted_text": obligation.extracted_text,
        "reminder_days_before": obligation.reminder_days_before,
        "notes": obligation.notes,
        "extraction_confidence": obligation.extraction_confidence,
        "extracted_at": obligation.extracted_at.isoformat() if obligation.extracted_at else None,
        "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
    }
