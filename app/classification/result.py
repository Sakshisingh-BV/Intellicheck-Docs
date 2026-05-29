# app/classification/result.py

from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    """
    Holds the output of document classification.

    Attributes:
        document_type:    Canonical machine name, e.g. "aadhaar_card".
        display_name:     Human-readable name, e.g. "Aadhaar Card".
        confidence:       Score between 0.0 and 1.0.
        matched_keywords: Keywords from the rules that were found in the text.
        extracted_fields: Dict of field_name → extracted value (via regex).
        all_scores:       Scores for every document type (useful for debugging).
    """

    document_type: str = "unknown"
    display_name: str = "Unknown Document"
    confidence: float = 0.0
    matched_keywords: list = field(default_factory=list)
    extracted_fields: dict = field(default_factory=dict)
    all_scores: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON responses."""
        return {
            "document_type": self.document_type,
            "display_name": self.display_name,
            "confidence": round(self.confidence, 4),
            "matched_keywords": self.matched_keywords,
            "extracted_fields": self.extracted_fields,
            "all_scores": {
                k: round(v, 4) for k, v in self.all_scores.items()
            },
        }
