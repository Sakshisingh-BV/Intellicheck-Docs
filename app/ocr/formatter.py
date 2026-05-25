class OCRFormatter:

    @staticmethod
    def format(parsed_results, image_name):

        return {
            "document_name": image_name,
            "total_blocks": len(parsed_results),
            "results": parsed_results
        }