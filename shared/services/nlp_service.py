"""NLP service for clause analysis and entity extraction using spaCy."""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import spacy
from spacy.tokens import Doc

from ..models.clause import Clause, ClauseType, ExtractedEntities
from ..utils.logging import setup_logging
from ..utils.exceptions import ClauseExtractionError

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
            raise ClauseExtractionError(
                "spaCy model not found. Install with: python -m spacy download en_core_web_lg"
            )
        except Exception as e:
            logger.error(f"Failed to initialize NLP service: {str(e)}")
            raise ClauseExtractionError(f"Failed to initialize NLP: {str(e)}")

        # Clause classification keywords
        self.clause_keywords = {
            ClauseType.PRICING: [
                'price', 'pricing', 'fee', 'fees', 'rate', 'rates', 'cost', 'costs',
                'charge', 'charges', 'payment amount', 'consideration'
            ],
            ClauseType.PAYMENT: [
                'payment', 'pay', 'invoice', 'invoicing', 'billing', 'installment',
                'due date', 'payment terms', 'net 30', 'net 60'
            ],
            ClauseType.TERMINATION: [
                'termination', 'terminate', 'cancel', 'cancellation', 'end agreement',
                'discontinue', 'cessation'
            ],
            ClauseType.RENEWAL: [
                'renewal', 'renew', 'extension', 'extend', 'term extension'
            ],
            ClauseType.AUTO_RENEWAL: [
                'auto-renew', 'automatic renewal', 'automatically renew',
                'unless terminated', 'evergreen'
            ],
            ClauseType.SERVICE_LEVEL: [
                'service level', 'sla', 'uptime', 'availability', 'performance',
                'response time', 'resolution time'
            ],
            ClauseType.LIABILITY: [
                'liability', 'liable', 'indemnify', 'indemnification', 'limitation of liability',
                'damages', 'consequential damages'
            ],
            ClauseType.PENALTIES: [
                'penalty', 'penalties', 'liquidated damages', 'late fee', 'fine', 'fines'
            ],
            ClauseType.DISCOUNTS: [
                'discount', 'rebate', 'volume discount', 'early payment discount'
            ],
            ClauseType.WARRANTY: [
                'warranty', 'warrant', 'warranties', 'guarantee', 'representation'
            ],
            ClauseType.CONFIDENTIALITY: [
                'confidential', 'confidentiality', 'non-disclosure', 'nda',
                'proprietary information', 'trade secret'
            ],
            ClauseType.INTELLECTUAL_PROPERTY: [
                'intellectual property', 'ip', 'copyright', 'trademark', 'patent',
                'proprietary rights', 'ownership'
            ]
        }

        # Risk signal patterns
        self.risk_patterns = {
            'no_price_escalation': r'(?:price|fee|rate)s?\s+(?:shall|will)?\s*(?:remain)?\s*(?:fixed|constant)',
            'auto_renewal': r'(?:auto(?:matic)?(?:ally)?\s+renew|evergreen)',
            'no_termination_clause': r'(?:perpetual|indefinite|no\s+termination)',
            'unlimited_liability': r'(?:unlimited\s+liability|no\s+cap\s+on\s+liability)',
            'no_sla': r'(?:no\s+service\s+level|without\s+guarantee)',
            'missing_penalty': r'(?:no\s+penalty|without\s+penalties)',
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
                "sentence_count": len(list(doc.sents))
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
        entities = ExtractedEntities()

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
        best_type = max(type_scores, key=type_scores.get)
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
            last_period = summary.rfind('.')
            if last_period > 50:
                summary = summary[:last_period + 1]
            else:
                summary = summary + "..."

        # Clean whitespace
        summary = re.sub(r'\s+', ' ', summary).strip()

        return summary

    def _parse_money(self, text: str) -> Optional[float]:
        """Parse monetary amount from text."""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$£€¥,]', '', text)
            # Extract number
            match = re.search(r'\d+(?:\.\d+)?', cleaned)
            if match:
                return float(match.group())
        except:
            pass
        return None

    def _parse_percentage(self, text: str) -> Optional[float]:
        """Parse percentage from text."""
        try:
            # Extract number before %
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None

    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency code from text."""
        # Common currency patterns
        currency_patterns = {
            'USD': r'\$|USD|US\$|U\.S\.\$',
            'EUR': r'€|EUR',
            'GBP': r'£|GBP',
            'BHD': r'BHD|BD',
        }

        for currency, pattern in currency_patterns.items():
            if re.search(pattern, text):
                return currency

        return None

    def _extract_rates(self, text: str) -> List[float]:
        """Extract numerical rates from text."""
        rates = []

        # Pattern: number followed by rate-related word
        pattern = r'(\d+(?:\.\d+)?)\s*(?:per|rate|%)'

        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                rate = float(match.group(1))
                rates.append(rate)
            except:
                pass

        return rates[:10]  # Limit to 10

    def _extract_durations(self, text: str) -> List[str]:
        """Extract time durations from text."""
        durations = []

        # Pattern: number + time unit
        pattern = r'(\d+)\s*(day|days|week|weeks|month|months|year|years)'

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
                results.append({
                    "clause_type": ClauseType.OTHER,
                    "classification_confidence": 0.0,
                    "entities": ExtractedEntities(),
                    "risk_signals": [],
                    "normalized_summary": text[:100],
                    "error": str(e)
                })

        logger.info(f"Batch analysis completed: {len(results)} results")
        return results
