"""Qwen (通义千问多模态模型) implementation"""

import base64
import httpx
from typing import Dict, Any, Optional
from .base import BaseImageModel


class QwenVLModel(BaseImageModel):
    """
    Qwen multimodal model for image understanding

    Model: qwen3.5-plus (supports vision and deep thinking)
    API Docs: https://help.aliyun.com/zh/model-studio/developer-reference/use-qwen-vl
    """

    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.model_name = "qwen3.5-plus"  # 支持图像理解和深度思考

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        max_tokens: int = 1000,
        reference_images: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze image with Qwen VL

        Args:
            image_path: Local path or URL
            prompt: Question or instruction
            max_tokens: Max response tokens
            reference_images: Optional list of reference image paths or URLs
        """
        try:
            # Prepare main image content
            if image_path.startswith("http"):
                image_content = {"image": image_path}
            else:
                # Local file - encode to base64
                base64_data = self._encode_image_base64(image_path)
                image_content = {"image": f"data:image;base64,{base64_data}"}

            # Prepare reference images if provided
            ref_image_contents = []
            if reference_images:
                for ref_img_path in reference_images:
                    if ref_img_path.startswith("http"):
                        ref_image_contents.append({"image": ref_img_path})
                    else:
                        # Local file - encode to base64
                        base64_data = self._encode_image_base64(ref_img_path)
                        ref_image_contents.append({"image": f"data:image;base64,{base64_data}"})

            # Build content list - main image + reference images + prompt
            content_list = []

            # Add reference images first if provided
            if ref_image_contents:
                content_list.append({"text": "参考图片："})
                content_list.extend(ref_image_contents)

            # Add main image
            content_list.append(image_content)

            # Add prompt
            content_list.append({"text": prompt})

            # Prepare message
            message = [
                {"role": "system", "content": "你是一个专业的图像分析助手。"},
                {
                    "role": "user",
                    "content": content_list
                }
            ]

            # API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "input": {
                    "messages": message
                },
                "parameters": {
                    "max_tokens": max_tokens,
                    "result_format": "message",
                    "enable_thinking": True
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

            # Extract response
            if result.get("output"):
                content = result["output"]["choices"][0]["message"]["content"][0]["text"]
                return {
                    "success": True,
                    "content": content,
                    "model": self.model_name,
                    "usage": result.get("usage", {})
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error"),
                    "raw": result
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
        OCR with Qwen VL

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

    async def extract_text_from_screenshot(
        self,
        image_path: str,
        programming_language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from screenshot (specialized for code/terminal)

        Args:
            image_path: Path to screenshot
            programming_language: Optional hint (python, javascript, etc.)
        """
        if programming_language:
            prompt = f"这是一个 {programming_language} 代码截图。请提取所有代码内容，保持原有格式和缩进。"
        else:
            prompt = "请提取这张截图中的所有文本内容。如果是代码，请保持原有格式。如果是终端输出，请完整提取。"

        return await self.analyze_image(image_path, prompt, max_tokens=3000)

    async def analyze_data_visualization(
        self,
        image_path: str,
        prompt: str,
        analysis_focus: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze data visualization (charts, graphs, dashboards)

        Args:
            image_path: Path to visualization
            prompt: What to analyze
            analysis_focus: Optional focus (trends, anomalies, comparisons, etc.)
        """
        enhanced_prompt = f"""分析这个数据可视化：

用户需求：{prompt}

请提供：
1. 可视化类型识别（柱状图、折线图、饼图等）
2. 关键数据和指标
3. 趋势和模式
4. 异常值或特殊点
5. 洞察和结论
"""

        if analysis_focus:
            enhanced_prompt += f"\n\n重点关注：{analysis_focus}"

        return await self.analyze_image(image_path, enhanced_prompt, max_tokens=1500)

    async def compare_images(
        self,
        image_path1: str,
        image_path2: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Compare two images (UI diff, before/after, etc.)

        Args:
            image_path1: First image path
            image_path2: Second image path
            prompt: Comparison instructions
        """
        try:
            # Prepare both images
            if image_path1.startswith("http"):
                img1 = {"image": image_path1}
            else:
                base64_1 = self._encode_image_base64(image_path1)
                img1 = {"image": f"data:image;base64,{base64_1}"}

            if image_path2.startswith("http"):
                img2 = {"image": image_path2}
            else:
                base64_2 = self._encode_image_base64(image_path2)
                img2 = {"image": f"data:image;base64,{base64_2}"}

            message = [
                {"role": "system", "content": "你是一个专业的图像对比分析助手。"},
                {
                    "role": "user",
                    "content": [
                        {"text": f"请对比这两张图片：{prompt}"},
                        img1,
                        img2
                    ]
                }
            ]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "input": {
                    "messages": message
                },
                "parameters": {
                    "max_tokens": 2000,
                    "result_format": "message",
                    "enable_thinking": True
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

            if result.get("output"):
                content = result["output"]["choices"][0]["message"]["content"][0]["text"]
                return {
                    "success": True,
                    "content": content,
                    "model": self.model_name
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error")
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        reference_image: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Qwen VL does not support image generation.
        This method is provided for interface compatibility.
        """
        return {
            "success": False,
            "error": "Qwen VL model does not support image generation. Please use a model that supports image generation (e.g., Gemini, DALL-E, etc.)"
        }
