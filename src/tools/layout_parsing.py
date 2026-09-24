"""Document layout parsing tool for MCP"""

from pathlib import Path
from mcp.types import TextContent


class LayoutParsingTool:
    """Document layout parsing tool wrapper"""

    def __init__(self, model):
        self.model = model

    async def layout_parsing(self, image_source: str) -> list[TextContent]:
        """
        Document layout parsing using GLM-OCR.

        Args:
            image_source: Local file path or URL to the document image.
        """
        # Validate file exists for local paths
        if not image_source.startswith(("http://", "https://")):
            if not Path(image_source).exists():
                return [TextContent(
                    type="text",
                    text=f"Error: File not found: {image_source}"
                )]

        try:
            result = await self.model.layout_parsing(image_source)

            if result["success"]:
                return [TextContent(
                    type="text",
                    text=f"## Layout Parsing Result\n\n{result['content']}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: Layout parsing failed: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error during layout parsing: {str(e)}"
            )]
