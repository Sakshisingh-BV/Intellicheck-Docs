class OCRFormatter:

    @staticmethod
    def format(parsed_results, image_name):
        # Extract all text in order
        full_text = " ".join(
            block.get("text", "") for block in parsed_results
        ).strip()

        return {
            "document_name": image_name,
            "text": full_text,
            "total_blocks": len(parsed_results),
            "results": parsed_results
        }