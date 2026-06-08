# validator.py
from typing import List
from .matcher import AddressMatcher
from .freshness import FreshnessValidator
from .normalizer import AddressNormalizer


class AddressVerifier:
    """Main orchestrator"""

    @staticmethod
    def verify(customer_address: dict, documents: List[dict]) -> dict:
        """
        Run full verification flow.
        customer_address: dict with keys line1, city, state, pincode.
        documents: list of dicts, each with keys: doc_type, address (dict), extracted_date.
        Returns dict with: matches, conflicts, freshness_issues, overall_status, is_valid.
        """
        matches = []
        conflicts = []
        freshness_issues = []

        # Step 1: Match each document
        for doc in documents:
            doc_addr = doc.get("address", {})
            match = AddressMatcher.compare(customer_address, doc_addr)
            match["doc_source"] = doc.get("doc_type", "unknown")
            matches.append(match)

        # Step 2: Detect conflicts between documents
        conflicts = AddressVerifier._detect_conflicts(documents)

        # Step 3: Check freshness
        for doc in documents:
            is_fresh, msg = FreshnessValidator.validate(doc)
            if not is_fresh:
                freshness_issues.append(msg)

        # Step 4: Decide overall status
        overall_status = AddressVerifier._decide_status(matches, conflicts)

        is_valid = (
            overall_status == "MATCH" and
            len(conflicts) == 0 and
            len(freshness_issues) == 0
        )

        return {
            "customer_address": customer_address,
            "documents": documents,
            "matches": matches,
            "conflicts": conflicts,
            "freshness_issues": freshness_issues,
            "overall_status": overall_status,
            "is_valid": is_valid,
        }

    @staticmethod
    def _detect_conflicts(documents: List[dict]) -> List[str]:
        """Compare documents against each other"""
        conflicts = []

        for i, doc1 in enumerate(documents):
            for doc2 in documents[i+1:]:
                addr1 = doc1.get("address", {})
                addr2 = doc2.get("address", {})
                # Compare cities
                if (AddressNormalizer.normalize_string(addr1.get("city", "")) !=
                    AddressNormalizer.normalize_string(addr2.get("city", ""))):
                    conflicts.append(
                        f"{doc1.get('doc_type', 'unknown')} ({addr1.get('city', '')}) vs "
                        f"{doc2.get('doc_type', 'unknown')} ({addr2.get('city', '')})"
                    )

        return conflicts

    @staticmethod
    def _decide_status(matches: list, conflicts: list) -> str:
        """Simple logic for overall status"""
        if not matches:
            return "NO_MATCH"

        # If any conflict, max is PARTIAL_MATCH
        if conflicts:
            return "PARTIAL_MATCH"

        # Count full matches
        full_matches = sum(
            1 for m in matches if m.get("status") == "MATCH"
        )

        if full_matches == len(matches):
            return "MATCH"
        elif full_matches > 0:
            return "PARTIAL_MATCH"
        else:
            return "NO_MATCH"