class OCRParser:

    @staticmethod
    def parse(raw_result):
        """
        Parse raw PaddleOCR 3.5.0 result into a structured list.

        PaddleOCR 3.5 returns a list of OCRResult objects.
        Each OCRResult has parallel lists:
            - rec_texts:  list of recognized text strings
            - rec_scores: list of confidence floats
            - dt_polys:   list of bounding polygons (numpy arrays, shape (4,2))

        Returns:
            List of dicts with keys: text, confidence, bbox.
        """

        parsed_results = []

        if not raw_result:
            return parsed_results

        ocr_result = raw_result[0]

        texts = ocr_result.get("rec_texts", [])
        scores = ocr_result.get("rec_scores", [])
        polys = ocr_result.get("dt_polys", [])

        if not texts:
            return parsed_results

        for text, score, poly in zip(texts, scores, polys):

            # poly is a numpy array of shape (4, 2): [[x,y], ...]
            # Order: top_left, top_right, bottom_right, bottom_left
            bbox_points = poly.tolist()

            parsed_results.append({
                "text": text,
                "confidence": float(score),
                "bbox": {
                    "top_left": bbox_points[0],
                    "top_right": bbox_points[1],
                    "bottom_right": bbox_points[2],
                    "bottom_left": bbox_points[3]
                }
            })

        return parsed_results