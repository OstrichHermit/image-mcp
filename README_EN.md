# Image MCP Server

A universal image MCP server supporting multiple AI models for image understanding and generation.

[English](README_EN.md) | [简体中文](README.md)

## Features

- **Image Understanding**: Describe image content, answer questions about images
- **Multi-Image Analysis**: Contextual analysis with multiple reference images
- **OCR**: Extract text from images (code screenshots, terminal output)
- **Data Visualization Analysis**: Analyze charts and dashboards
- **Image Comparison**: UI diff checking, before/after comparison
- **Image Generation**: Generate images with Gemini image models (extensible)

## Supported Models

### Image Understanding
- **Qwen VL (Tongyi Qianwen)**: `qwen3.5-plus` - image understanding with deep thinking

### Image Generation
- **Gemini Flash**: `gemini-3.1-flash-image-preview` (default, fast)
- **Gemini Pro**: `gemini-3-pro-image-preview` (high quality, set `pro=true`)
- **Extensible**: Zhipu AI, DALL-E, Stable Diffusion, etc.

**Model Configuration**: Customize model names via the `GEMINI_FLASH_MODEL` and `GEMINI_PRO_MODEL` environment variables

## Installation

```bash
cd image-mcp
pip install -e .

# Required dependencies
pip install mcp httpx Pillow python-dotenv google-generativeai
```

**Note**: `google-generativeai` requires version >= 0.8.0 for the Gemini image generation API

## Configuration

### 1. Environment Variables

Edit the `.env` file:

```bash
# Qwen VL (image understanding) - required
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Gemini (image generation) - optional
GEMINI_API_KEY=your_gemini_api_key_here

# Gemini model configuration (optional, defaults are used if not set)
# Flash model (default, fast)
GEMINI_FLASH_MODEL=gemini-3.1-flash-image-preview
# Pro model (high quality)
GEMINI_PRO_MODEL=gemini-3-pro-image-preview
```

**Get API Keys**:
- Qwen VL: https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
- Gemini: https://aistudio.google.com/app/apikey

### 2. MCP Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "image-mcp": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/image-mcp",
      "env": {
        "DASHSCOPE_API_KEY": "your_dashscope_api_key",
        "GEMINI_API_KEY": "your_gemini_api_key"
      }
    }
  }
}
```

> On Windows, you may need `"command": "cmd"` with `"args": ["/c", "cd", "/d", "<path>", "&&", "python", "-m", "src.server"]`, or point `command` directly at a venv python executable.

## Tools

### analyze_image
General-purpose image analysis tool:
- **general**: general description and understanding
- **ocr**: text recognition (Chinese & English)
- **screenshot**: extract text from code/terminal screenshots
- **visualization**: data visualization analysis

**Multi-Image Support**:
- `reference_images`: optional list of reference images providing context for the main image
  - For comparison, change detection, style reference, etc.
  - Supports local file paths and URLs
  - Example: compare a current photo with historical photos to identify changes

Parameters:
- `image_source`: local file path or URL (main image)
- `prompt`: analysis instruction or question
- `analysis_type`: analysis type (default: general)
- `reference_images`: optional list of reference image paths

Example:
```python
# Single image analysis
analyze_image(
    image_source="photo.jpg",
    prompt="What is in this image?"
)

# Multi-image comparison
analyze_image(
    image_source="current_photo.jpg",
    prompt="What changed compared to the previous photos?",
    reference_images=["photo1.jpg", "photo2.jpg", "photo3.jpg"]
)
```

### compare_images
Compare two images for differences:
- UI diff checking
- Before/after comparison
- Design verification

Parameters:
- `expected_image`: reference image path
- `actual_image`: actual image path
- `prompt`: comparison instruction

### generate_image
Generate images with Gemini (requires `GEMINI_API_KEY`)

**Model Selection**:
- Flash (default): `gemini-3.1-flash-image-preview` - fast
- Pro: `gemini-3-pro-image-preview` - high quality (set `pro=true`)

Customizable via environment variables:
- `GEMINI_FLASH_MODEL`: Flash model name
- `GEMINI_PRO_MODEL`: Pro model name

Two modes:
- **Text-to-Image**: generate from text only
- **Image-to-Image (img2img)**: generate using reference image(s)

Parameters:
- `prompt`: text description (required)
- `output_path`: save path (optional, defaults to auto-generated name in `files/generated_images/`)
- `reference_image`: reference image path (optional)
- `aspect_ratio`: `1:1`, `16:9`, `9:16`, `21:9`, etc.
- `resolution`: `1K`, `2K` (default), `4K`

Example:
```python
# Text-to-Image (default 1:1, 2K)
generate_image(prompt="A cute cat in a garden")

# Custom ratio and resolution
generate_image(
    prompt="Landscape painting with mountains and a lake",
    aspect_ratio="16:9",
    resolution="4K"
)

# Image-to-Image with a reference
generate_image(
    prompt="Turn this cat into cartoon style",
    reference_image="path/to/cat.jpg"
)
```

### generate_image_batch
Batch-generate multiple images

Parameters:
- `prompts`: list of text descriptions (required)
- `output_dir`: save directory (optional, default `generated_images/`)
- `style`: image style
- `quality`: image quality

Example:
```python
generate_image_batch(
    prompts=["cat", "dog", "bird"],
    output_dir="my_images"
)
```

## Architecture

Pluggable model design makes it easy to add new AI models:

```
src/
├── server.py          # MCP server entry point
├── models/
│   ├── base.py        # Base model interface
│   ├── qwen.py        # Qwen VL (image understanding)
│   └── gemini.py      # Gemini (image generation)
└── tools/
    ├── analyze.py     # Image analysis tools
    └── generate.py    # Image generation tools
```

## Loose Coupling

All models implement the `BaseImageModel` interface:

```python
class BaseImageModel(ABC):
    @abstractmethod
    async def analyze_image(...): pass

    @abstractmethod
    async def ocr(...): pass

    @abstractmethod
    async def generate_image(...): pass
```

This makes it easy to swap or add new models without touching the tool layer.

## Extending with New Models

1. Create a new model class in `src/models/` inheriting from `BaseImageModel`
2. Implement all abstract methods
3. Register the new model in `src/server.py`

Example:

```python
# src/models/my_model.py
from .base import BaseImageModel

class MyImageModel(BaseImageModel):
    async def analyze_image(self, ...):
        # your implementation
        pass

    async def ocr(self, ...):
        pass

    async def generate_image(self, ...):
        pass
```

## Troubleshooting

### MCP fails to connect
- Check that API keys in `.env` are correct
- Confirm all dependencies are installed: `pip install mcp httpx Pillow python-dotenv google-generativeai`

### Image generation fails
- Confirm `GEMINI_API_KEY` is configured
- Check network connectivity
- Check API quota limits

## License

MIT
