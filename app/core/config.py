"""
Centralized application configuration.

All settings are configurable via environment variables with sensible defaults.
"""

# ── Feature Selection ────────────────────────────────────────────────────

ALL_FEATURES = {"stamp", "signature", "address", "idproof"}
DEFAULT_FEATURES = ALL_FEATURES.copy()

# ── Progress Stages ──────────────────────────────────────────────────────

PROGRESS_STAGES = [
    "INITIALIZING",
    "PREPROCESSING",
    "OCR",
    "STAMP_DETECTION",
    "SIGNATURE_DETECTION",
    "ADDRESS_CHECK",
    "ID_PROOF_CHECK",
    "FINALIZING",
]
