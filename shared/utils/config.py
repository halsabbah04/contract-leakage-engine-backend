"""Configuration management for Azure Functions app."""

import os
from functools import lru_cache
from typing import List


class Settings:
    """Application settings loaded from environment variables.

    Environment variables are read at instance creation time to ensure
    Azure Functions has loaded them from local.settings.json first.
    """

    def __init__(self) -> None:
        # Azure Functions
        self.FUNCTIONS_WORKER_RUNTIME: str = os.getenv("FUNCTIONS_WORKER_RUNTIME", "python")

        # Cosmos DB
        self.COSMOS_CONNECTION_STRING: str = os.getenv("CosmosDBConnectionString", "")
        self.COSMOS_DATABASE_NAME: str = os.getenv("CosmosDBDatabaseName", "ContractLeakageDB")
        self.COSMOS_CONTRACTS_CONTAINER: str = os.getenv("CosmosDBContractsContainer", "contracts")
        self.COSMOS_CLAUSES_CONTAINER: str = os.getenv("CosmosDBClausesContainer", "clauses")
        self.COSMOS_FINDINGS_CONTAINER: str = os.getenv("CosmosDBFindingsContainer", "leakage_findings")
        self.COSMOS_SESSIONS_CONTAINER: str = os.getenv("CosmosDBSessionsContainer", "analysis_sessions")
        self.COSMOS_OVERRIDES_CONTAINER: str = os.getenv("CosmosDBOverridesContainer", "user_overrides")
        self.COSMOS_OBLIGATIONS_CONTAINER: str = os.getenv("CosmosDBObligationsContainer", "obligations")

        # Azure Blob Storage
        self.STORAGE_CONNECTION_STRING: str = os.getenv("StorageConnectionString", "")
        self.STORAGE_CONTAINER_NAME: str = os.getenv("StorageContainerName", "contracts")

        # Azure OpenAI
        self.AZURE_OPENAI_API_KEY: str = os.getenv("OpenAIKey", "")
        self.AZURE_OPENAI_ENDPOINT: str = os.getenv("OpenAIEndpoint", "")
        self.AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("OpenAIDeploymentName", "gpt-52-deployment")
        self.AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv(
            "OpenAIEmbeddingDeploymentName", "text-embedding-3-large"
        )
        self.AZURE_OPENAI_API_VERSION: str = os.getenv("OpenAIAPIVersion", "2024-08-01-preview")
        self.AZURE_OPENAI_MAX_TOKENS: int = int(os.getenv("OpenAIMaxTokens", "4000"))
        self.AZURE_OPENAI_TEMPERATURE: float = float(os.getenv("OpenAITemperature", "0.2"))
        self.EMBEDDING_DIMENSIONS: int = int(os.getenv("EmbeddingDimensions", "3072"))

        # Azure AI Search
        self.AZURE_SEARCH_ENDPOINT: str = os.getenv("SearchServiceEndpoint", "")
        self.AZURE_SEARCH_API_KEY: str = os.getenv("SearchServiceKey", "")
        self.AZURE_SEARCH_INDEX_NAME: str = os.getenv("SearchIndexName", "clauses-index")
        self.AZURE_SEARCH_API_VERSION: str = os.getenv("SearchAPIVersion", "2023-11-01")

        # Azure Document Intelligence
        self.DOC_INTEL_ENDPOINT: str = os.getenv("DocumentIntelligenceEndpoint", "")
        self.DOC_INTEL_KEY: str = os.getenv("DocumentIntelligenceKey", "")
        self.DOC_INTEL_API_VERSION: str = os.getenv("DocumentIntelligenceAPIVersion", "2023-07-31")

        # Application Insights
        self.APPINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.ENABLE_DEBUG_LOGGING: bool = os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true"

        # File Upload Settings
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
        self.ALLOWED_FILE_EXTENSIONS: List[str] = os.getenv("ALLOWED_FILE_EXTENSIONS", "pdf,docx,doc,txt").split(",")

        # Rules Engine
        self.RULES_FILE_PATH: str = os.getenv("RULES_FILE_PATH", "rules/leakage_rules.yaml")

        # Default Analysis Parameters
        self.DEFAULT_INFLATION_RATE: float = float(os.getenv("DEFAULT_INFLATION_RATE", "0.03"))
        self.DEFAULT_CONFIDENCE_THRESHOLD: float = float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.7"))

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def validate(self) -> None:
        """Validate that required settings are present."""
        required_settings = [
            ("CosmosDBConnectionString", self.COSMOS_CONNECTION_STRING),
            ("StorageConnectionString", self.STORAGE_CONNECTION_STRING),
            ("OpenAIKey", self.AZURE_OPENAI_API_KEY),
            ("OpenAIEndpoint", self.AZURE_OPENAI_ENDPOINT),
            ("SearchServiceEndpoint", self.AZURE_SEARCH_ENDPOINT),
            ("SearchServiceKey", self.AZURE_SEARCH_API_KEY),
            ("DocumentIntelligenceEndpoint", self.DOC_INTEL_ENDPOINT),
            ("DocumentIntelligenceKey", self.DOC_INTEL_KEY),
        ]

        missing = [name for name, value in required_settings if not value]

        if missing:
            raise ValueError(
                f"Missing required configuration settings: {', '.join(missing)}. "
                "Please check your local.settings.json or Azure Function App configuration."
            )


# Global settings instance - created lazily
_settings: Settings | None = None


def get_settings(validate: bool = True) -> Settings:
    """Get settings instance.

    Args:
        validate: If True, validate required settings are present.
                  Set to False for basic operations like logging setup.

    Returns:
        Settings instance with current environment variable values.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    if validate:
        _settings.validate()
    return _settings


def reset_settings() -> None:
    """Reset cached settings. Useful for testing."""
    global _settings
    _settings = None
