from app.preprocessing.pipeline import process_image
from app.preprocessing.blur import detect_blur
from app.preprocessing.utils import load_image
from app.ocr.engine import OCREngine
from app.ocr.parser import OCRParser
from app.ocr.formatter import OCRFormatter


class OCRPipeline:

    def __init__(self):
        self.engine = OCREngine()

    def run(self, image_path, preprocess=False, check_quality=True):
        """
        Full OCR pipeline: optional quality check → OCR → parse → format.

        PaddleOCR 3.5 includes its own ML-based document preprocessor
        (orientation correction, unwarping). Our preprocessing pipeline
        (crop, CLAHE, denoise, binarize) is designed for traditional OCR
        and can degrade neural OCR accuracy. Therefore, preprocessing is
        disabled by default.

        Args:
            image_path: Path to the input image file.
            preprocess: If True, run the full preprocessing pipeline
                        and feed the processed image to OCR. Use this
                        only for traditional OCR engines. Defaults to False.
            check_quality: If True, run blur detection as a quality
                           gate (without modifying the image).
                           Defaults to True.

        Returns:
            Tuple of (parsed_result, formatted_result, quality_info).
            quality_info contains blur_score and is_blurry when
            check_quality is True, otherwise None.
        """

        quality_info = None

        if preprocess:
            # Full preprocessing: crop → rotate → CLAHE → denoise → binarize
            # Then feed the preprocessed image to OCR
            preprocess_result = process_image(image_path)

            ocr_ready_image = preprocess_result["ocr_ready_image"]

            quality_info = {
                "blur_score": preprocess_result["blur_score"],
                "is_blurry": preprocess_result["is_blurry"],
                "preprocessing_applied": True
            }

            raw_result = self.engine.extract(ocr_ready_image)

        else:
            # Feed the raw image directly to PaddleOCR
            # PaddleOCR 3.5 handles orientation, unwarping internally

            if check_quality:
                # Run blur detection without modifying the image
                image = load_image(image_path)
                import cv2
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blur_result = detect_blur(gray)
                quality_info = {
                    "blur_score": blur_result["blur_score"],
                    "is_blurry": blur_result["is_blurry"],
                    "preprocessing_applied": False
                }

            raw_result = self.engine.extract(image_path)

        parsed_result = OCRParser.parse(raw_result)

        formatted_result = OCRFormatter.format(
            parsed_result,
            image_path
        )

        return parsed_result, formatted_result, quality_info