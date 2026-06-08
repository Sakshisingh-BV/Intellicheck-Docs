# extractor.py — Extract address fields from OCR text using regex
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AddressExtractor:
    """Extract structured address from raw OCR text using regex patterns."""

    # Indian states and UTs (lowercase for matching)
    STATES = [
        "andhra pradesh", "arunachal pradesh", "assam", "bihar",
        "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh",
        "jharkhand", "karnataka", "kerala", "madhya pradesh",
        "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
        "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
        "telangana", "tripura", "uttar pradesh", "uttarakhand",
        "west bengal", "delhi", "chandigarh", "puducherry",
        "jammu and kashmir", "ladakh",
    ]

    # Major Indian cities (lowercase)
    CITIES = [
        "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad",
        "ahmedabad", "chennai", "kolkata", "pune", "jaipur",
        "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal",
        "visakhapatnam", "patna", "vadodara", "ghaziabad", "ludhiana",
        "agra", "nashik", "faridabad", "meerut", "rajkot", "varanasi",
        "srinagar", "aurangabad", "dhanbad", "amritsar", "navi mumbai",
        "allahabad", "prayagraj", "ranchi", "howrah", "coimbatore",
        "raipur", "kochi", "chandigarh", "mysore", "mysuru", "greater noida",
        "noida", "gurgaon", "gurugram", "dehradun",
    ]

    @staticmethod
    def extract_from_text(ocr_text: str) -> Optional[dict]:
        """
        Extract address fields from raw OCR text.
        Returns dict with keys: line1, city, state, pincode — or None.
        """
        if not ocr_text or len(ocr_text.strip()) < 10:
            return None

        text = ocr_text.strip()
        text_lower = text.lower()

        pincode = AddressExtractor._extract_pincode(text)
        state = AddressExtractor._extract_state(text_lower)
        city = AddressExtractor._extract_city(text_lower)
        line1 = AddressExtractor._extract_address_line(text, pincode, state, city)

        # Need at least pincode or (city + state) to be useful
        if not pincode and not (city and state):
            logger.debug("Not enough address fields extracted")
            return None

        return {
            "line1": line1 or "",
            "city": city or "",
            "state": state or "",
            "pincode": pincode or "",
        }

    @staticmethod
    def _extract_pincode(text: str) -> Optional[str]:
        """Extract 6-digit Indian pincode."""
        # PIN followed by code, or standalone 6 digits
        patterns = [
            r'(?:pin\s*(?:code)?|postal\s*code)\s*[:\-]?\s*(\d{6})\b',
            r'\b(\d{6})\b',  # any 6-digit number
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pin = match.group(1)
                # Basic validity: Indian pincodes start with 1-9
                if pin[0] != '0':
                    return pin
        return None

    @staticmethod
    def _extract_state(text_lower: str) -> Optional[str]:
        """Extract Indian state name."""
        # Try labeled patterns first
        labeled = re.search(
            r'(?:state|province)\s*[:\-]?\s*([a-z\s]+?)(?:\s*[,\n\d]|$)',
            text_lower
        )
        if labeled:
            candidate = labeled.group(1).strip()
            for state in AddressExtractor.STATES:
                if state in candidate or candidate in state:
                    return state.title()

        # Fallback: find any known state in text
        for state in AddressExtractor.STATES:
            if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                return state.title()
        return None

    @staticmethod
    def _extract_city(text_lower: str) -> Optional[str]:
        """Extract Indian city name."""
        # Try labeled patterns first
        labeled = re.search(
            r'(?:city|district|town)\s*[:\-]?\s*([a-z\s]+?)(?:\s*[,\n\d]|$)',
            text_lower
        )
        if labeled:
            candidate = labeled.group(1).strip()
            for city in AddressExtractor.CITIES:
                if city in candidate or candidate in city:
                    return city.title()

        # Fallback: find any known city in text
        for city in AddressExtractor.CITIES:
            if re.search(r'\b' + re.escape(city) + r'\b', text_lower):
                return city.title()
        return None

    @staticmethod
    def _extract_address_line(
        text: str,
        pincode: Optional[str],
        state: Optional[str],
        city: Optional[str],
    ) -> Optional[str]:
        """
        Extract address line 1 — the street/locality part.
        Strategy: find the line(s) before pincode/city/state.
        """
        # Try "Address:" labeled field
        labeled = re.search(
            r'(?:address|addr|residential\s*address)\s*[:\-]\s*(.+?)(?:\n|$)',
            text, re.IGNORECASE
        )
        if labeled:
            line = labeled.group(1).strip()
            # Clean out city/state/pincode from the line
            line = AddressExtractor._clean_address_line(line, pincode, state, city)
            if len(line) > 5:
                return line

        # Fallback: take the line just before pincode
        if pincode:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if pincode in line:
                    # Take current line (before pincode) or previous line
                    before_pin = line.split(pincode)[0].strip()
                    if len(before_pin) > 5:
                        return AddressExtractor._clean_address_line(
                            before_pin, pincode, state, city
                        )
                    if i > 0 and len(lines[i - 1].strip()) > 5:
                        return AddressExtractor._clean_address_line(
                            lines[i - 1].strip(), pincode, state, city
                        )

        return None

    @staticmethod
    def _clean_address_line(
        line: str,
        pincode: Optional[str],
        state: Optional[str],
        city: Optional[str],
    ) -> str:
        """Remove pincode/city/state from address line to get just street info."""
        # Strip relation/care-of prefixes (e.g., D/O Sanjay Singh, S/O Kumar) at the start
        line = re.sub(
            r'^(?:[dswc]/[o0])\s+[a-z\s\.]+?(?:,\s*|\s+)',
            '',
            line.strip(),
            flags=re.IGNORECASE
        )

        if pincode:
            line = line.replace(pincode, "")
        if state:
            line = re.sub(re.escape(state), "", line, flags=re.IGNORECASE)
        if city:
            line = re.sub(re.escape(city), "", line, flags=re.IGNORECASE)
        # Clean trailing commas, dashes, spaces
        line = re.sub(r'[\s,\-]+$', '', line)
        line = re.sub(r'^[\s,\-]+', '', line)
        line = re.sub(r'\s+', ' ', line)
        return line.strip()
