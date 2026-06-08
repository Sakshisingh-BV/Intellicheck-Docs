# matcher.py
from difflib import SequenceMatcher
from .normalizer import AddressNormalizer


class AddressMatcher:
    """Compare two addresses, return match status"""

    SIMILARITY_THRESHOLD = 0.85  # Line1 similarity for MATCH
    PARTIAL_THRESHOLD = 0.60     # For PARTIAL_MATCH

    @staticmethod
    def compare(customer_addr: dict, doc_addr: dict) -> dict:
        """
        Compare customer address vs extracted address.
        Both are dicts with keys: line1, city, state, pincode.
        Returns dict with: status, confidence, matched_fields, mismatched_fields, reason.
        """
        matched = []
        mismatched = []
        scores = {}

        # 1. Pincode: exact match (highest priority)
        pincode_match = (
            AddressNormalizer.normalize_pincode(customer_addr.get("pincode", "")) ==
            AddressNormalizer.normalize_pincode(doc_addr.get("pincode", ""))
        )
        if pincode_match:
            matched.append("pincode")
            scores["pincode"] = 1.0
        else:
            mismatched.append("pincode")
            scores["pincode"] = 0.0

        # 2. State: exact match
        state_match = (
            AddressNormalizer.normalize_string(customer_addr.get("state", "")) ==
            AddressNormalizer.normalize_string(doc_addr.get("state", ""))
        )
        if state_match:
            matched.append("state")
            scores["state"] = 1.0
        else:
            mismatched.append("state")
            scores["state"] = 0.0

        # 3. City: fuzzy match
        city_sim = AddressMatcher._similarity(
            customer_addr.get("city", ""), doc_addr.get("city", "")
        )
        if city_sim > 0.85:
            matched.append("city")
            scores["city"] = city_sim
        else:
            mismatched.append("city")
            scores["city"] = city_sim

        # 4. Line1: fuzzy match + containment match (most variation here)
        line1_cust = customer_addr.get("line1", "")
        line1_doc = doc_addr.get("line1", "")
        
        line1_sim = AddressMatcher._similarity(line1_cust, line1_doc)
        is_contained = AddressMatcher._check_containment(line1_cust, line1_doc)
        
        if line1_sim > AddressMatcher.SIMILARITY_THRESHOLD or is_contained:
            matched.append("line1")
            scores["line1"] = max(line1_sim, 1.0 if is_contained else 0.0)
        else:
            mismatched.append("line1")
            scores["line1"] = line1_sim

        # Decide overall status
        confidence = sum(scores.values()) / len(scores) if scores else 0.0

        if pincode_match and state_match and len(matched) >= 3:
            status = "MATCH"
        elif pincode_match and state_match:
            status = "PARTIAL_MATCH"
        elif city_sim > 0.7 or state_match:
            status = "PARTIAL_MATCH"
        else:
            status = "NO_MATCH"

        reason = AddressMatcher._build_reason(matched, mismatched, scores)

        return {
            "status": status,
            "confidence": confidence,
            "matched_fields": matched,
            "mismatched_fields": mismatched,
            "reason": reason,
        }

    @staticmethod
    def _check_containment(text1: str, text2: str) -> bool:
        """Check if one normalized address is contained within the other after removing common terms."""
        import re
        common_words = {
            "house", "no", "flat", "plot", "apartment", "apt", "near", 
            "opposite", "opp", "sector", "pocket", "pock", "sec", "block"
        }
        
        def compress(text: str) -> str:
            t = text.lower().strip()
            # Keep alphanumeric and spaces
            t = re.sub(r'[^a-z0-9\s]', ' ', t)
            words = t.split()
            filtered = [w for w in words if w not in common_words]
            return "".join(filtered)
            
        comp1 = compress(text1)
        comp2 = compress(text2)
        
        if len(comp1) < 2 or len(comp2) < 2:
            return False
            
        return (comp1 in comp2) or (comp2 in comp1)

    @staticmethod
    def _similarity(text1: str, text2: str) -> float:
        """Fuzzy string similarity (0-1)"""
        norm1 = AddressNormalizer.normalize_string(text1)
        norm2 = AddressNormalizer.normalize_string(text2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    @staticmethod
    def _build_reason(matched: list, mismatched: list, scores: dict) -> str:
        if not mismatched:
            return "All fields match perfectly."

        if "pincode" in matched and "state" in matched:
            if "line1" in mismatched:
                return "Pincode, State match, but Address Line 1 differs."
            if "city" in mismatched:
                return "Pincode, State match, but City differs."

        return f"Matched: {', '.join(matched)}. Mismatched: {', '.join(mismatched)}."