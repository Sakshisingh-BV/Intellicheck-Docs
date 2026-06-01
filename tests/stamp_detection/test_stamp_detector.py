# tests/stamp_detection/test_stamp_detector.py

import os
import sys
import cv2
import numpy as np
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.stamp_detection import StampDetector
from app.pipelines.stamp_detection_pipeline import StampDetectionPipeline

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestStampDetector:
    """Test suite for stamp detector"""
    
    @staticmethod
    def test_model_loading():
        """Test 1: Can we load the model?"""
        print("\n" + "="*60)
        print("TEST 1: Model Loading")
        print("="*60)
        
        try:
            detector = StampDetector("app/models/best.pt")
            print("✅ Model loaded successfully!")
            print(f"   Model type: {type(detector.model)}")
            print(f"   Confidence threshold: {detector.confidence_threshold}")
            return True
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False

    @staticmethod
    def test_detection_on_image(image_path: str):
        """Test 2: Run detection on a sample image"""
        print("\n" + "="*60)
        print("TEST 2: Detection on Image")
        print("="*60)
        
        if not os.path.exists(image_path):
            print(f"❌ Test image not found: {image_path}")
            return False
        
        try:
            detector = StampDetector("app/models/best.pt")
            
            # Load and show image info
            image = cv2.imread(image_path)
            print(f"📷 Image loaded: {image_path}")
            print(f"   Shape: {image.shape}")
            
            # Run detection
            print("🔍 Running detection...")
            result = detector.detect(image_path)
            
            # Print results
            print(f"\n✅ Detection completed!")
            print(f"   Document Type: {result['document_type']}")
            print(f"   Total detections: {result['summary']['total_detections']}")
            print(f"   Physical stamps: {result['summary']['physical_stamps']}")
            print(f"   Signatures: {result['summary']['signatures']}")
            
            # Print document fields (always present for debugging)
            print(f"\n📝 Document Fields:")
            for key, value in result['document_fields'].items():
                if key != 'scoring_breakdown':
                    print(f"   {key}: {value}")
            
            # Print individual detections
            print("\n📋 Individual Detections:")
            for i, det in enumerate(result['detections']):
                print(f"   [{i}] {det['label']}")
                print(f"       Confidence: {det['confidence']}")
                print(f"       BBox: {det['bbox']}")
                print(f"       Ink Confirmed: {det['ink_confirmed']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Detection failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def test_visualization(image_path: str, output_path: str):
        """Test 3: Create visualization"""
        print("\n" + "="*60)
        print("TEST 3: Visualization")
        print("="*60)
        
        try:
            detector = StampDetector("app/models/best.pt")
            
            print(f"📷 Creating visualization...")
            annotated = detector.visualize_detections(image_path, output_path)
            
            print(f"✅ Visualization saved!")
            print(f"   Output: {output_path}")
            print(f"   Shape: {annotated.shape}")
            
            return True
            
        except Exception as e:
            print(f"❌ Visualization failed: {e}")
            return False

    @staticmethod
    def test_pipeline(image_path: str):
        """Test 4: Full pipeline"""
        print("\n" + "="*60)
        print("TEST 4: Full Pipeline Integration")
        print("="*60)
        
        try:
            pipeline = StampDetectionPipeline("app/models/best.pt")
            
            # Load image
            image = cv2.imread(image_path)
            print(f"📷 Processing image: {image_path}")
            
            # Run pipeline
            print("⚙️  Running pipeline...")
            result = pipeline.process(image)
            
            if result['success']:
                print(f"\n✅ Pipeline completed!")
                print(f"   Document Type: {result['document_type']}")
                print(f"   Physical Stamps found: {result['physical_stamps_found']}")
                print(f"   Signatures found: {result['signatures_found']}")
                
                # Show document fields
                print(f"\n📝 Document Fields:")
                for key, value in result.get('document_fields', {}).items():
                    if key != 'scoring_breakdown':
                        print(f"   {key}: {value}")
                return True
            else:
                print(f"❌ Pipeline error: {result['error']}")
                return False
                
        except Exception as e:
            print(f"❌ Pipeline test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("STAMP DETECTION TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Model loading
    results['Model Loading'] = TestStampDetector.test_model_loading()
    
    # Test 2-4: Detection tests (use a sample image if available)
    test_image = "data/rubberstamp.png"
    if os.path.exists(test_image):
        results['Detection'] = TestStampDetector.test_detection_on_image(test_image)
        results['Visualization'] = TestStampDetector.test_visualization(
            test_image,
            "data/test_outputs/stamp_visualization.jpg"
        )
        results['Pipeline'] = TestStampDetector.test_pipeline(test_image)
    else:
        print(f"\n⚠️  Skipping image tests (no sample at {test_image})")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    run_all_tests()