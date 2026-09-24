"""Image generation tools for MCP"""

import os
from typing import Optional
from pathlib import Path
from mcp.types import TextContent


class GenerateImageTool:
    """Image generation tool wrapper"""

    def __init__(self, model):
        self.model = model
        # Default output directory (in workspace root files folder)
        # Get workspace root: image-mcp/src/tools/generate.py -> image-mcp -> workspace root
        workspace_root = Path(__file__).parent.parent.parent.parent
        self.default_output_dir = workspace_root / "files" / "生成图"
        self.default_output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        filename: Optional[str] = None,
        **kwargs
    ) -> list[TextContent]:
        """
        Generate an image from text prompt

        Args:
            prompt: Text description of the image to generate
            output_path: Optional path to save the generated image
            filename: Optional custom filename (without path, e.g., "my_image.png")
            **kwargs: Additional model-specific parameters
                - reference_images: List of reference image paths for img2img
                - size: Image size (e.g., "1024x1024")
                - quality: Image quality ("standard" or "hd")
                - style: Image style ("vivid" or "natural")
                - temperature: Creativity level (0.0-1.0)
        """
        try:
            # Generate default output path if not provided
            if not output_path:
                # Use custom filename if provided, otherwise generate default
                if filename:
                    # Ensure filename has .png extension
                    clean_filename = filename if filename.endswith('.png') else f"{filename}.png"
                    output_path = str(self.default_output_dir / clean_filename)
                else:
                    import uuid
                    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                    reference_images = kwargs.get("reference_images", [])
                    mode_prefix = "img2img" if reference_images else "gen"
                    auto_filename = f"{mode_prefix}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
                    output_path = str(self.default_output_dir / auto_filename)
            else:
                # Ensure user-provided output_path has file extension
                output_path_obj = Path(output_path)
                if not output_path_obj.suffix:
                    # If no extension, add .png by default
                    output_path = str(output_path_obj.with_suffix('.png'))
                elif output_path_obj.is_dir():
                    # If it's a directory, generate filename in that directory
                    import uuid
                    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                    reference_images = kwargs.get("reference_images", [])
                    mode_prefix = "img2img" if reference_images else "gen"
                    auto_filename = f"{mode_prefix}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
                    output_path = str(output_path_obj / auto_filename)

            # Call model to generate image
            result = await self.model.generate_image(
                prompt=prompt,
                output_path=output_path,
                **kwargs
            )

            if result["success"]:
                mode = result.get("mode", "text2img")
                mode_emoji = "🖼️→🖼️" if mode == "img2img" else "📝→🖼️"

                response_parts = [
                    f"✅ Image Generated Successfully! {mode_emoji}\n",
                    f"\n📝 Prompt:\n{prompt}\n",
                ]

                # Show reference images if used
                ref_images = result.get("reference_images", [])
                if ref_images:
                    if len(ref_images) == 1:
                        response_parts.append(
                            f"\n🖼️ Reference Image: `{ref_images[0]}`\n"
                        )
                    else:
                        response_parts.append(
                            f"\n🖼️ Reference Images ({len(ref_images)}):\n"
                        )
                        for idx, ref_img in enumerate(ref_images, 1):
                            response_parts.append(f"  {idx}. `{ref_img}`\n")

                # Show image configuration if provided
                if result.get("aspect_ratio"):
                    response_parts.append(
                        f"\n📐 Aspect Ratio: {result['aspect_ratio']}\n"
                    )
                if result.get("resolution"):
                    response_parts.append(
                        f"\n🔍 Resolution: {result['resolution']}\n"
                    )

                response_parts.extend([
                    f"\n📁 Saved to: `{result['image_path']}`\n",
                    f"\n🤖 Model: {result.get('model', 'Unknown')}\n",
                    f"\n🔧 Mode: {mode}\n"
                ])

                # Get file size
                if result["image_path"]:
                    file_size = Path(result["image_path"]).stat().st_size
                    response_parts.append(f"📊 Size: {file_size / 1024:.1f} KB\n")

                return [TextContent(
                    type="text",
                    text="".join(response_parts)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Image generation failed: {result.get('error', 'Unknown error')}"
                )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error during image generation: {str(e)}"
            )]

    async def generate_image_batch(
        self,
        prompts: list[str],
        output_dir: Optional[str] = None,
        **kwargs
    ) -> list[TextContent]:
        """
        Generate multiple images from text prompts

        Args:
            prompts: List of text descriptions
            output_dir: Optional directory to save images
            **kwargs: Additional model-specific parameters
        """
        try:
            import uuid
            from datetime import datetime

            # Use provided output dir or default
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self.default_output_dir

            results = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for idx, prompt in enumerate(prompts):
                filename = f"batch_{timestamp}_{idx+1}_{uuid.uuid4().hex[:8]}.png"
                file_path = str(output_path / filename)

                result = await self.model.generate_image(
                    prompt=prompt,
                    output_path=file_path,
                    **kwargs
                )

                results.append({
                    "index": idx + 1,
                    "prompt": prompt,
                    "result": result
                })

            # Build response
            response_lines = [
                "✅ Batch Image Generation Complete!\n",
                f"\n📊 Total: {len(prompts)} images\n",
            ]

            success_count = 0
            for item in results:
                if item["result"]["success"]:
                    success_count += 1
                    response_lines.append(
                        f"\n✅ [{item['index']}] {item['prompt'][:50]}...\n"
                        f"   → {item['result']['image_path']}\n"
                    )
                else:
                    response_lines.append(
                        f"\n❌ [{item['index']}] {item['prompt'][:50]}...\n"
                        f"   → {item['result'].get('error', 'Unknown error')}\n"
                    )

            response_lines.append(f"\n✨ Success: {success_count}/{len(prompts)}\n")

            return [TextContent(
                type="text",
                text="".join(response_lines)
            )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error during batch generation: {str(e)}"
            )]
