# freshness.py
from datetime import datetime, timedelta


# Freshness window in days per doc type (default 90)
FRESHNESS_WINDOW = {
    "utility_bill": 90,
    "bank_statement": 90,
    "rental_agreement": 180,
    "aadhaar_card": 3650,    # 10 years
    "passport": 3650,
    "driving_license": 3650,
}


class FreshnessValidator:
    """Check if documents are recent enough"""

    @staticmethod
    def validate(doc: dict) -> tuple:
        """
        Check if document is fresh.
        doc: dict with keys doc_type (str) and extracted_date (datetime or None).
        Returns: (is_fresh, message)
        """
        extracted_date = doc.get("extracted_date")
        if not extracted_date:
            return True, "No date on document"

        doc_type = doc.get("doc_type", "")
        window_days = FRESHNESS_WINDOW.get(doc_type, 90)
        threshold = datetime.now() - timedelta(days=window_days)

        is_fresh = extracted_date >= threshold

        if is_fresh:
            return True, ""

        age_days = (datetime.now() - extracted_date).days
        message = f"{doc_type} is {age_days} days old (> {window_days} days)"

        return False, message