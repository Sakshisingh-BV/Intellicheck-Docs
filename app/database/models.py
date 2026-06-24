"""
Database models for job tracking.

Stores processing jobs and their results in PostgreSQL for audit/history.
"""

from sqlalchemy import Column, String, JSON, Text, DateTime
from sqlalchemy.sql import func

from app.database.base import Base


class Job(Base):
    """
    Represents a document processing job.

    Lifecycle:
        queued → processing → completed | failed
    """

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, doc="UUID job identifier")
    doc_id = Column(String(36), nullable=False, index=True, doc="Document UUID")
    filename = Column(String(255), nullable=False, doc="Original uploaded filename")

    status = Column(
        String(20),
        nullable=False,
        default="queued",
        index=True,
        doc="Job status: queued | processing | completed | failed",
    )
    step = Column(
        String(50),
        nullable=True,
        doc="Current processing step (e.g. PREPROCESSING, OCR)",
    )

    features = Column(
        JSON,
        nullable=True,
        doc="Requested feature set: stamp, signature, address, idproof",
    )
    result = Column(JSON, nullable=True, doc="Final processing result JSON")
    error = Column(Text, nullable=True, doc="Error message if job failed")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when job completed or failed",
    )

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {
            "job_id": self.id,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "status": self.status,
            "step": self.step,
            "features": self.features,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
