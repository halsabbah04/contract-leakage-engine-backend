"""Azure Document Intelligence (Form Recognizer) OCR service."""

import time

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from ..utils.config import get_settings
from ..utils.exceptions import OCRError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings()


class OCRService:
    """Service for OCR using Azure Document Intelligence."""

    def __init__(self):
        """Initialize OCR service."""
        try:
            self.client = DocumentAnalysisClient(
                endpoint=settings.DOC_INTEL_ENDPOINT,
                credential=AzureKeyCredential(settings.DOC_INTEL_KEY),
            )
            logger.info("OCR service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OCR service: {str(e)}")
            raise OCRError(f"Failed to initialize Azure Document Intelligence: {str(e)}")

    def extract_text_from_pdf(self, file_content: bytes, filename: str) -> tuple[str, dict]:
        """
        Extract text from PDF using Document Intelligence.

        Uses the prebuilt-read model which is optimized for text extraction
        from documents including scanned PDFs.

        Args:
            file_content: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            Tuple of (extracted_text, metadata)
            - extracted_text: Full text content
            - metadata: Dict with page_count, confidence, language, etc.

        Raises:
            OCRError: If extraction fails
        """
        try:
            logger.info(f"Starting OCR for PDF: {filename}")

            # Begin analysis using prebuilt-read model
            poller = self.client.begin_analyze_document(model_id="prebuilt-read", document=file_content)

            # Wait for completion (with timeout)
            logger.info("Waiting for OCR analysis to complete...")
            result = poller.result()

            # Extract text content
            extracted_text = result.content

            # Build metadata
            metadata = {
                "page_count": len(result.pages),
                "language": result.languages[0] if result.languages else "unknown",
                "confidence": self._calculate_average_confidence(result),
                "model_id": "prebuilt-read",
                "api_version": settings.DOC_INTEL_API_VERSION,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "extraction_timestamp": time.time(),
            }

            logger.info(
                f"OCR completed: {metadata['page_count']} pages, "
                f"{metadata['character_count']} chars, "
                f"confidence: {metadata['confidence']:.2f}"
            )

            return extracted_text, metadata

        except HttpResponseError as e:
            logger.error(f"Azure Document Intelligence API error: {str(e)}")
            raise OCRError(f"OCR API error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error during OCR: {str(e)}")
            raise OCRError(f"OCR extraction failed: {str(e)}")

    def extract_text_from_docx(self, file_content: bytes, filename: str) -> tuple[str, dict]:
        """
        Extract text from DOCX using Document Intelligence.

        Args:
            file_content: DOCX file content as bytes
            filename: Original filename (for logging)

        Returns:
            Tuple of (extracted_text, metadata)

        Raises:
            OCRError: If extraction fails
        """
        try:
            logger.info(f"Starting text extraction from DOCX: {filename}")

            # Use same prebuilt-read model (supports DOCX)
            poller = self.client.begin_analyze_document(model_id="prebuilt-read", document=file_content)

            logger.info("Waiting for analysis to complete...")
            result = poller.result()

            # Extract text
            extracted_text = result.content

            # Build metadata
            metadata = {
                "page_count": len(result.pages),
                "language": result.languages[0] if result.languages else "unknown",
                "confidence": self._calculate_average_confidence(result),
                "model_id": "prebuilt-read",
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "extraction_timestamp": time.time(),
            }

            logger.info(
                f"Text extraction completed: {metadata['page_count']} pages, " f"{metadata['character_count']} chars"
            )

            return extracted_text, metadata

        except HttpResponseError as e:
            logger.error(f"Azure Document Intelligence API error: {str(e)}")
            raise OCRError(f"Text extraction API error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {str(e)}")
            raise OCRError(f"Text extraction failed: {str(e)}")

    def extract_text(self, file_content: bytes, filename: str, file_type: str) -> tuple[str, dict]:
        """
        Extract text from document (auto-detect type).

        Args:
            file_content: File content as bytes
            filename: Original filename
            file_type: File extension (pdf, docx, doc)

        Returns:
            Tuple of (extracted_text, metadata)

        Raises:
            OCRError: If extraction fails or unsupported type
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            return self.extract_text_from_pdf(file_content, filename)
        elif file_type in ["docx", "doc"]:
            return self.extract_text_from_docx(file_content, filename)
        else:
            raise OCRError(f"Unsupported file type for OCR: {file_type}")

    def _calculate_average_confidence(self, result) -> float:
        """
        Calculate average confidence score from OCR result.

        Args:
            result: Document analysis result

        Returns:
            Average confidence (0.0 to 1.0)
        """
        try:
            if not result.pages:
                return 0.0

            # Get confidence from lines
            total_confidence = 0.0
            line_count = 0

            for page in result.pages:
                for line in page.lines:
                    if hasattr(line, "confidence") and line.confidence is not None:
                        total_confidence += line.confidence
                        line_count += 1

            if line_count == 0:
                # If no line confidence, use a default high confidence
                # (Document Intelligence is generally very accurate)
                return 0.95

            return total_confidence / line_count

        except Exception as e:
            logger.warning(f"Could not calculate confidence: {str(e)}")
            return 0.0

    def extract_with_layout(self, file_content: bytes, filename: str) -> tuple[str, dict, list]:
        """
        Extract text with layout information (advanced).

        This preserves structural information like tables, sections, etc.
        Useful for future enhancements.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Tuple of (text, metadata, layout_elements)

        Raises:
            OCRError: If extraction fails
        """
        try:
            logger.info(f"Starting layout-aware extraction: {filename}")

            poller = self.client.begin_analyze_document(model_id="prebuilt-read", document=file_content)

            result = poller.result()

            # Extract text
            text = result.content

            # Extract layout elements
            layout_elements = []

            for page in result.pages:
                page_elements = {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "lines": [],
                }

                for line in page.lines:
                    page_elements["lines"].append(
                        {
                            "text": line.content,
                            "bounding_box": (line.polygon if hasattr(line, "polygon") else None),
                            "confidence": (line.confidence if hasattr(line, "confidence") else None),
                        }
                    )

                layout_elements.append(page_elements)

            # Metadata
            metadata = {
                "page_count": len(result.pages),
                "language": result.languages[0] if result.languages else "unknown",
                "has_layout": True,
                "character_count": len(text),
                "extraction_timestamp": time.time(),
            }

            logger.info(f"Layout extraction completed: {metadata['page_count']} pages")

            return text, metadata, layout_elements

        except Exception as e:
            logger.error(f"Layout extraction failed: {str(e)}")
            raise OCRError(f"Layout extraction failed: {str(e)}")
