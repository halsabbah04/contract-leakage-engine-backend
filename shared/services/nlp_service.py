"""NLP service for clause analysis and entity extraction using spaCy."""

import re
from typing import Dict, List, Optional, Tuple

import spacy
from spacy.tokens import Doc

from ..models.clause import ClauseType, ExtractedEntities
from ..utils.exceptions import ClauseExtractionError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)


class NLPService:
    """Service for NLP-based clause analysis and entity extraction."""

    def __init__(self):
        """Initialize NLP service with spaCy model."""
        try:
            logger.info("Loading spaCy model...")
            # Load English language model
            self.nlp = spacy.load("en_core_web_lg")

            # Add custom pipeline components if needed
            logger.info("NLP service initialized with en_core_web_lg")

        except OSError:
            logger.error("spaCy model not found. Please run: python -m spacy download en_core_web_lg")
            raise ClauseExtractionError("spaCy model not found. Install with: python -m spacy download en_core_web_lg")
        except Exception as e:
            logger.error(f"Failed to initialize NLP service: {str(e)}")
            raise ClauseExtractionError(f"Failed to initialize NLP: {str(e)}")

        # Clause classification keywords
        self.clause_keywords = {
            ClauseType.PRICING: [
                "price",
                "pricing",
                "fee",
                "fees",
                "rate",
                "rates",
                "cost",
                "costs",
                "charge",
                "charges",
                "payment amount",
                "consideration",
            ],
            ClauseType.PAYMENT: [
                "payment",
                "pay",
                "invoice",
                "invoicing",
                "billing",
                "installment",
                "due date",
                "payment terms",
                "net 30",
                "net 60",
            ],
            ClauseType.TERMINATION: [
                "termination",
                "terminate",
                "cancel",
                "cancellation",
                "end agreement",
                "discontinue",
                "cessation",
            ],
            ClauseType.RENEWAL: [
                "renewal",
                "renew",
                "extension",
                "extend",
                "term extension",
            ],
            ClauseType.AUTO_RENEWAL: [
                "auto-renew",
                "automatic renewal",
                "automatically renew",
                "unless terminated",
                "evergreen",
            ],
            ClauseType.SERVICE_LEVEL: [
                "service level",
                "sla",
                "uptime",
                "availability",
                "performance",
                "response time",
                "resolution time",
            ],
            ClauseType.LIABILITY: [
                "liability",
                "liable",
                "indemnify",
                "indemnification",
                "limitation of liability",
                "damages",
                "consequential damages",
            ],
            ClauseType.PENALTIES: [
                "penalty",
                "penalties",
                "liquidated damages",
                "late fee",
                "fine",
                "fines",
            ],
            ClauseType.DISCOUNTS: [
                "discount",
                "rebate",
                "volume discount",
                "early payment discount",
            ],
            ClauseType.WARRANTY: [
                "warranty",
                "warrant",
                "warranties",
                "guarantee",
                "representation",
            ],
            ClauseType.CONFIDENTIALITY: [
                "confidential",
                "confidentiality",
                "non-disclosure",
                "nda",
                "proprietary information",
                "trade secret",
            ],
            ClauseType.INTELLECTUAL_PROPERTY: [
                "intellectual property",
                "ip",
                "copyright",
                "trademark",
                "patent",
                "proprietary rights",
                "ownership",
            ],
        }

        # Risk signal patterns
        self.risk_patterns = {
            "no_price_escalation": r"(?:price|fee|rate)s?\s+(?:shall|will)?\s*(?:remain)?\s*(?:fixed|constant)",
            "auto_renewal": r"(?:auto(?:matic)?(?:ally)?\s+renew|evergreen)",
            "no_termination_clause": r"(?:perpetual|indefinite|no\s+termination)",
            "unlimited_liability": r"(?:unlimited\s+liability|no\s+cap\s+on\s+liability)",
            "no_sla": r"(?:no\s+service\s+level|without\s+guarantee)",
            "missing_penalty": r"(?:no\s+penalty|without\s+penalties)",
        }

    def analyze_clause(self, clause_text: str, context: Optional[str] = None) -> Dict:
        """
        Analyze a clause using NLP.

        Args:
            clause_text: Clause text to analyze
            context: Optional surrounding context

        Returns:
            Dictionary with analysis results
        """
        try:
            # Process with spaCy
            doc = self.nlp(clause_text)

            # Extract entities
            entities = self._extract_entities(doc)

            # Classify clause type
            clause_type, confidence = self._classify_clause_type(clause_text)

            # Detect risk signals
            risk_signals = self._detect_risk_signals(clause_text)

            # Generate normalized summary
            summary = self._generate_summary(clause_text, clause_type)

            analysis = {
                "clause_type": clause_type,
                "classification_confidence": confidence,
                "entities": entities,
                "risk_signals": risk_signals,
                "normalized_summary": summary,
                "word_count": len(clause_text.split()),
                "sentence_count": len(list(doc.sents)),
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing clause: {str(e)}")
            raise ClauseExtractionError(f"Clause analysis failed: {str(e)}")

    def _extract_entities(self, doc: Doc) -> ExtractedEntities:
        """
        Extract named entities from spaCy Doc.

        Args:
            doc: spaCy Doc object

        Returns:
            ExtractedEntities object
        """
        entities = ExtractedEntities(currency=None)

        for ent in doc.ents:
            if ent.label_ == "MONEY":
                # Extract monetary amounts
                amount = self._parse_money(ent.text)
                if amount:
                    entities.amounts.append(amount)
            elif ent.label_ == "DATE":
                # Extract dates
                entities.dates.append(ent.text)
            elif ent.label_ == "PERCENT":
                # Extract percentages
                percentage = self._parse_percentage(ent.text)
                if percentage:
                    entities.percentages.append(percentage)
            elif ent.label_ in ["ORG", "PERSON"]:
                # Extract parties
                entities.parties.append(ent.text)

        # Extract currency (look for currency symbols/codes)
        currency = self._extract_currency(doc.text)
        if currency:
            entities.currency = currency

        # Extract monetary values that spaCy might miss (non-standard currencies like BHD)
        additional_amounts = self._extract_monetary_values(doc.text)
        for amount in additional_amounts:
            if amount not in entities.amounts:
                entities.amounts.append(amount)

        # Extract numerical rates
        rates = self._extract_rates(doc.text)
        entities.rates.extend(rates)

        # Extract durations
        durations = self._extract_durations(doc.text)
        entities.durations.extend(durations)

        return entities

    def _classify_clause_type(self, clause_text: str) -> Tuple[str, float]:
        """
        Classify clause type based on keywords.

        Args:
            clause_text: Clause text

        Returns:
            Tuple of (clause_type, confidence)
        """
        clause_lower = clause_text.lower()

        # Count keyword matches for each type
        type_scores = {}

        for clause_type, keywords in self.clause_keywords.items():
            score = sum(1 for keyword in keywords if keyword in clause_lower)
            if score > 0:
                type_scores[clause_type] = score

        if not type_scores:
            return ClauseType.OTHER, 0.5

        # Get type with highest score
        best_type = max(type_scores, key=lambda k: type_scores[k])
        max_score = type_scores[best_type]

        # Calculate confidence (normalize score)
        total_keywords = len(self.clause_keywords.get(best_type, []))
        confidence = min(max_score / total_keywords, 1.0) if total_keywords > 0 else 0.5

        return best_type, confidence

    def _detect_risk_signals(self, clause_text: str) -> List[str]:
        """
        Detect risk signals in clause text.

        Args:
            clause_text: Clause text

        Returns:
            List of detected risk signal names
        """
        signals = []

        for signal_name, pattern in self.risk_patterns.items():
            if re.search(pattern, clause_text, re.IGNORECASE):
                signals.append(signal_name)
                logger.info(f"Risk signal detected: {signal_name}")

        return signals

    def _generate_summary(self, clause_text: str, clause_type: str) -> str:
        """
        Generate normalized summary of clause.

        Args:
            clause_text: Original clause text
            clause_type: Classified type

        Returns:
            Concise summary string
        """
        # For POC, create simple summary
        # In production, use extractive summarization or GPT

        # Truncate and clean
        summary = clause_text[:200]

        # If truncated, find last complete sentence
        if len(clause_text) > 200:
            last_period = summary.rfind(".")
            if last_period > 50:
                summary = summary[: last_period + 1]
            else:
                summary = summary + "..."

        # Clean whitespace
        summary = re.sub(r"\s+", " ", summary).strip()

        return summary

    def _parse_money(self, text: str) -> Optional[float]:
        """Parse monetary amount from text, handling multipliers like million/billion."""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r"[$£€¥,]", "", text)

            # Check for multipliers (million, billion, thousand)
            text_lower = cleaned.lower()
            multiplier = 1.0
            if "billion" in text_lower:
                multiplier = 1_000_000_000
            elif "million" in text_lower:
                multiplier = 1_000_000
            elif "thousand" in text_lower or " k" in text_lower:
                multiplier = 1_000

            # Extract number
            match = re.search(r"\d+(?:\.\d+)?", cleaned)
            if match:
                value = float(match.group()) * multiplier
                return value
        except (ValueError, AttributeError, TypeError) as e:
            logger.debug(f"Failed to parse money from '{text}': {e}")
        return None

    def _parse_percentage(self, text: str) -> Optional[float]:
        """Parse percentage from text."""
        try:
            # Extract number before %
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if match:
                return float(match.group(1))
        except (ValueError, AttributeError, TypeError) as e:
            logger.debug(f"Failed to parse percentage from '{text}': {e}")
        return None

    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency code from text."""
        # Common currency patterns
        currency_patterns = {
            "USD": r"\$|USD|US\s*\$|U\.S\.\s*\$",
            "EUR": r"€|EUR",
            "GBP": r"£|GBP",
            "BHD": r"BHD|BD\s+\d",
            "SAR": r"SAR",
            "AED": r"AED",
            "KWD": r"KWD",
            "QAR": r"QAR",
            "OMR": r"OMR",
        }

        for currency, pattern in currency_patterns.items():
            if re.search(pattern, text):
                return currency

        return None

    def _extract_monetary_values(self, text: str) -> List[float]:
        """
        Extract monetary values from text using regex patterns.
        Catches values that spaCy might miss (non-standard currencies like BHD).

        Args:
            text: Text to search

        Returns:
            List of extracted monetary values
        """
        amounts = []

        # Pattern for currency code followed by amount (e.g., "BHD 7,650,000")
        # Supports: BHD, USD, EUR, GBP, SAR, AED, KWD, QAR, OMR
        currency_amount_pattern = r"(?:BHD|USD|EUR|GBP|SAR|AED|KWD|QAR|OMR)\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|thousand|k)?"

        matches = re.finditer(currency_amount_pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Parse the amount
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)

                # Check for multipliers
                full_match = match.group(0).lower()
                if "billion" in full_match:
                    amount *= 1_000_000_000
                elif "million" in full_match:
                    amount *= 1_000_000
                elif "thousand" in full_match or " k" in full_match:
                    amount *= 1_000

                if amount > 0:
                    amounts.append(amount)
            except (ValueError, AttributeError) as e:
                logger.debug(f"Failed to parse monetary value from '{match.group(0)}': {e}")

        # Also extract amounts with currency symbols: $1,000,000
        symbol_amount_pattern = r"[$£€]\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|thousand|k)?"

        matches = re.finditer(symbol_amount_pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)

                full_match = match.group(0).lower()
                if "billion" in full_match:
                    amount *= 1_000_000_000
                elif "million" in full_match:
                    amount *= 1_000_000
                elif "thousand" in full_match or " k" in full_match:
                    amount *= 1_000

                if amount > 0 and amount not in amounts:
                    amounts.append(amount)
            except (ValueError, AttributeError) as e:
                logger.debug(f"Failed to parse monetary value from '{match.group(0)}': {e}")

        return amounts

    def _extract_rates(self, text: str) -> List[float]:
        """Extract numerical rates from text."""
        rates = []

        # Pattern: number followed by rate-related word
        pattern = r"(\d+(?:\.\d+)?)\s*(?:per|rate|%)"

        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                rate = float(match.group(1))
                rates.append(rate)
            except (ValueError, AttributeError, TypeError) as e:
                logger.debug(f"Failed to parse rate from match: {e}")

        return rates[:10]  # Limit to 10

    def _extract_durations(self, text: str) -> List[str]:
        """Extract time durations from text."""
        durations = []

        # Pattern: number + time unit
        pattern = r"(\d+)\s*(day|days|week|weeks|month|months|year|years)"

        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            durations.append(match.group(0))

        return durations[:10]  # Limit to 10

    def batch_analyze_clauses(self, clause_texts: List[str]) -> List[Dict]:
        """
        Analyze multiple clauses efficiently.

        Args:
            clause_texts: List of clause texts

        Returns:
            List of analysis results
        """
        logger.info(f"Batch analyzing {len(clause_texts)} clauses")

        results = []
        for i, text in enumerate(clause_texts):
            try:
                analysis = self.analyze_clause(text)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze clause {i}: {str(e)}")
                # Add placeholder result
                results.append(
                    {
                        "clause_type": ClauseType.OTHER,
                        "classification_confidence": 0.0,
                        "entities": ExtractedEntities(currency=None),
                        "risk_signals": [],
                        "normalized_summary": text[:100],
                        "error": str(e),
                    }
                )

        logger.info(f"Batch analysis completed: {len(results)} results")
        return results
