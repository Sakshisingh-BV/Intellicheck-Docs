import logging
from typing import Dict, Optional
import cv2
import numpy as np

from app.stamp_detection import StampDetector
from app.stamp_detection.utils import StampDetectionUtils

logger = logging.getLogger(__name__)


class StampDetectionPipeline:
    """
    Stamp Detection Pipeline
    
    Document classification (e-stamp) and object detection (physical stamps,
    signatures) are fully independent. A document can simultaneously be an
    e-stamp AND contain physical rubber stamps and signatures.
    """

    def __init__(self, model_path: str = "app/models/best.pt"):
        """Initialize the stamp detection pipeline"""
        self.detector = StampDetector(model_path=model_path)
        logger.info("✅ Stamp Detection Pipeline initialized")

    def process(self, preprocessed_image: np.ndarray, 
                image_path: Optional[str] = None) -> Dict:
        """
        Process image through stamp detection pipeline
        
        Args:
            preprocessed_image: Image from preprocessing pipeline
            image_path: Original image path (for logging)
        
        Returns:
            Dict with detection results
        """
        
        try:
            logger.info(f"Starting stamp detection...")
            
            # Run detection
            detection_result = self.detector.detect(
                preprocessed_image,
                return_crops=True
            )
            
            # Analyze results
            analysis = self._analyze_detections(detection_result)
            
            # Create output
            output = {
                "success": True,
                "document_type": detection_result.get("document_type", "non_e_stamp"),
                "is_estamp_document": detection_result.get("is_estamp_document", False),
                "document_fields": detection_result.get("document_fields", {}),
                "physical_stamps_found": analysis["stamp_count"],
                "signatures_found": analysis["signature_count"],
                "raw_detections": detection_result["detections"],
                "summary": detection_result["summary"],
                "analysis": analysis,
                "image_path": image_path
            }
            
            logger.info(
                f"Detection complete: document_type={output['document_type']}, "
                f"physical_stamps={output['physical_stamps_found']}, "
                f"signatures={output['signatures_found']}"
            )
            return output
            
        except Exception as e:
            logger.error(f"Error in stamp detection pipeline: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _analyze_detections(self, detection_result: Dict) -> Dict:
        """Analyze detections — stamps are always physical objects."""
        
        detections = detection_result["detections"]
        
        analysis = {
            "valid_stamps": [],
            "invalid_stamps": [],
            "signatures": [],
            "stamp_count": 0,
            "signature_count": 0
        }
        
        for detection in detections:
            if detection["label"] == "stamp":
                if detection["ink_confirmed"]:
                    analysis["valid_stamps"].append(detection)
                    analysis["stamp_count"] += 1
                else:
                    analysis["invalid_stamps"].append(detection)
            
            elif detection["label"] == "signature":
                analysis["signatures"].append(detection)
                analysis["signature_count"] += 1

        # Overlapping stamp detection (reuses existing utility)
        image_shape = detection_result.get("image_shape")
        overlap_result = StampDetectionUtils.check_overlapping_stamps(
            detections, image_shape
        )
        analysis["overlap_analysis"] = overlap_result

        return analysis

    def process_with_visualization(self, preprocessed_image: np.ndarray,
                                  output_path: str) -> Dict:
        """Process image AND save visualization"""
        
        result = self.process(preprocessed_image)
        
        if result['success']:
            annotated = self.detector.visualize_detections(
                preprocessed_image,
                save_path=output_path
            )
            logger.info(f"Visualization saved to {output_path}")
        
        return result