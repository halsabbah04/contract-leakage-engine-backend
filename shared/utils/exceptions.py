"""Custom exceptions for the application."""


class ContractLeakageEngineError(Exception):
    """Base exception for all application errors."""
    pass


class ConfigurationError(ContractLeakageEngineError):
    """Raised when there's a configuration problem."""
    pass


class DocumentProcessingError(ContractLeakageEngineError):
    """Raised when document processing fails."""
    pass


class OCRError(DocumentProcessingError):
    """Raised when OCR extraction fails."""
    pass


class ClauseExtractionError(DocumentProcessingError):
    """Raised when clause extraction fails."""
    pass


class DatabaseError(ContractLeakageEngineError):
    """Raised when database operations fail."""
    pass


class StorageError(ContractLeakageEngineError):
    """Raised when blob storage operations fail."""
    pass


class AIServiceError(ContractLeakageEngineError):
    """Raised when AI service calls fail."""
    pass


class OpenAIError(AIServiceError):
    """Raised when Azure OpenAI calls fail."""
    pass


class SearchServiceError(AIServiceError):
    """Raised when Azure AI Search operations fail."""
    pass


class EmbeddingServiceError(AIServiceError):
    """Raised when embedding generation fails."""
    pass


class RAGServiceError(AIServiceError):
    """Raised when RAG operations fail."""
    pass


class AIDetectionError(AIServiceError):
    """Raised when AI-powered detection fails."""
    pass


class ValidationError(ContractLeakageEngineError):
    """Raised when data validation fails."""
    pass


class FileUploadError(ContractLeakageEngineError):
    """Raised when file upload fails."""
    pass


class UnsupportedFileTypeError(FileUploadError):
    """Raised when uploaded file type is not supported."""
    pass


class FileSizeExceededError(FileUploadError):
    """Raised when uploaded file exceeds size limit."""
    pass


class LeakageDetectionError(ContractLeakageEngineError):
    """Raised when leakage detection fails."""
    pass


class RulesEngineError(LeakageDetectionError):
    """Raised when rules engine execution fails."""
    pass


class ImpactCalculationError(ContractLeakageEngineError):
    """Raised when impact calculation fails."""
    pass


class ReportGenerationError(ContractLeakageEngineError):
    """Raised when report generation fails."""
    pass


class ContractNotFoundError(ContractLeakageEngineError):
    """Raised when a requested contract is not found."""
    pass


class AnalysisNotFoundError(ContractLeakageEngineError):
    """Raised when analysis results are not found."""
    pass
