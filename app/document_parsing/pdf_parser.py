import os
import tempfile
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PDFPageImage:
    page_number: int
    image_path: str


class PDFParser:
    """
    Converts PDF pages into temporary images suitable for OCR.

    The caller owns cleanup of the generated image paths. This keeps the parser
    reusable for API routes, scripts, tests, and future pipelines.
    """

    def __init__(self, dpi: int = 75):
        self.dpi = dpi

    def parse(self, pdf_path: str) -> List[PDFPageImage]:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "PDF parsing requires pypdfium2. Install project dependencies "
                "or run: pip install pypdfium2"
            ) from exc

        document = pdfium.PdfDocument(pdf_path)
        page_images = []

        try:
            for page_index in range(len(document)):
                page = document[page_index]
                bitmap = page.render(scale=self.dpi / 72)
                pil_image = bitmap.to_pil()

                tmp = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f"_page{page_index + 1}.png",
                )
                tmp.close()
                pil_image.save(tmp.name)

                page_images.append(
                    PDFPageImage(
                        page_number=page_index + 1,
                        image_path=tmp.name,
                    )
                )
        finally:
            document.close()

        return page_images
