"""Azure Function: Health Check

Simple health check endpoint to verify API is running.
"""

import json
from datetime import datetime

import azure.functions as func

from shared.utils.config import get_settings
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings(validate=False)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.

    Route: GET /api/health

    Returns:
    - 200: Service is healthy
    """
    logger.info("health check triggered")

    try:
        response_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "AI Contract & Commercial Leakage Engine",
            "version": "1.0.0-poc",
            "runtime": settings.FUNCTIONS_WORKER_RUNTIME,
            "database": {
                "cosmos_db": settings.COSMOS_DATABASE_NAME,
                "connected": bool(settings.COSMOS_CONNECTION_STRING),
            },
        }

        return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return func.HttpResponse(
            json.dumps(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )
