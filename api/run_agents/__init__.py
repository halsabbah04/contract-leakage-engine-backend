"""Azure Function: Run Agents

Triggers AI agent execution for a contract.
Currently supports the Obligation Extraction Agent.
"""

import asyncio
import json
from typing import List, Optional

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.services.agent_orchestrator import AgentType, OrchestratorConfig, get_orchestrator
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Trigger agent execution for a contract.

    Route: POST /api/run_agents/{contract_id}

    Query Parameters:
        agents: Comma-separated list of agents to run (optional)
                Available: "obligation"
                Default: all available agents
        parallel: Whether to run agents in parallel (default: true)

    Request Body (optional):
        {
            "agents": ["obligation"],
            "parallel": true,
            "timeout_seconds": 300
        }

    Returns:
        200: Agent execution completed
        404: Contract not found
        500: Server error
    """
    logger.info("run_agents function triggered")

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

        logger.info(f"Running agents for contract: {contract_id}")

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

        # Parse request body if present
        try:
            body = req.get_json() if req.get_body() else {}
        except ValueError:
            body = {}

        # Get agents to run
        agents_param = req.params.get("agents") or body.get("agents")
        agent_types = _parse_agent_types(agents_param)

        # Get parallel setting
        parallel_param = req.params.get("parallel", "true").lower()
        run_parallel = body.get("parallel", parallel_param != "false")

        # Get timeout
        timeout_seconds = body.get("timeout_seconds", 300)

        logger.info(
            f"Agent config: agents={[a.value for a in agent_types]}, "
            f"parallel={run_parallel}, timeout={timeout_seconds}s"
        )

        # Create orchestrator config
        config = OrchestratorConfig(
            agents_to_run=agent_types,
            run_parallel=run_parallel,
            continue_on_failure=True,
            timeout_seconds=timeout_seconds,
        )

        # Get orchestrator and run agents
        orchestrator = get_orchestrator(config)

        # Run async code in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(orchestrator.run_agents(contract_id, agent_types))
        finally:
            loop.close()

        logger.info(
            f"Agent execution complete: {result.successful_agents}/{result.total_agents} successful, "
            f"{result.duration_ms:.0f}ms"
        )

        # Build response
        response_data = {
            "contract_id": contract_id,
            "status": "completed" if result.failed_agents == 0 else "partial",
            "duration_ms": result.duration_ms,
            "agents": {
                "total": result.total_agents,
                "successful": result.successful_agents,
                "failed": result.failed_agents,
                "partial": result.partial_agents,
            },
            "agent_statuses": result.agent_statuses,
            "results": {},
        }

        # Add result summaries for each agent
        for agent_type, agent_result in result.agent_results.items():
            if agent_result:
                if agent_type == "obligation":
                    # Add obligation summary
                    response_data["results"]["obligations"] = {
                        "total_extracted": agent_result.get("summary", {}).get("total_obligations", 0),
                        "by_type": agent_result.get("summary", {}).get("by_type", {}),
                        "by_status": agent_result.get("summary", {}).get("by_status", {}),
                        "due_soon_count": agent_result.get("summary", {}).get("due_soon_count", 0),
                        "overdue_count": agent_result.get("summary", {}).get("overdue_count", 0),
                    }

        # Add errors/warnings if any
        if result.errors:
            response_data["errors"] = result.errors
        if result.warnings:
            response_data["warnings"] = result.warnings

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
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
        logger.error(f"Unexpected error in run_agents: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


def _parse_agent_types(agents_param: Optional[str | List[str]]) -> List[AgentType]:
    """
    Parse agent types from parameter.

    Args:
        agents_param: Comma-separated string or list of agent names

    Returns:
        List of AgentType enums
    """
    if not agents_param:
        # Default: run all available agents
        return [AgentType.OBLIGATION]

    # Handle list input
    if isinstance(agents_param, list):
        agent_names = agents_param
    else:
        # Handle comma-separated string
        agent_names = [a.strip().lower() for a in agents_param.split(",")]

    # Map to enum
    agent_types = []
    for name in agent_names:
        try:
            agent_type = AgentType(name)
            agent_types.append(agent_type)
        except ValueError:
            logger.warning(f"Unknown agent type: {name}")

    # Return default if no valid agents found
    return agent_types if agent_types else [AgentType.OBLIGATION]
