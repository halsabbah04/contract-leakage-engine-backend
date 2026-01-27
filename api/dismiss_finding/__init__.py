"""Azure Function: Dismiss Finding

Allow users to dismiss a finding and add notes.
"""

import json

import azure.functions as func

from shared.db import FindingRepository, SessionRepository, get_cosmos_client
from shared.models.session import FindingOverride
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Dismiss a finding and optionally add user notes.

    Route: POST /api/dismiss_finding/{contract_id}/{finding_id}

    Request body (optional):
    {
        "reason": "User's reason for dismissing",
        "notes": "Additional notes"
    }

    Returns:
    - 200: Finding dismissed successfully
    - 404: Finding not found
    - 500: Server error
    """
    logger.info("dismiss_finding function triggered")

    try:
        # Get parameters
        contract_id = req.route_params.get("contract_id")
        finding_id = req.route_params.get("finding_id")

        if not contract_id or not finding_id:
            return func.HttpResponse(
                json.dumps({"error": "contract_id and finding_id are required"}),
                status_code=400,
                mimetype="application/json",
            )

        # Parse request body
        try:
            req_body = req.get_json()
            reason = req_body.get("reason", "User dismissed")
            notes = req_body.get("notes")
        except ValueError:
            reason = "User dismissed"
            notes = None

        logger.info(f"Dismissing finding {finding_id} for contract {contract_id}")

        # Initialize repositories
        cosmos_client = get_cosmos_client()
        finding_repo = FindingRepository(cosmos_client.findings_container)
        session_repo = SessionRepository(cosmos_client.sessions_container)

        # Dismiss the finding
        updated_finding = finding_repo.dismiss_finding(finding_id, contract_id, notes)

        # Record override in session
        override = FindingOverride(finding_id=finding_id, action="dismissed", reason=reason)
        session_repo.add_override(contract_id, override)

        logger.info(f"Finding {finding_id} dismissed successfully")

        return func.HttpResponse(
            json.dumps(
                {
                    "message": "Finding dismissed successfully",
                    "finding_id": finding_id,
                    "contract_id": contract_id,
                    "finding": updated_finding.model_dump(mode="json", exclude={"embedding"}),
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        logger.warning(f"Finding not found: {str(e)}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=404, mimetype="application/json")

    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in dismiss_finding: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
