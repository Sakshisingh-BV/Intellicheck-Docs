# app/classification/__init__.py

from app.classification.classifier import DocumentClassifier
from app.classification.result import ClassificationResult

__all__ = ["DocumentClassifier", "ClassificationResult"]
