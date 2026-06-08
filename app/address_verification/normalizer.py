# normalizer.py
import re
from typing import Dict

class AddressNormalizer:
    """Simple, rule-based normalization"""
    
    # Expansions: common abbreviations
    EXPANSIONS = {
        r'\bM\.G\.\s*Rd\.?\b': 'Mahatma Gandhi Road',
        r'\bMG\s*Rd\.?\b': 'Mahatma Gandhi Road',
        r'\bRd\.?\b': 'Road',
        r'\bSt\.?\b': 'Street',
        r'\bAve\.?\b': 'Avenue',
        r'\bApt\.?\b': 'Apartment',
        r'\bNo\.?\b': 'Number',
        r'\bBlvd\.?\b': 'Boulevard',
        r'\bLn\.?\b': 'Lane',
        r'\bDr\.?\b': 'Drive',
        r'\bOpp\.?\b': 'Opposite',
        r'\bNr\.?\b': 'Near',
        r'\bB\.G\.\s*Rd\.?\b': 'Banjara Gardens Road',
    }
    
    # Normalize spacing and casing
    @staticmethod
    def normalize_string(text: str) -> str:
        if not text:
            return ""
        
        # Lowercase
        text = text.lower().strip()
        
        # Expand abbreviations
        for pattern, expansion in AddressNormalizer.EXPANSIONS.items():
            text = re.sub(pattern, expansion.lower(), text, flags=re.IGNORECASE)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special chars (keep alphanumeric, space, hyphen)
        text = re.sub(r'[^a-z0-9\s\-]', '', text)
        
        return text.strip()
    
    @staticmethod
    def tokenize(text: str) -> set:
        """Break into tokens for fuzzy matching"""
        normalized = AddressNormalizer.normalize_string(text)
        return set(normalized.split())
    
    @staticmethod
    def normalize_pincode(pincode: str) -> str:
        """Just digits, no spaces"""
        return re.sub(r'\D', '', str(pincode))