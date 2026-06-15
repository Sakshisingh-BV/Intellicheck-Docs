  # app/classification/classifier.py
#
# Rule-based document classifier.
# Uses weighted keyword scoring + regex field extraction.

import re
from app.classification.document_rules import (
    DOCUMENT_RULES,
    PRIMARY_WEIGHT,
    SECONDARY_WEIGHT,
    FIELD_HINT_WEIGHT,
    NEGATIVE_PENALTY,
)
from app.classification.result import ClassificationResult


# Minimum confidence threshold — below this, classify as "unknown"
MIN_CONFIDENCE_THRESHOLD = 0.15


class DocumentClassifier:
    """
    Classifies document type from OCR-extracted text using rule-based
    keyword matching and regex field extraction.

    Usage:
        classifier = DocumentClassifier()
        result = classifier.classify("GOVERNMENT OF INDIA AADHAAR ...")
    """

    def __init__(self, rules=None, threshold=None):
        self.rules = rules or DOCUMENT_RULES
        self.threshold = threshold or MIN_CONFIDENCE_THRESHOLD

    def classify(self, ocr_text: str) -> ClassificationResult:
        """
        Classify a document based on its OCR text.

        Args:
            ocr_text: Full concatenated OCR text from the document.

        Returns:
            ClassificationResult with document_type, confidence,
            matched_keywords, extracted_fields, and all_scores.
        """

        if not ocr_text or not ocr_text.strip():
            return ClassificationResult()

        text_lower = ocr_text.lower()

        all_scores = {}
        all_details = {}

        for rule in self.rules:
            score, matched = self._score_document_type(text_lower, rule)
            type_name = rule["type_name"]
            all_scores[type_name] = score
            all_details[type_name] = {
                "score": score,
                "matched": matched,
                "rule": rule,
            }

        # Find the best-scoring document type
        if not all_scores:
            return ClassificationResult(all_scores=all_scores)

        best_type = max(all_scores, key=all_scores.get)
        best_score = all_scores[best_type]

        # Below threshold → unknown
        if best_score < self.threshold:
            return ClassificationResult(all_scores=all_scores)

        best_rule = all_details[best_type]["rule"]
        matched_keywords = all_details[best_type]["matched"]

        # Extract structured fields using regex patterns
        extracted_fields = self._extract_fields(ocr_text, best_rule)

        return ClassificationResult(
            document_type=best_rule["type_name"],
            display_name=best_rule["display_name"],
            confidence=min(best_score, 1.0),
            matched_keywords=matched_keywords,
            extracted_fields=extracted_fields,
            all_scores=all_scores,
        )

    @staticmethod
    def _keyword_matches(keyword_lower: str, text_lower: str) -> bool:
        """
        Check if a keyword matches within the OCR text.

        For single-word keywords, uses direct substring matching.
        For multi-word keywords, first tries exact substring matching.
        If that fails, checks whether all individual words of the
        keyword appear anywhere in the text. This handles OCR text
        blocks that may not appear in the expected reading order
        (e.g., "Identification Authority of India Unique" instead of
        "Unique Identification Authority of India").
        """
        # Fast path: exact substring match
        if keyword_lower in text_lower:
            return True

        # For multi-word keywords, check if all words are present
        words = keyword_lower.split()
        if len(words) > 1:
            return all(word in text_lower for word in words)

        return False

    def _score_document_type(self, text_lower: str, rule: dict) -> tuple:
        """
        Compute a weighted keyword score for one document type.

        Returns:
            Tuple of (normalized_score, list_of_matched_keywords).
        """

        keywords = rule["keywords"]
        negative_keywords = rule.get("negative_keywords", [])

        raw_score = 0.0
        max_possible = 0.0
        matched = []

        # Score primary keywords
        for kw in keywords.get("primary", []):
            max_possible += PRIMARY_WEIGHT
            if self._keyword_matches(kw.lower(), text_lower):
                raw_score += PRIMARY_WEIGHT
                matched.append(kw)

        # Score secondary keywords
        for kw in keywords.get("secondary", []):
            max_possible += SECONDARY_WEIGHT
            if self._keyword_matches(kw.lower(), text_lower):
                raw_score += SECONDARY_WEIGHT
                matched.append(kw)

        # Score field hint keywords
        for kw in keywords.get("field_hints", []):
            max_possible += FIELD_HINT_WEIGHT
            if self._keyword_matches(kw.lower(), text_lower):
                raw_score += FIELD_HINT_WEIGHT
                matched.append(kw)

        # Apply negative keyword penalties
        for kw in negative_keywords:
            if self._keyword_matches(kw.lower(), text_lower):
                raw_score += NEGATIVE_PENALTY

        # Normalize to 0.0 – 1.0
        if max_possible == 0:
            return 0.0, matched

        normalized = max(raw_score / max_possible, 0.0)
        return normalized, matched

    def _extract_fields(self, ocr_text: str, rule: dict) -> dict:
        """
        Run regex patterns from the rule config against the OCR text.

        Returns:
            Dict of field_name → extracted value string.
            Only includes fields where a match was found.
        """

        field_patterns = rule.get("field_patterns", {})
        extracted = {}

        for field_name, pattern in field_patterns.items():
            match = pattern.search(ocr_text)
            if match:
                try:
                    value = match.group("value").strip()
                    if value:
                        extracted[field_name] = value
                except IndexError:
                    # Pattern doesn't have a 'value' group — use full match
                    extracted[field_name] = match.group(0).strip()

        return extracted
