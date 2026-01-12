"""Cosmos DB operations and data access layer."""

from .cosmos_client import CosmosDBClient, get_cosmos_client
from .repositories import (
    ContractRepository,
    ClauseRepository,
    FindingRepository,
    SessionRepository
)

__all__ = [
    "CosmosDBClient",
    "get_cosmos_client",
    "ContractRepository",
    "ClauseRepository",
    "FindingRepository",
    "SessionRepository",
]
