"""Text preprocessing and segmentation service."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..utils.logging import setup_logging

logger = setup_logging(__name__)


@dataclass
class TextSegment:
    """Represents a segment of text (clause, section, paragraph)."""

    text: str
    segment_type: str  # 'section', 'clause', 'paragraph'
    section_number: Optional[str] = None
    page_number: Optional[int] = None
    start_position: int = 0
    end_position: int = 0
    level: int = 0  # Hierarchical level (0=top, 1=subsection, etc.)


class TextPreprocessingService:
    """Service for cleaning and segmenting contract text."""

    def __init__(self):
        """Initialize text preprocessing service."""
        logger.info("Text preprocessing service initialized")

        # Common contract section patterns
        self.section_patterns = [
            r"^(\d+\.)+\s+",  # 1. 1.1. 1.1.1.
            r"^[A-Z][a-z]*\s+\d+\.?\s+",  # Section 1.
            r"^Article\s+\d+\.?\s+",  # Article 1.
            r"^SECTION\s+\d+\.?\s+",  # SECTION 1.
            r"^\([a-z]\)\s+",  # (a)
            r"^\([0-9]+\)\s+",  # (1)
        ]

    def preprocess_text(self, raw_text: str) -> str:
        """
        Clean and normalize text.

        Args:
            raw_text: Raw extracted text

        Returns:
            Cleaned text
        """
        logger.info("Preprocessing text...")

        text = raw_text

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove page numbers (common patterns)
        text = re.sub(r"\n\s*Page\s+\d+\s+of\s+\d+\s*\n", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

        # Remove header/footer artifacts
        text = re.sub(r"\n\s*-\s*\d+\s*-\s*\n", "\n", text)

        # Normalize line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        logger.info(f"Text preprocessed: {len(text)} characters")
        return text

    def segment_by_clauses(self, text: str) -> List[TextSegment]:
        """
        Segment text into clauses based on structure.

        Uses heuristics to identify clause boundaries:
        - Numbered sections
        - Headers
        - Paragraph breaks

        Args:
            text: Preprocessed text

        Returns:
            List of text segments
        """
        logger.info("Segmenting text into clauses...")

        segments = []
        lines = text.split("\n")

        current_segment: list[str] = []
        current_section = None
        segment_start = 0
        char_position = 0

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            if not line_stripped:
                char_position += len(line) + 1
                continue

            # Check if this line starts a new section
            is_section_header = self._is_section_header(line_stripped)

            if is_section_header:
                # Save previous segment
                if current_segment:
                    segment_text = "\n".join(current_segment).strip()
                    if segment_text:
                        segments.append(
                            TextSegment(
                                text=segment_text,
                                segment_type="clause",
                                section_number=current_section,
                                start_position=segment_start,
                                end_position=char_position,
                            )
                        )

                # Start new segment
                current_section = self._extract_section_number(line_stripped)
                current_segment = [line_stripped]
                segment_start = char_position

            else:
                current_segment.append(line_stripped)

            char_position += len(line) + 1

        # Add final segment
        if current_segment:
            segment_text = "\n".join(current_segment).strip()
            if segment_text:
                segments.append(
                    TextSegment(
                        text=segment_text,
                        segment_type="clause",
                        section_number=current_section,
                        start_position=segment_start,
                        end_position=char_position,
                    )
                )

        logger.info(f"Segmented into {len(segments)} clauses")
        return segments

    def segment_by_paragraphs(self, text: str) -> List[TextSegment]:
        """
        Segment text into paragraphs.

        Args:
            text: Preprocessed text

        Returns:
            List of paragraph segments
        """
        logger.info("Segmenting text into paragraphs...")

        paragraphs = text.split("\n\n")
        segments = []

        char_position = 0
        for para in paragraphs:
            para_stripped = para.strip()
            if para_stripped:
                segments.append(
                    TextSegment(
                        text=para_stripped,
                        segment_type="paragraph",
                        start_position=char_position,
                        end_position=char_position + len(para_stripped),
                    )
                )
            char_position += len(para) + 2  # +2 for \n\n

        logger.info(f"Segmented into {len(segments)} paragraphs")
        return segments

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from text.

        Args:
            text: Contract text

        Returns:
            Dictionary of metadata
        """
        logger.info("Extracting metadata from text...")

        metadata = {
            "character_count": len(text),
            "word_count": len(text.split()),
            "paragraph_count": len(text.split("\n\n")),
            "line_count": len(text.split("\n")),
            "avg_paragraph_length": 0.0,
            "has_numbering": False,
            "estimated_clauses": 0,
        }

        # Check for numbered sections
        for pattern in self.section_patterns:
            if re.search(pattern, text, re.MULTILINE):
                metadata["has_numbering"] = True
                break

        # Estimate clause count
        segments = self.segment_by_clauses(text)
        metadata["estimated_clauses"] = len(segments)

        # Average paragraph length
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            metadata["avg_paragraph_length"] = float(sum(len(p) for p in paragraphs) / len(paragraphs))

        logger.info(f"Metadata extracted: {metadata}")
        return metadata

    def _is_section_header(self, line: str) -> bool:
        """
        Check if a line is a section header.

        Args:
            line: Line of text

        Returns:
            True if likely a section header
        """
        # Check against section patterns
        for pattern in self.section_patterns:
            if re.match(pattern, line):
                return True

        # Check for all-caps headers
        if line.isupper() and len(line.split()) <= 5:
            return True

        return False

    def _extract_section_number(self, line: str) -> Optional[str]:
        """
        Extract section number from header.

        Args:
            line: Header line

        Returns:
            Section number if found
        """
        # Try numbered patterns
        match = re.match(r"^([\d\.]+)", line)
        if match:
            return match.group(1).rstrip(".")

        # Try article/section patterns
        match = re.match(r"^(Article|Section|SECTION)\s+([\d\.]+)", line, re.IGNORECASE)
        if match:
            return match.group(2).rstrip(".")

        # Try lettered patterns
        match = re.match(r"^\(([a-z0-9]+)\)", line)
        if match:
            return match.group(1)

        return None

    def clean_clause_text(self, clause_text: str) -> str:
        """
        Clean individual clause text.

        Args:
            clause_text: Raw clause text

        Returns:
            Cleaned clause text
        """
        text = clause_text

        # Remove section numbering from start
        for pattern in self.section_patterns:
            text = re.sub(f"^{pattern}", "", text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with spaCy)
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if s.strip()]

    def detect_language(self, text: str) -> str:
        """
        Detect language of text.

        Args:
            text: Input text

        Returns:
            Language code (e.g., 'en')
        """
        # For POC, assume English
        # In production, use language detection library
        return "en"

    def extract_key_terms(self, text: str) -> List[str]:
        """
        Extract potential key terms from text.

        Uses simple heuristics:
        - Capitalized phrases
        - Technical terms
        - Quoted terms

        Args:
            text: Input text

        Returns:
            List of key terms
        """
        key_terms = []

        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', text)
        key_terms.extend(quoted)

        # Extract defined terms (patterns like "X means Y")
        definitions = re.findall(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:means|shall mean)", text)
        key_terms.extend(definitions)

        # Remove duplicates
        key_terms = list(set(key_terms))

        return key_terms[:50]  # Limit to top 50
