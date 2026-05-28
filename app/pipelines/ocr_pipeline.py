import cv2
from app.preprocessing.blur import detect_blur
from app.preprocessing.utils import load_image
from app.ocr.engine import OCREngine
from app.ocr.parser import OCRParser
from app.ocr.formatter import OCRFormatter


class OCRPipeline:

    def __init__(self):
        self.engine = OCREngine()

    def run(self, image_path, check_quality=True):
        """
        OCR pipeline: optional quality check → PaddleOCR → parse → format.

        PaddleOCR 3.5 handles orientation correction, unwarping, and
        image enhancement internally. No custom preprocessing needed.

        Args:
            image_path: Path to the input image file.
            check_quality: If True, run blur detection as a quality
                           gate (without modifying the image).
                           Defaults to True.

        Returns:
            Tuple of (parsed_result, formatted_result, quality_info).
            quality_info contains blur_score and is_blurry when
            check_quality is True, otherwise None.
        """

        quality_info = None

        if check_quality:
            image = load_image(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_result = detect_blur(gray)
            quality_info = {
                "blur_score": blur_result["blur_score"],
                "is_blurry": blur_result["is_blurry"],
                "blur_level": blur_result["blur_level"],
            }

        # Feed raw image directly to PaddleOCR 3.5
        raw_result = self.engine.extract(image_path)

        parsed_result = OCRParser.parse(raw_result)

        formatted_result = OCRFormatter.format(
            parsed_result,
            image_path
        )

        return parsed_result, formatted_result, quality_info