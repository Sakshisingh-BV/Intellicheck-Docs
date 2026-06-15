import os

from app.document_parsing.pdf_parser import PDFPageImage
from app.services.document_processor import DocumentProcessor


class FakePDFParser:
    def __init__(self, page_paths):
        self.page_paths = page_paths
        self.received_path = None

    def parse(self, pdf_path):
        self.received_path = pdf_path
        return [
            PDFPageImage(page_number=index + 1, image_path=path)
            for index, path in enumerate(self.page_paths)
        ]


class FakeDocumentProcessor(DocumentProcessor):
    def __init__(self, page_paths):
        self.pdf_parser = FakePDFParser(page_paths)
        self.use_minio = False
        self.minio_client = None
        self.bucket_name = None

    def _process_image_document(self, image_path, doc_id, **kwargs):
        page_number = kwargs["page_number"]
        return {
            "doc_id": doc_id,
            "filename": kwargs["filename"],
            "file_type": "image",
            "page_number": page_number,
            "source_file": kwargs["source_file"],
            "status": "completed",
            "ocr_result": {
                "document_name": kwargs["filename"],
                "text": f"page {page_number} text",
                "total_blocks": 1,
                "results": [
                    {
                        "text": f"page {page_number} text",
                        "confidence": 0.9,
                        "bbox": {},
                    }
                ],
            },
            "classification": {
                "document_type": "aadhaar_card" if page_number == 2 else "unknown",
                "display_name": "Aadhaar Card" if page_number == 2 else "Unknown Document",
                "confidence": 0.8 if page_number == 2 else 0.0,
                "matched_keywords": [],
                "extracted_fields": {},
                "all_scores": {},
            },
        }


def test_pdf_document_is_processed_page_by_page_and_aggregated(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF test")

    page_paths = []
    for page_number in (1, 2):
        page_path = tmp_path / f"page-{page_number}.png"
        page_path.write_bytes(b"image")
        page_paths.append(str(page_path))

    processor = FakeDocumentProcessor(page_paths)

    result = processor.process_document(str(pdf_path))

    assert processor.pdf_parser.received_path == str(pdf_path)
    assert result["status"] == "completed"
    assert result["file_type"] == "pdf"
    assert result["page_count"] == 2
    assert result["ocr_result"]["text"] == "page 1 text\n\npage 2 text"
    assert result["ocr_result"]["total_blocks"] == 2
    assert result["ocr_result"]["results"][0]["page_number"] == 1
    assert result["ocr_result"]["results"][1]["page_number"] == 2
    assert result["classification"]["document_type"] == "aadhaar_card"
    assert all(not os.path.exists(path) for path in page_paths)


def test_unsupported_file_type_returns_structured_error(tmp_path):
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not a document")

    processor = FakeDocumentProcessor([])

    result = processor.process_document(str(text_path))

    assert result["status"] == "unsupported_file_type"
    assert result["classification"]["document_type"] == "unknown"
