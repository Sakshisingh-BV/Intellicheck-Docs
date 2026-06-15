from paddleocr import PaddleOCR


class OCREngine:

    def __init__(self):

        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=640,
            text_det_limit_type="max",
            lang='en',
            device='cpu',
            enable_mkldnn=False
        )

    def extract(self, image_input):
        """
        Run OCR on an image.

        Args:
            image_input: file path (str) or numpy array (BGR/grayscale)

        Returns:
            List of OCRResult objects from PaddleOCR 3.5.
        """

        result = self.ocr.predict(image_input)

        return result
