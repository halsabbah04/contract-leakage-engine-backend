"""Azure Function: Create Override

Create a new user override for a finding.
"""

import json
from datetime import datetime

import azure.functions as func

from shared.db import OverrideRepository, get_cosmos_client
from shared.models.override import OverrideAction, UserOverride
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new user override for a finding.

    Route: POST /api/overrides/{contract_id}

    Request body:
    {
        "finding_id": "string",
        "action": "accept" | "reject" | "change_severity" | "mark_false_positive" | "add_note" | "resolve",
        "user_email": "string",
        "previous_value": "string" (optional),
        "new_value": "string" (optional),
        "notes": "string" (optional),
        "reason": "string" (optional)
    }

    Returns:
    - 201: Override created successfully
    - 400: Invalid request
    - 500: Server error
    """
    logger.info("create_override function triggered")

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

        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            logger.warning("Invalid JSON in request body")
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        # Validate required fields
        finding_id = req_body.get("finding_id")
        action = req_body.get("action")
        user_email = req_body.get("user_email")

        if not all([finding_id, action, user_email]):
            logger.warning("Missing required fields")
            return func.HttpResponse(
                json.dumps({"error": "Missing required fields: finding_id, action, user_email"}),
                status_code=400,
                mimetype="application/json",
            )

        # Validate action
        try:
            action_enum = OverrideAction(action)
        except ValueError:
            logger.warning(f"Invalid action: {action}")
            return func.HttpResponse(
                json.dumps(
                    {
                        "error": f"Invalid action: {action}",
                        "valid_actions": [a.value for a in OverrideAction],
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Creating override for finding {finding_id} in contract {contract_id}")

        # Create override object
        override = UserOverride(
            finding_id=finding_id,
            contract_id=contract_id,
            action=action_enum,
            user_email=user_email,
            previous_value=req_body.get("previous_value"),
            new_value=req_body.get("new_value"),
            notes=req_body.get("notes"),
            reason=req_body.get("reason"),
            timestamp=datetime.utcnow(),
        )

        # Initialize repository and save
        cosmos_client = get_cosmos_client()
        override_repo = OverrideRepository(cosmos_client.overrides_container)

        created_override = override_repo.create(override)

        logger.info(f"Successfully created override {created_override.id}")

        response_data = {
            "override_id": created_override.id,
            "finding_id": created_override.finding_id,
            "success": True,
            "message": "Override created successfully",
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=201,
            mimetype="application/json",
        )

    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in create_override: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
