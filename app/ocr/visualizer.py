import cv2
import numpy as np


class OCRVisualizer:

    @staticmethod
    def draw_boxes(image_path, parsed_results, output_path):
        """
        Draw OCR bounding boxes and text labels on an image.

        Args:
            image_path: Path to the original image.
            parsed_results: List of parsed OCR results with bbox dicts.
            output_path: Path to save the annotated image.
        """

        image = cv2.imread(image_path)

        for item in parsed_results:

            points = item["bbox"]

            # Draw the full quadrilateral polygon
            poly = np.array([
                points["top_left"],
                points["top_right"],
                points["bottom_right"],
                points["bottom_left"]
            ], dtype=np.int32)

            cv2.polylines(
                image,
                [poly],
                isClosed=True,
                color=(0, 255, 0),
                thickness=2
            )

            # Draw text label above the top-left corner
            top_left = tuple(map(int, points["top_left"]))
            label_pos = (top_left[0], max(top_left[1] - 5, 10))

            cv2.putText(
                image,
                item["text"],
                label_pos,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA
            )

        cv2.imwrite(output_path, image)