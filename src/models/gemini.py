"""Gemini 2.5 Flash implementation for image generation"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from PIL import Image
from .base import BaseImageModel


class GeminiImageModel(BaseImageModel):
    """
    Gemini image generation model (supports both Flash and Pro models)

    Models:
    - gemini-3.1-flash-image-preview (default, faster generation)
    - gemini-3-pro-image-preview (higher quality, use_pro_model=True)

    Model names can be configured via environment variables:
    - GEMINI_FLASH_MODEL: Flash model name (default: gemini-3.1-flash-image-preview)
    - GEMINI_PRO_MODEL: Pro model name (default: gemini-3-pro-image-preview)

    API Docs: https://ai.google.dev/gemini-api/docs/image-generation
    """

    def __init__(self, api_key: str, use_pro_model: bool = False):
        super().__init__(api_key)

        # Load model names from environment variables with defaults
        flash_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.1-flash-image-preview")
        pro_model = os.getenv("GEMINI_PRO_MODEL", "gemini-3-pro-image-preview")

        # Select model based on parameter
        self.model_name = pro_model if use_pro_model else flash_model
        self.use_pro_model = use_pro_model

        # Import google.genai lazily to allow optional dependency
        try:
            from google import genai
            self.genai = genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise ImportError(
                "google-genai package is required for Gemini model. "
                "Install it with: pip install google-genai"
            )

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 1000,
        reference_images: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze image with Gemini

        Note: Gemini 2.5 Flash Image is primarily for image generation.
        For image understanding, consider using Qwen VL instead.

        Args:
            image_path: Local path or URL
            prompt: Question or instruction
            max_tokens: Max response tokens
            reference_images: Optional list of reference image paths or URLs
        """
        try:
            # Build contents list
            contents = []

            # Add reference images if provided
            if reference_images:
                contents.append("参考图片：")
                for ref_img_path in reference_images:
                    if ref_img_path.startswith("http"):
                        return {
                            "success": False,
                            "error": "URL reference images not yet supported for Gemini analysis. Use local file path."
                        }
                    ref_image = Image.open(ref_img_path)
                    contents.append(ref_image)

            # Load main image
            if image_path.startswith("http"):
                return {
                    "success": False,
                    "error": "URL images not yet supported for Gemini analysis. Use local file path."
                }

            image = Image.open(image_path)
            contents.append(image)
            contents.append(prompt)

            # Generate content
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            # Extract text response
            content = ""
            for part in response.parts:
                if part.text is not None:
                    content += part.text

            return {
                "success": True,
                "content": content,
                "model": self.model_name
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def ocr(
        self,
        image_path: str,
        language: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        OCR with Gemini

        Args:
            image_path: Path to image
            language: Language hint (auto, zh, en)
        """
        # OCR prompt based on language
        if language == "zh":
            prompt = "请识别这张图片中的所有中文文字，按原文输出。"
        elif language == "en":
            prompt = "Please extract all English text from this image and output it as is."
        else:  # auto
            prompt = "请识别这张图片中的所有文字（包括中文和英文），按原文输出。保持原有格式。"

        return await self.analyze_image(image_path, prompt, max_tokens=2000)

    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        reference_images: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image using Gemini model (Flash or Pro)

        Args:
            prompt: Text description of the image to generate
            output_path: Optional path to save the generated image
            reference_images: Optional list of paths to reference images for img2img (up to 14 images)
            **kwargs: Additional parameters
                - aspect_ratio: Image aspect ratio ("1:1", "16:9", etc.)
                - resolution: Image resolution ("1K", "2K", "4K")
                - thinking_level: Thinking level ("HIGH", "MINIMAL") - default: "MINIMAL"
                - temperature: Creativity level (default: 1.0)
        """
        try:
            from google.genai import types

            # Build contents list
            contents = [prompt]

            # Add all reference images if provided (img2img mode)
            if reference_images:
                for ref_path in reference_images:
                    if ref_path.startswith("http"):
                        return {
                            "success": False,
                            "error": "URL reference images not yet supported. Use local file path."
                        }

                    # Load and add PIL Image directly
                    ref_image = Image.open(ref_path)
                    contents.append(ref_image)

            # Optional configuration
            config_kwargs = {}
            aspect_ratio = kwargs.get("aspect_ratio")
            resolution = kwargs.get("resolution")
            thinking_level = kwargs.get("thinking_level", "MINIMAL")  # Default to MINIMAL

            # Build config if any optional parameters are provided
            if aspect_ratio or resolution or thinking_level:
                config_parts = {}

                # Image configuration
                if aspect_ratio or resolution:
                    config_parts["image_config"] = types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution
                    )

                # Thinking configuration
                if thinking_level:
                    config_parts["thinking_config"] = types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel[thinking_level]
                    )

                config_kwargs["config"] = types.GenerateContentConfig(
                    **config_parts
                )

            # Generate image
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                **config_kwargs
            )

            # Extract and save image
            for part in response.parts:
                if part.inline_data is not None:
                    # Get PIL Image
                    image = part.as_image()

                    # Save to file if output_path provided
                    if output_path:
                        # Ensure directory exists
                        output_file = Path(output_path)
                        output_file.parent.mkdir(parents=True, exist_ok=True)

                        # Ensure file has extension
                        if not output_file.suffix:
                            output_file = output_file.with_suffix('.png')

                        # Save image (Google Image.save() determines format from extension)
                        image.save(str(output_file))

                        return {
                            "success": True,
                            "image_path": str(output_path),
                            "image_data": None,
                            "model": self.model_name,
                            "prompt_used": prompt,
                            "reference_images": reference_images if reference_images else [],
                            "mode": "img2img" if reference_images else "text2img",
                            "aspect_ratio": aspect_ratio,
                            "resolution": resolution
                        }
                    else:
                        # Return raw image data
                        from io import BytesIO
                        buffer = BytesIO()
                        image.save(buffer, format='PNG')
                        image_data = buffer.getvalue()

                        return {
                            "success": True,
                            "image_path": None,
                            "image_data": image_data,
                            "model": self.model_name,
                            "prompt_used": prompt,
                            "reference_images": reference_images if reference_images else [],
                            "mode": "img2img" if reference_images else "text2img",
                            "aspect_ratio": aspect_ratio,
                            "resolution": resolution
                        }

            # If we get here, no image was generated
            return {
                "success": False,
                "error": "No image data in response. The model may have generated text instead."
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Image generation failed: {str(e)}"
            }

    def _enhance_prompt(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """
        Enhance prompt for better image generation results

        Args:
            prompt: Original user prompt
            kwargs: Additional parameters (style, quality, etc.)
        """
        # This method is kept for compatibility but we now use the original prompt
        # as Gemini 2.5 Flash handles prompt enhancement internally
        return prompt
