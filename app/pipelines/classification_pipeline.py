# app/pipelines/classification_pipeline.py
#
# Thin orchestrator: OCR parsed results → concatenated text → classifier.
# Keeps the upload route clean and classification logic decoupled.

from app.classification.classifier import DocumentClassifier
from app.classification.result import ClassificationResult


class ClassificationPipeline:
    """
    Bridges OCR output to document classification.

    Usage:
        pipeline = ClassificationPipeline()
        result = pipeline.run(parsed_ocr_results)
    """

    def __init__(self):
        self.classifier = DocumentClassifier()

    def run(self, parsed_ocr_results: list) -> ClassificationResult:
        """
        Classify a document from its parsed OCR results.

        Args:
            parsed_ocr_results: List of dicts with "text" keys,
                                as returned by OCRParser.parse().

        Returns:
            ClassificationResult with document type, confidence,
            matched keywords, and extracted fields.
        """

        # Concatenate all OCR text blocks into a single string
        full_text = " ".join(
            item.get("text", "") for item in parsed_ocr_results
        )

        return self.classifier.classify(full_text)
