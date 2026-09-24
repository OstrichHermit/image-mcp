"""Base interface for image models"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path


class BaseImageModel(ABC):
    """Base class for all image models"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 1000,
        reference_images: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze an image and return the result

        Args:
            image_path: Path to the image file or URL
            prompt: Question or instruction for the image
            max_tokens: Maximum tokens in response
            reference_images: Optional list of reference image paths or URLs
            **kwargs: Additional model-specific parameters

        Returns:
            Dict with keys:
                - success: bool
                - content: str (model response)
                - error: str (if failed)
        """
        pass

    @abstractmethod
    async def ocr(
        self,
        image_path: str,
        language: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from an image

        Args:
            image_path: Path to the image file
            language: Language code (auto, zh, en, etc.)
            **kwargs: Additional parameters

        Returns:
            Dict with keys:
                - success: bool
                - text: str (extracted text)
                - error: str (if failed)
        """
        pass

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        reference_image: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an image from text prompt

        Args:
            prompt: Text description of the image to generate
            output_path: Optional path to save the generated image
            reference_image: Optional path to reference image for img2img
            **kwargs: Additional model-specific parameters

        Returns:
            Dict with keys:
                - success: bool
                - image_path: str (path to saved image)
                - image_data: bytes (raw image data if output_path is None)
                - error: str (if failed)
        """
        pass

    def _validate_image_path(self, image_path: str) -> bool:
        """Validate that image path exists"""
        if image_path.startswith("http"):
            return True  # URL
        return Path(image_path).exists()

    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        import base64
        from pathlib import Path

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
