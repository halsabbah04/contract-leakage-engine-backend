"""Azure Functions v4 Programming Model Entry Point

This file registers all HTTP endpoints using the v4 model while
keeping the existing api/ folder structure with function implementations.
"""

# Suppress harmless google._upb module cache warning from Azure Functions worker
import warnings
import logging

warnings.filterwarnings("ignore", message=".*google._upb.*")
warnings.filterwarnings("ignore", message=".*Attempt to remove module cache.*")
logging.getLogger("azure.functions._thirdparty.flask.app").setLevel(logging.ERROR)

import azure.functions as func

# Import all function handlers from api/ folder
from api.health import main as health_handler
from api.upload_contract import main as upload_contract_handler
from api.analyze_contract import main as analyze_contract_handler
from api.get_analysis import main as get_analysis_handler
from api.get_contract import main as get_contract_handler
from api.get_clauses import main as get_clauses_handler
from api.get_findings import main as get_findings_handler
from api.list_contracts import main as list_contracts_handler
from api.dismiss_finding import main as dismiss_finding_handler
from api.export_report import main as export_report_handler
from api.create_override import main as create_override_handler
from api.get_overrides import main as get_overrides_handler
from api.get_override_summary import main as get_override_summary_handler

# Create the Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# Health Check - Anonymous
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return health_handler(req)


# Upload Contract
@app.route(route="upload_contract", methods=["POST"])
def upload_contract(req: func.HttpRequest) -> func.HttpResponse:
    return upload_contract_handler(req)


# Analyze Contract
@app.route(route="analyze_contract/{contract_id}", methods=["POST"])
def analyze_contract(req: func.HttpRequest) -> func.HttpResponse:
    return analyze_contract_handler(req)


# Get Analysis
@app.route(route="get_analysis/{contract_id}", methods=["GET"])
def get_analysis(req: func.HttpRequest) -> func.HttpResponse:
    return get_analysis_handler(req)


# Get Contract
@app.route(route="get_contract/{contract_id}", methods=["GET"])
def get_contract(req: func.HttpRequest) -> func.HttpResponse:
    return get_contract_handler(req)


# Get Clauses
@app.route(route="get_clauses/{contract_id}", methods=["GET"])
def get_clauses(req: func.HttpRequest) -> func.HttpResponse:
    return get_clauses_handler(req)


# Get Findings
@app.route(route="get_findings/{contract_id}", methods=["GET"])
def get_findings(req: func.HttpRequest) -> func.HttpResponse:
    return get_findings_handler(req)


# List Contracts
@app.route(route="list_contracts", methods=["GET"])
def list_contracts(req: func.HttpRequest) -> func.HttpResponse:
    return list_contracts_handler(req)


# Dismiss Finding
@app.route(route="dismiss_finding/{contract_id}/{finding_id}", methods=["POST"])
def dismiss_finding(req: func.HttpRequest) -> func.HttpResponse:
    return dismiss_finding_handler(req)


# Export Report
@app.route(route="export_report/{contract_id}", methods=["GET"])
def export_report(req: func.HttpRequest) -> func.HttpResponse:
    return export_report_handler(req)


# Create Override
@app.route(route="overrides/{contract_id}", methods=["POST"])
def create_override(req: func.HttpRequest) -> func.HttpResponse:
    return create_override_handler(req)


# Get Overrides
@app.route(route="overrides/{contract_id}", methods=["GET"])
def get_overrides(req: func.HttpRequest) -> func.HttpResponse:
    return get_overrides_handler(req)


# Get Override Summary
@app.route(route="overrides/{contract_id}/summary", methods=["GET"])
def get_override_summary(req: func.HttpRequest) -> func.HttpResponse:
    return get_override_summary_handler(req)
