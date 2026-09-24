"""GLM-OCR layout parsing model using Zhipu AI"""

import asyncio
import base64
from pathlib import Path
from typing import Dict, Any


class GlmOcrModel:
    """
    Zhipu GLM-OCR layout parsing model

    Uses zai-sdk for document layout parsing and OCR.
    API Docs: https://open.bigmodel.cn/dev/api/ocr/layout
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-init client to avoid import-time side effects"""
        if self._client is None:
            from zai import ZhipuAiClient
            self._client = ZhipuAiClient(api_key=self.api_key)
        return self._client

    @staticmethod
    def _encode_file_base64(file_path: str) -> str:
        """Encode a local file to base64 string"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _mime_type_for(file_path: str) -> str:
        """Guess MIME type from file extension"""
        ext = Path(file_path).suffix.lower()
        return {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "image/png")

    def _prepare_file_arg(self, image_source: str) -> str:
        """
        Prepare the file argument for the API.

        - If it's a URL, pass through directly.
        - If it's a local file, encode to base64 data URI.
        """
        if image_source.startswith(("http://", "https://")):
            return image_source

        path = Path(image_source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {image_source}")

        b64 = self._encode_file_base64(image_source)
        mime = self._mime_type_for(image_source)
        return f"data:{mime};base64,{b64}"

    async def layout_parsing(self, image_source: str) -> Dict[str, Any]:
        """
        Call GLM-OCR for document layout parsing.

        Args:
            image_source: Local file path or URL.

        Returns:
            dict with keys: success, content, error, model
        """
        try:
            file_arg = self._prepare_file_arg(image_source)

            client = self._get_client()

            # zai-sdk is synchronous -- wrap with asyncio.to_thread
            response = await asyncio.to_thread(
                client.layout_parsing.create,
                model="glm-ocr",
                file=file_arg,
            )

            # response is a LayoutParsingResp pydantic model
            # Key field: md_results  (Markdown formatted recognition result)
            if response.md_results:
                return {
                    "success": True,
                    "content": response.md_results,
                    "model": response.model,
                }
            elif response.layout_details:
                # Fallback: reconstruct text from layout_details
                pages_text = []
                for page in response.layout_details:
                    for detail in page:
                        if detail.content:
                            pages_text.append(detail.content)
                return {
                    "success": True,
                    "content": "\n".join(pages_text) if pages_text else "No text content found in document.",
                    "model": response.model,
                }
            else:
                return {
                    "success": False,
                    "error": "No parsing results returned from API.",
                }

        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
