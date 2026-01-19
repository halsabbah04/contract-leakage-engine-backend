"""Azure Function: Export Report

Generate and download analysis reports in PDF or Excel format.
"""

import json
from datetime import datetime

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.services.report_service import ReportService
from shared.utils.exceptions import ContractNotFoundError, ReportGenerationError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Export contract analysis report.

    Route: GET /api/export_report/{contract_id}
    Query Parameters:
        - format: "pdf" or "excel" (default: "pdf")
        - include_clauses: "true" or "false" (default: "false", PDF only)

    Returns:
    - 200: Report file (binary)
    - 400: Invalid parameters
    - 404: Contract not found
    - 500: Server error
    """
    logger.info("export_report function triggered")

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

        # Get format from query parameters
        report_format = req.params.get("format", "pdf").lower()

        if report_format not in ["pdf", "excel"]:
            logger.warning(f"Invalid format requested: {report_format}")
            return func.HttpResponse(
                json.dumps({"error": "format must be 'pdf' or 'excel'"}),
                status_code=400,
                mimetype="application/json",
            )

        # Get include_clauses parameter (PDF only)
        include_clauses = req.params.get("include_clauses", "false").lower() == "true"

        logger.info(f"Exporting {report_format} report for contract {contract_id}")

        # Verify contract exists
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        contract = contract_repo.get_by_contract_id(contract_id)

        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Generate report
        report_service = ReportService()

        if report_format == "pdf":
            logger.info(f"Generating PDF report (include_clauses={include_clauses})")
            report_bytes = report_service.generate_pdf_report(contract_id=contract_id, include_clauses=include_clauses)
            content_type = "application/pdf"
            file_extension = "pdf"

        else:  # excel
            logger.info("Generating Excel report")
            report_bytes = report_service.generate_excel_report(contract_id=contract_id)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_extension = "xlsx"

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_contract_name = contract.contract_name.replace(" ", "_")[:50]
        filename = f"{safe_contract_name}_{timestamp}.{file_extension}"

        logger.info(f"Report generated successfully: {filename} ({len(report_bytes)} bytes)")

        # Return file
        return func.HttpResponse(
            report_bytes,
            status_code=200,
            mimetype=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(report_bytes)),
            },
        )

    except ContractNotFoundError as e:
        logger.error(f"Contract not found: {str(e)}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=404, mimetype="application/json")

    except ReportGenerationError as e:
        logger.error(f"Report generation error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to generate report", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in export_report: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
