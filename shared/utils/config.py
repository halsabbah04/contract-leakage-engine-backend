"""Configuration management for Azure Functions app."""

import os
from typing import Optional
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # Azure Functions
    FUNCTIONS_WORKER_RUNTIME: str = os.getenv("FUNCTIONS_WORKER_RUNTIME", "python")

    # Cosmos DB
    COSMOS_CONNECTION_STRING: str = os.getenv("CosmosDBConnectionString", "")
    COSMOS_DATABASE_NAME: str = os.getenv("CosmosDBDatabaseName", "ContractLeakageDB")
    COSMOS_CONTRACTS_CONTAINER: str = os.getenv("CosmosDBContractsContainer", "contracts")
    COSMOS_CLAUSES_CONTAINER: str = os.getenv("CosmosDBClausesContainer", "clauses")
    COSMOS_FINDINGS_CONTAINER: str = os.getenv("CosmosDBFindingsContainer", "leakage_findings")
    COSMOS_SESSIONS_CONTAINER: str = os.getenv("CosmosDBSessionsContainer", "analysis_sessions")

    # Azure Blob Storage
    STORAGE_CONNECTION_STRING: str = os.getenv("StorageConnectionString", "")
    STORAGE_CONTAINER_NAME: str = os.getenv("StorageContainerName", "contracts")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = os.getenv("OpenAIKey", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("OpenAIEndpoint", "")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("OpenAIDeploymentName", "gpt-52-deployment")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("OpenAIEmbeddingDeploymentName", "text-embedding-3-large")
    AZURE_OPENAI_API_VERSION: str = os.getenv("OpenAIAPIVersion", "2024-08-01-preview")
    AZURE_OPENAI_MAX_TOKENS: int = int(os.getenv("OpenAIMaxTokens", "4000"))
    AZURE_OPENAI_TEMPERATURE: float = float(os.getenv("OpenAITemperature", "0.2"))
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EmbeddingDimensions", "3072"))

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT: str = os.getenv("SearchServiceEndpoint", "")
    AZURE_SEARCH_API_KEY: str = os.getenv("SearchServiceKey", "")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("SearchIndexName", "clauses-index")
    AZURE_SEARCH_API_VERSION: str = os.getenv("SearchAPIVersion", "2023-11-01")

    # Azure Document Intelligence
    DOC_INTEL_ENDPOINT: str = os.getenv("DocumentIntelligenceEndpoint", "")
    DOC_INTEL_KEY: str = os.getenv("DocumentIntelligenceKey", "")
    DOC_INTEL_API_VERSION: str = os.getenv("DocumentIntelligenceAPIVersion", "2023-07-31")

    # Application Insights
    APPINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DEBUG_LOGGING: bool = os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true"

    # File Upload Settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    ALLOWED_FILE_EXTENSIONS: list = os.getenv("ALLOWED_FILE_EXTENSIONS", "pdf,docx,doc").split(",")

    # Rules Engine
    RULES_FILE_PATH: str = os.getenv("RULES_FILE_PATH", "rules/leakage_rules.yaml")

    # Default Analysis Parameters
    DEFAULT_INFLATION_RATE: float = float(os.getenv("DEFAULT_INFLATION_RATE", "0.03"))
    DEFAULT_CONFIDENCE_THRESHOLD: float = float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.7"))

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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate()
    return settings
