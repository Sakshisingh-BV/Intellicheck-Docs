import cv2
from app.preprocessing.blur import detect_blur
from app.preprocessing.utils import load_image
from app.ocr.engine import OCREngine
from app.ocr.parser import OCRParser
from app.ocr.formatter import OCRFormatter


class OCRPipeline:

    def __init__(self):
        self.engine = OCREngine()

    def run(self, image_input, check_quality=True, image_name=None):
        """
        OCR pipeline: optional quality check → PaddleOCR → parse → format.

        PaddleOCR 3.5 handles orientation correction, unwarping, and
        image enhancement internally. No custom preprocessing needed.

        Args:
            image_input: Path to an image file (str) or a numpy array
                         (BGR/grayscale).
            check_quality: If True, run blur detection as a quality
                           gate (without modifying the image).
                           Defaults to True.
            image_name: Display name for the document in formatted output.
                        Defaults to the file path when a path is given,
                        or "image" when a numpy array is given.

        Returns:
            Tuple of (parsed_result, formatted_result, quality_info).
            quality_info contains blur_score and is_blurry when
            check_quality is True, otherwise None.
        """

        quality_info = None

        if check_quality:
            if isinstance(image_input, str):
                image = load_image(image_input)
            else:
                image = image_input
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            blur_result = detect_blur(gray)
            quality_info = {
                "blur_score": blur_result["blur_score"],
                "is_blurry": blur_result["is_blurry"],
                "blur_level": blur_result["blur_level"],
            }

        # Feed image directly to PaddleOCR 3.5
        raw_result = self.engine.extract(image_input)

        parsed_result = OCRParser.parse(raw_result)

        display_name = image_name or (image_input if isinstance(image_input, str) else "image")
        formatted_result = OCRFormatter.format(
            parsed_result,
            display_name
        )

        return parsed_result, formatted_result, quality_info