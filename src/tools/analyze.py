"""Image analysis tools for MCP"""

import os
from typing import Optional
from pathlib import Path
from mcp.types import TextContent


class AnalyzeImageTool:
    """Image analysis tool wrapper"""

    def __init__(self, model):
        self.model = model

    async def analyze_image(
        self,
        image_source: str,
        prompt: str,
        analysis_type: str = "general",
        reference_images: Optional[list] = None
    ) -> list[TextContent]:
        """
        General-purpose image analysis

        Args:
            image_source: Local file path or URL
            prompt: What to analyze/extract/understand
            analysis_type: Type of analysis (general, ocr, screenshot, visualization, ui_diff)
            reference_images: Optional list of reference image paths or URLs
        """
        # Validate image exists
        if not image_source.startswith("http"):
            if not Path(image_source).exists():
                return [TextContent(
                    type="text",
                    text=f"❌ Error: Image file not found: {image_source}"
                )]

        # Validate reference images if provided
        if reference_images:
            for ref_img in reference_images:
                if not ref_img.startswith("http"):
                    if not Path(ref_img).exists():
                        return [TextContent(
                            type="text",
                            text=f"❌ Error: Reference image not found: {ref_img}"
                        )]

        # Route to appropriate method
        try:
            if analysis_type == "ocr":
                result = await self.model.ocr(image_source)
            elif analysis_type == "screenshot":
                result = await self.model.extract_text_from_screenshot(image_source)
            elif analysis_type == "visualization":
                # Extract focus from prompt if provided
                result = await self.model.analyze_data_visualization(image_source, prompt)
            else:  # general
                result = await self.model.analyze_image(
                    image_source,
                    prompt,
                    reference_images=reference_images
                )

            if result["success"]:
                return [TextContent(
                    type="text",
                    text=f"✅ Analysis Result:\n\n{result['content']}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Analysis failed: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error during analysis: {str(e)}"
            )]

    async def compare_images(
        self,
        expected_image: str,
        actual_image: str,
        prompt: str
    ) -> list[TextContent]:
        """
        Compare two images (UI diff, before/after)

        Args:
            expected_image: Reference image path
            actual_image: Actual image path
            prompt: Comparison instructions
        """
        # Validate both images exist
        for img_path, name in [(expected_image, "expected"), (actual_image, "actual")]:
            if not img_path.startswith("http"):
                if not Path(img_path).exists():
                    return [TextContent(
                        type="text",
                        text=f"❌ Error: {name} image not found: {img_path}"
                    )]

        try:
            result = await self.model.compare_images(expected_image, actual_image, prompt)

            if result["success"]:
                return [TextContent(
                    type="text",
                    text=f"✅ Comparison Result:\n\n{result['content']}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Comparison failed: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error during comparison: {str(e)}"
            )]
