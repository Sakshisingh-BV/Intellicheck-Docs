#!/usr/bin/env python3
"""
Stamp Detector Test Suite — single image or batch mode.

Usage:
    python tests/stamp_detection/test_stamp_detector_simple.py
        → runs against data/estamps.png (default)

    python tests/stamp_detection/test_stamp_detector_simple.py data/stamp1.png
        → runs against a specific image

    python tests/stamp_detection/test_stamp_detector_simple.py --all
        → runs against every image in data/

    python tests/stamp_detection/test_stamp_detector_simple.py --dir data
        → runs against every image in the given directory
"""

import os
import sys
import glob
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.stamp_detection import StampDetector

SUPPORTED_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')


def format_bbox(bbox):
    """Format bounding box nicely"""
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    return f"[{x1}, {y1}, {x2}, {y2}] (w:{w}, h:{h})"


def test_detection_on_image(image_path: str):
    """Run detection and display results in clean format"""
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return False
    
    print("\n" + "="*70)
    print("STAMP DETECTION TEST")
    print("="*70)
    
    try:
        # ========== MODEL LOADING ==========
        print("\n⚙️  MODEL LOADING")
        try:
            detector = StampDetector("app/models/best.pt")
            print("   ✅ Model loaded successfully")
            print(f"   Model: {type(detector.model).__name__}")
            print(f"   Stamp Confidence Threshold: {detector.confidence_threshold}")
            print(f"   Signature Confidence Threshold: {detector.signature_confidence_threshold}")
        except Exception as e:
            print(f"   ❌ Model loading failed: {e}")
            return False
        
        result = detector.detect(image_path)
        
        # ========== DOCUMENT CLASSIFICATION ==========
        doc_type = result['document_type']
        # Convert non_e_stamp to physical_stamp for display
        display_type = "PHYSICAL_STAMP" if doc_type == "non_e_stamp" else doc_type.upper()
        
        print("\n📄 DOCUMENT CLASSIFICATION")
        print(f"   Document Type: {display_type}")
        
        # ========== E-STAMP DATA EXTRACTION ==========
        fields = result['document_fields']
        print("\n📋 EXTRACTION RESULTS")
        print(f"   Certificate Number: {fields.get('certificate_number') or 'N/A'}")
        print(f"   Stamp Duty: {fields.get('stamp_duty') or 'N/A'}")
        print(f"   State: {fields.get('state') or 'N/A'}")
        print(f"   Date: {fields.get('date') or 'N/A'}")
        
        # ========== QR CODE ==========
        print("\n🔐 QR CODE")
        print(f"   QR Present: {fields.get('qr_present')}")
        print(f"   QR Decoded: {fields.get('qr_decoded')}")
        if fields.get('qr_data'):
            print(f"   QR Data: {fields['qr_data'][:50]}...")
        print(f"   Cert Match: {fields.get('qr_certificate_match')}")
        
        # ========== E-STAMP SCORE ==========
        print("\n⭐ E-STAMP SCORING")
        print(f"   Score: {fields.get('estamp_score')}/{fields.get('estamp_threshold')}")
        
        # ========== DETECTION SUMMARY ==========
        summary = result['summary']
        print("\n📊 DETECTION SUMMARY")
        print(f"   Total Detections: {summary['total_detections']}")
        print(f"   Physical Stamps: {summary['physical_stamps']}")
        print(f"   Signatures: {summary['signatures']}")
        print(f"   With Anomalies: {summary['detections_with_anomalies']}")
        print(f"   Overall Confidence: {summary['overall_confidence']:.2f}")
        
        # ========== INDIVIDUAL DETECTIONS ==========
        if result['detections']:
            print("\n📍 DETECTION DETAILS")
            for i, det in enumerate(result['detections'], 1):
                label = det['label'].upper()
                conf = det['confidence']
                bbox = det['bbox']
                anomalies = det.get('anomalies', [])
                
                print(f"\n   [{i}] {label}")
                print(f"       Confidence: {conf:.2f}")
                print(f"       BBox: {format_bbox(bbox)}")
                print(f"       Ink Confirmed: {det['ink_confirmed']}")
                if anomalies:
                    print(f"       ⚠️  Anomalies: {', '.join(anomalies)}")
                else:
                    print(f"       ✓ No anomalies")
        else:
            print("\n📍 DETECTION DETAILS")
            print("   No detections found")
        
        # ========== ANOMALY SUMMARY ==========
        print("\n🔍 ANOMALY DETECTION")
        anomaly_types = set()
        for det in result['detections']:
            for anom in det.get('anomalies', []):
                anomaly_types.add(anom)
        
        if anomaly_types:
            for anom_type in anomaly_types:
                count = sum(1 for det in result['detections'] if anom_type in det.get('anomalies', []))
                print(f"   ✓ {anom_type.replace('_', ' ').title()}: {count}")
        else:
            print("   ✓ No anomalies detected")
        
        print("\n" + "="*70)
        print("✅ DETECTION COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def collect_images(args):
    """Return list of image paths to test based on CLI args."""
    # Explicit single image
    if len(args) >= 1 and args[0] not in ('--all', '--dir'):
        return [args[0]]

    # --dir <path>
    if '--dir' in args:
        idx = args.index('--dir')
        base_dir = args[idx + 1] if idx + 1 < len(args) else 'data'
    elif '--all' in args:
        base_dir = 'data'
    else:
        # Default: single canonical e-stamp sample
        return ['data/Stamp5.png']

    images = []
    for ext in SUPPORTED_EXTS:
        images.extend(glob.glob(os.path.join(base_dir, f'*{ext}')))
        images.extend(glob.glob(os.path.join(base_dir, f'*{ext.upper()}')))
    return sorted(set(images))


def main():
    """Run single-image or batch tests."""
    args = sys.argv[1:]
    images = collect_images(args)

    if not images:
        print("\n⚠️  No images found. Check path or use --all / --dir <path>")
        return

    is_batch = len(images) > 1

    if is_batch:
        print("\n" + "="*70)
        print(f"STAMP DETECTOR - BATCH TEST ({len(images)} images)")
        print("="*70)

    passed = 0
    for img_path in images:
        ok = test_detection_on_image(img_path)
        if ok:
            passed += 1

    if is_batch:
        print(f"\n{'='*70}")
        print(f"BATCH COMPLETE: {passed}/{len(images)} passed")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
