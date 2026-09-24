# Image MCP Server

A universal image MCP server supporting multiple AI models for image understanding and generation.

[English](README_EN.md) | [简体中文](README.md)

## Features

- **Image Understanding**: Describe image content, answer questions about images
- **Multi-Image Analysis**: Contextual analysis with multiple reference images
- **OCR**: Extract text from images (code screenshots, terminal output)
- **Data Visualization Analysis**: Analyze charts and dashboards
- **Image Comparison**: UI diff checking, before/after comparison
- **Image Generation**: OpenAI GPT Image 2.5 (default engine), text-to-image & reference-guided editing

## Supported Models

### Image Understanding
- **Qwen VL (Tongyi Qianwen)**: `qwen3.5-plus` - image understanding with deep thinking

### Image Generation (default engine: OpenAI)
- **GPT Image 2.5 Fast**: `gpt-image-2.5-flare` (default, speed-first)
- **GPT Image 2.5 Pro**: `gpt-image-2.5-sunburst` (editing-precision-first, set `pro=true`)
- **Quality tiers**: `low` / `medium` / `high` / `xhigh` / `max`
- **Relay-friendly**: point `OPENAI_BASE_URL` at any OpenAI-compatible endpoint (OpenRouter auto-detected)
- **Fallback engine**: Gemini (`engine="gemini"`, Flash / Pro)
- **Extensible**: Zhipu AI, Stable Diffusion, etc.

**Model Configuration**: Customize model names via the `OPENAI_IMAGE_MODEL_FAST` / `OPENAI_IMAGE_MODEL_PRO` / `GEMINI_FLASH_MODEL` / `GEMINI_PRO_MODEL` environment variables

## Installation

```bash
cd image-mcp
pip install -e .

# Required dependencies
pip install httpx Pillow python-dotenv

# Optional: only needed for the Gemini fallback engine
pip install google-generativeai
```

**Note**: The protocol layer is a hand-written MCP implementation (JSON-RPC 2.0 over stdio) — no third-party MCP framework required

## Configuration

### 1. Environment Variables

Edit the `.env` file (see `.env.example`):

```bash
# Qwen VL (image understanding) - required
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# OpenAI GPT Image 2.5 (image generation, default engine)
OPENAI_API_KEY=your_openai_api_key_here

# Relay / proxy endpoint (optional, leave empty for official OpenAI)
# e.g. a third-party relay: https://api.example-relay.com/v1 (OpenRouter compatible)
OPENAI_BASE_URL=

# GPT Image 2.5 model configuration (optional)
OPENAI_IMAGE_MODEL_FAST=gpt-image-2.5-flare
OPENAI_IMAGE_MODEL_PRO=gpt-image-2.5-sunburst

# Gemini (optional fallback engine, engine="gemini")
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_FLASH_MODEL=gemini-3.1-flash-image-preview
GEMINI_PRO_MODEL=gemini-3-pro-image-preview

# Zhipu AI (layout-aware document OCR, optional)
ZHIPU_API_KEY=your_zhipu_api_key_here
```

**Get API Keys**:
- Qwen VL: https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
- OpenAI: https://platform.openai.com/api-keys
- Gemini: https://aistudio.google.com/app/apikey
- Zhipu AI: https://open.bigmodel.cn/

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
Generate images. Default engine is OpenAI GPT Image 2.5 (requires `OPENAI_API_KEY`); set `engine="gemini"` to use Gemini (requires `GEMINI_API_KEY`)

**Engine & Model Selection** (OpenAI, default):
- Fast (default): `gpt-image-2.5-flare` - speed-first
- Pro: `gpt-image-2.5-sunburst` - editing-precision-first (set `pro=true`)

**Quality tiers** (`quality`): `low` / `medium` (default) / `high` / `xhigh` / `max`

Two modes:
- **Text-to-Image**: generate from text only
- **Image-to-Image (img2img)**: generate using reference image(s) (edits go through `/images/edits`, pixel-level preservation)

Parameters:
- `prompt`: text description (required)
- `engine`: generation engine - `openai` (default when `OPENAI_API_KEY` is set) / `gemini`
- `pro`: use the precision tier (default false)
- `quality`: quality tier (OpenAI engine)
- `output_path`: save path (optional, defaults to auto-generated name in `files/generated_images/`)
- `reference_images`: reference image path list (optional)
- `aspect_ratio`: `1:1`, `16:9`, `9:16`, `21:9`, etc.
- `resolution`: `1K`, `2K` (default), `4K`

Example:
```python
# Text-to-Image (default 1:1, 2K, medium quality)
generate_image(prompt="A cute cat in a garden")

# Precision tier + high quality
generate_image(
    prompt="Landscape painting with mountains and a lake",
    pro=True,
    quality="high",
    aspect_ratio="16:9"
)

# Image-to-Image with a reference
generate_image(
    prompt="Turn this cat into cartoon style",
    reference_images=["path/to/cat.jpg"]
)

# Switch to the Gemini engine
generate_image(
    prompt="Cyberpunk city at night",
    engine="gemini"
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
- Confirm all dependencies are installed: `pip install httpx Pillow python-dotenv`

### Image generation fails
- OpenAI engine: confirm `OPENAI_API_KEY` is configured (plus `OPENAI_BASE_URL` when using a relay)
- Gemini engine: confirm `GEMINI_API_KEY` is configured
- Check network connectivity (the adapter retries 3 times)
- Check API quota limits

## License

MIT
