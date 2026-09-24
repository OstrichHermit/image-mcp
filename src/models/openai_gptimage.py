"""OpenAI GPT Image 2.5 implementation for image generation"""

import os
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import httpx

from .base import BaseImageModel


def _post_with_retry(client: httpx.Client, url: str, headers: dict,
                     max_attempts: int = 3, **kwargs):
    """POST with retry on transient network errors (home router DNS occasionally flaps)."""
    import time
    last_err = None
    for attempt in range(max_attempts):
        try:
            return client.post(url, headers=headers, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise last_err


class OpenAIGPTImageModel(BaseImageModel):
    """
    OpenAI GPT Image 2.5 model (Flare / Sunburst)

    Models:
    - gpt-image-2.5-flare (default, speed-first, ~50% lower latency than 2.0)
    - gpt-image-2.5-sunburst (editing-precision-first, slower, better multi-edit consistency)

    Released 2026-09-08. Same pricing structure as gpt-image-2 but consumes
    ~75% fewer output tokens at equal quality. Quality tiers: low/medium/high/xhigh/max.

    Model names can be configured via environment variables:
    - OPENAI_IMAGE_MODEL_FAST: default (default: gpt-image-2.5-flare)
    - OPENAI_IMAGE_MODEL_PRO: high-quality (default: gpt-image-2.5-sunburst)
    - OPENAI_BASE_URL: optional, for API relays (default: https://api.openai.com/v1)

    API docs: https://developers.openai.com/api/docs/guides/image-generation
    """

    # aspect_ratio (Gemini-style param) -> closest supported size
    ASPECT_TO_SIZE = {
        "1:1": "1024x1024",
        "2:3": "1024x1536",
        "3:4": "1024x1536",
        "4:5": "1024x1536",
        "1:4": "1024x1536",
        "1:8": "1024x1536",
        "9:16": "1024x1536",
        "3:2": "1536x1024",
        "4:3": "1536x1024",
        "5:4": "1536x1024",
        "4:1": "1536x1024",
        "8:1": "1536x1024",
        "16:9": "1536x1024",
        "21:9": "1536x1024",
    }
    RESOLUTION_TO_SIZE = {
        "512px": "1024x1024",
        "1K": "1024x1024",
        "2K": "2048x2048",
        "4K": "2048x2048",
    }

    def __init__(self, api_key: str, use_pro_model: bool = False):
        super().__init__(api_key)

        fast_model = os.getenv("OPENAI_IMAGE_MODEL_FAST", "gpt-image-2.5-flare")
        pro_model = os.getenv("OPENAI_IMAGE_MODEL_PRO", "gpt-image-2.5-sunburst")
        self.model_name = pro_model if use_pro_model else fast_model
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

        # OpenRouter uses a dedicated image endpoint (/api/v1/images) and
        # namespaced model slugs (openai/gpt-image-2.5-flare)
        self.is_openrouter = "openrouter.ai" in self.base_url
        if self.is_openrouter and "/" not in self.model_name:
            self.model_name = f"openai/{self.model_name}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def _resolve_size(self, kwargs: Dict[str, Any]) -> Optional[str]:
        """Resolve output size from size / aspect_ratio / resolution params."""
        size = kwargs.get("size")
        if size:
            return size
        aspect_ratio = kwargs.get("aspect_ratio")
        if aspect_ratio and aspect_ratio in self.ASPECT_TO_SIZE:
            return self.ASPECT_TO_SIZE[aspect_ratio]
        resolution = kwargs.get("resolution")
        if resolution and resolution in self.RESOLUTION_TO_SIZE:
            return self.RESOLUTION_TO_SIZE[resolution]
        return None

    def _save_or_return(self, image_bytes: bytes, output_path: Optional[str],
                        prompt: str, reference_images: Optional[list]) -> Dict[str, Any]:
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            if not output_file.suffix:
                output_file = output_file.with_suffix(".png")
            output_file.write_bytes(image_bytes)
            return {
                "success": True,
                "image_path": str(output_file),
                "image_data": None,
                "model": self.model_name,
                "prompt_used": prompt,
                "reference_images": reference_images if reference_images else [],
                "mode": "img2img" if reference_images else "text2img",
            }
        return {
            "success": True,
            "image_path": None,
            "image_data": image_bytes,
            "model": self.model_name,
            "prompt_used": prompt,
            "reference_images": reference_images if reference_images else [],
            "mode": "img2img" if reference_images else "text2img",
        }

    # ------------------------------------------------------------------
    # BaseImageModel interface
    # ------------------------------------------------------------------

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 1000,
        reference_images: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "GPT Image 2.5 is a generation/editing model, not a vision model. "
                     "Use analyze_image (Qwen VL) for image understanding."
        }

    async def ocr(
        self,
        image_path: str,
        language: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "GPT Image 2.5 does not support OCR. Use analyze_image (Qwen VL) "
                     "or analyze_image_ocr (GLM-OCR) instead."
        }

    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        reference_images: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an image using GPT Image 2.5 (flare or sunburst)

        Args:
            prompt: Text description of the image to generate
            output_path: Optional path to save the generated image
            reference_images: Optional list of local paths for img2img / editing
            **kwargs: Additional parameters
                - size: Image size (e.g. "1024x1024", "1536x1024", "1024x1536", "2048x2048")
                - quality: low / medium / high / xhigh / max / auto
                - aspect_ratio: Gemini-style ratio, mapped to size automatically
                - resolution: Gemini-style resolution, mapped to size automatically
        """
        try:
            quality = kwargs.get("quality")
            size = self._resolve_size(kwargs)

            def _data_url(path: str) -> str:
                suffix = Path(path).suffix.lower().lstrip(".") or "png"
                if suffix == "jpg":
                    suffix = "jpeg"
                encoded = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
                return f"data:image/{suffix};base64,{encoded}"

            if self.is_openrouter:
                # OpenRouter dedicated Image API: POST {base}/images
                payload = {"model": self.model_name, "prompt": prompt}
                if quality:
                    payload["quality"] = quality
                if size:
                    payload["size"] = size
                if reference_images:
                    refs = []
                    for ref_path in reference_images:
                        if ref_path.startswith("http"):
                            refs.append({"type": "image_url", "image_url": {"url": ref_path}})
                        else:
                            refs.append({"type": "image_url", "image_url": {"url": _data_url(ref_path)}})
                    payload["input_references"] = refs

                with httpx.Client(timeout=300.0) as client:
                    resp = _post_with_retry(
                        client,
                        f"{self.base_url}/images",
                        headers={**self._headers(), "Content-Type": "application/json"},
                        json=payload,
                    )
            elif reference_images:
                # OpenAI official: editing via multipart /images/edits
                files = []
                for ref_path in reference_images:
                    if ref_path.startswith("http"):
                        return {
                            "success": False,
                            "error": "URL reference images not yet supported. Use local file path."
                        }
                    ref_bytes = Path(ref_path).read_bytes()
                    files.append(
                        ("image[]", (Path(ref_path).name, ref_bytes, "application/octet-stream"))
                    )

                data = {"model": self.model_name, "prompt": prompt}
                if quality:
                    data["quality"] = quality
                if size:
                    data["size"] = size

                with httpx.Client(timeout=300.0) as client:
                    resp = _post_with_retry(
                        client,
                        f"{self.base_url}/images/edits",
                        headers=self._headers(),
                        data=data,
                        files=files,
                    )
            else:
                # OpenAI official: text-to-image via /images/generations
                payload = {"model": self.model_name, "prompt": prompt}
                if quality:
                    payload["quality"] = quality
                if size:
                    payload["size"] = size

                with httpx.Client(timeout=300.0) as client:
                    resp = _post_with_retry(
                        client,
                        f"{self.base_url}/images/generations",
                        headers={**self._headers(), "Content-Type": "application/json"},
                        json=payload,
                    )

            if resp.status_code != 200:
                try:
                    err_detail = resp.json().get("error", {})
                    if isinstance(err_detail, dict):
                        err_detail = err_detail.get("message", resp.text)
                except Exception:
                    err_detail = resp.text
                return {
                    "success": False,
                    "error": f"Image API error {resp.status_code}: {err_detail}"
                }

            result = resp.json()
            data_list = result.get("data") or []
            if not data_list:
                return {
                    "success": False,
                    "error": "No image data in response."
                }

            item = data_list[0]
            if item.get("b64_json"):
                image_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                with httpx.Client(timeout=120.0) as client:
                    img_resp = client.get(item["url"])
                    img_resp.raise_for_status()
                    image_bytes = img_resp.content
            else:
                return {
                    "success": False,
                    "error": "Response contained neither b64_json nor url."
                }

            out = self._save_or_return(image_bytes, output_path, prompt, reference_images)
            usage = result.get("usage") or {}
            if usage.get("cost") is not None:
                out["cost_usd"] = usage["cost"]
            return out

        except Exception as e:
            return {
                "success": False,
                "error": f"Image generation failed: {str(e)}"
            }
