# stamp_detection/utils.py - STAMP DETECTION UTILITIES

import cv2
import numpy as np
from typing import List, Dict, Optional
import logging
import requests

logger = logging.getLogger(__name__)


class StampDetectionUtils:
    """Utilities for stamp detection and visualization"""

    @staticmethod
    def has_colored_ink(crop: np.ndarray, min_ink_ratio: float = 0.02) -> bool:
        """Check if cropped region has colored ink (stamp indicator)"""
        try:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            
            # Blue ink
            blue_lower = np.array([100, 50, 50])
            blue_upper = np.array([130, 255, 255])
            
            # Red ink
            red_lower1 = np.array([0, 50, 50])
            red_upper1 = np.array([10, 255, 255])
            red_lower2 = np.array([170, 50, 50])
            red_upper2 = np.array([180, 255, 255])
            
            blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
            red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
            red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
            
            combined = blue_mask | red_mask1 | red_mask2
            ink_ratio = np.count_nonzero(combined) / combined.size
            
            return ink_ratio > min_ink_ratio
        except Exception as e:
            logger.error(f"Error checking ink: {e}")
            return False

    @staticmethod
    def crop_detection(image: np.ndarray, bbox: List[float]) -> np.ndarray:
        """Safely crop region from image"""
        try:
            x1, y1, x2, y2 = map(int, bbox)
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(image.shape[1], x2)
            y2 = min(image.shape[0], y2)
            return image[y1:y2, x1:x2]
        except Exception as e:
            logger.error(f"Error cropping: {e}")
            return None

    @staticmethod
    def draw_detections(image: np.ndarray, detections: List[dict]) -> np.ndarray:
        """Draw bounding boxes with enhanced labels for stamp types"""
        result = image.copy()
        
        colors = {
            'stamp': (0, 255, 0),             # Green
            'signature': (255, 0, 0),         # Red
        }
        
        for det in detections:
            try:
                bbox = det.get('bbox', [])
                label = det.get('label', 'unknown')
                conf = det.get('confidence', 0.0)
                anomalies = det.get('anomalies', [])
                
                x1, y1, x2, y2 = map(int, bbox)
                color = colors.get(label, (255, 255, 255))
                
                # Draw rectangle
                cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
                
                # Label with type
                label_text = f"{label}: {conf:.2f}"
                cv2.putText(result, label_text, (x1, y1 - 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Add anomaly warning
                if anomalies:
                    anomaly_text = f"⚠️ {', '.join(anomalies[:2])}"
                    cv2.putText(result, anomaly_text, (x1, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
            except Exception as e:
                logger.warning(f"Error drawing detection: {e}")
                continue
        
        return result

    @staticmethod
    def verify_estamp_with_authority(certificate_number: str, state: str, 
                                     api_key: Optional[str] = None) -> Dict:
        """
        Optional: Verify e-stamp with issuing authority.
        
        This calls the government e-stamp verification API.
        State-wise APIs:
        - Maharashtra: StampDutyOnline API
        - Gujarat: GSECL API
        - Others: Similar state-level APIs
        
        Args:
            certificate_number: E-stamp cert number (e.g., MH-240101-123456)
            state: Issuing state (e.g., Maharashtra)
            api_key: API key for verification (optional)
        
        Returns:
            {
                "verified": True/False,
                "status": "valid" | "invalid" | "not_available",
                "details": {...},
                "timestamp": "2024-01-15T10:30:00"
            }
        """
        
        try:
            if not api_key:
                logger.warning("No API key provided for e-stamp verification")
                return {
                    "verified": False,
                    "status": "not_available",
                    "message": "Verification service not configured"
                }
            
            # State-specific verification endpoints
            verification_endpoints = {
                "Maharashtra": "https://stampdutyonline.maharashtra.gov.in/verify",
                "Gujarat": "https://gsecl.gujstat.gov.in/verify",
                "Karnataka": "https://stampdoc.karnataka.gov.in/verify",
                "Tamil Nadu": "https://stampdoc.tamilnadu.gov.in/verify",
                "Delhi": "https://delhi-estamp.gov.in/verify"
            }
            
            endpoint = verification_endpoints.get(state)
            if not endpoint:
                return {
                    "verified": False,
                    "status": "not_available",
                    "message": f"Verification not available for {state}"
                }
            
            # Make verification request
            response = requests.post(
                endpoint,
                json={
                    "certificate_number": certificate_number,
                    "api_key": api_key
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "verified": True,
                    "status": data.get("status", "valid"),
                    "details": data,
                    "timestamp": data.get("timestamp")
                }
            else:
                return {
                    "verified": False,
                    "status": "verification_failed",
                    "message": f"API returned {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "verified": False,
                "status": "not_available",
                "message": "Verification service is currently down"
            }
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {
                "verified": False,
                "status": "error",
                "message": str(e)
            }

    @staticmethod
    def check_overlapping_stamps(detections: List[dict], 
                                image_shape: tuple) -> Dict:
        """
        Check for overlapping stamps that might hide content.
        
        Returns:
            {
                "overlapping_pairs": [
                    {
                        "stamp1_index": 0,
                        "stamp2_index": 1,
                        "overlap_percentage": 15.5
                    }
                ],
                "has_suspicious_overlap": True/False
            }
        """
        
        overlapping_pairs = []
        
        for i in range(len(detections)):
            for j in range(i + 1, len(detections)):
                bbox1 = detections[i]["bbox"]
                bbox2 = detections[j]["bbox"]
                
                # Calculate intersection
                x1_min = max(bbox1[0], bbox2[0])
                y1_min = max(bbox1[1], bbox2[1])
                x1_max = min(bbox1[2], bbox2[2])
                y1_max = min(bbox1[3], bbox2[3])
                
                if x1_min < x1_max and y1_min < y1_max:
                    # Calculate overlap area
                    overlap_area = (x1_max - x1_min) * (y1_max - y1_min)
                    bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
                    overlap_pct = (overlap_area / bbox1_area) * 100
                    
                    if overlap_pct > 5:  # More than 5% overlap
                        overlapping_pairs.append({
                            "stamp1_index": i,
                            "stamp2_index": j,
                            "overlap_percentage": round(overlap_pct, 2)
                        })
        
        return {
            "overlapping_pairs": overlapping_pairs,
            "has_suspicious_overlap": len(overlapping_pairs) > 0
        }

    @staticmethod
    def format_stamp_report(detection: Dict) -> str:
        """Format detection result as human-readable report"""
        
        report = f"\n{'='*50}\n"
        report += f"Label: {detection.get('label', 'Unknown')}\n"
        report += f"Confidence: {detection.get('confidence', 0):.2%}\n"
        report += f"Position: {detection.get('bbox')}\n"
        report += f"Ink Confirmed: {detection.get('ink_confirmed', 'N/A')}\n"
        
        if detection.get('anomalies'):
            report += f"\nANOMALIES DETECTED:\n"
            for anomaly in detection.get('anomalies', []):
                report += f"  ⚠️ {anomaly}\n"
        
        report += f"{'='*50}"
        return report

    @staticmethod
    def validate_certificate_number(cert_number: str) -> Dict:
        """Validate certificate number format"""
        
        import re
        
        # Standard format: XX-YYMMDD-XXXXXX
        pattern = r'^[A-Z]{2,3}-\d{6}-\d{6}$'
        
        is_valid = bool(re.match(pattern, cert_number)) if cert_number else False
        
        if is_valid:
            parts = cert_number.split('-')
            state_code = parts[0]
            date_str = parts[1]
            
            return {
                "valid": True,
                "state_code": state_code,
                "date": f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}",
                "serial": parts[2]
            }
        else:
            return {
                "valid": False,
                "message": f"Invalid format: {cert_number}"
            }

    @staticmethod
    def compare_detections(old_detection: Dict, new_detection: Dict) -> Dict:
        """Compare two detection results (useful for re-verification)"""
        
        return {
            "same_position": old_detection.get('bbox') == new_detection.get('bbox'),
            "same_type": old_detection.get('type') == new_detection.get('type'),
            "confidence_change": new_detection.get('confidence', 0) - old_detection.get('confidence', 0),
            "new_anomalies": set(new_detection.get('anomalies', [])) - set(old_detection.get('anomalies', []))
        }