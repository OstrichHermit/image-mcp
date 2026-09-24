#!/usr/bin/env python3
"""Image MCP Server - Universal image understanding and generation

手写 MCP 协议（newline-delimited JSON-RPC 2.0 over stdio），协议层仅用标准库。
复用同包 models/tools 的图像分析与生成流程。日志全部输出到 stderr，
stdout 仅输出协议消息。

依赖：httpx、Pillow、python-dotenv（业务层），无第三方 MCP 依赖。
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "image-mcp", "version": "2.0.0"}

# Lazy-loaded model instances
_models_initialized = False
_analyze_tool = None
_generate_tool = None
_gemini_model_flash = None
_gemini_model_pro = None
_openai_model_fast = None
_openai_model_pro = None
_layout_parsing_tool = None


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def write(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def reply(msg_id, result):
    write({"jsonrpc": "2.0", "id": msg_id, "result": result})


def reply_error(msg_id, code, message):
    write({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


async def _ensure_models():
    """Initialize models on first use (lazy loading)"""
    global _models_initialized, _analyze_tool, _generate_tool
    global _gemini_model_flash, _gemini_model_pro, _layout_parsing_tool
    global _openai_model_fast, _openai_model_pro

    if _models_initialized:
        return

    from src.models import QwenVLModel, GeminiImageModel, GlmOcrModel, OpenAIGPTImageModel
    from src.tools import AnalyzeImageTool, GenerateImageTool, LayoutParsingTool

    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY not found in environment")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    qwen_model = QwenVLModel(DASHSCOPE_API_KEY)
    _analyze_tool = AnalyzeImageTool(qwen_model)

    if OPENAI_API_KEY:
        _openai_model_fast = OpenAIGPTImageModel(OPENAI_API_KEY, use_pro_model=False)
        _openai_model_pro = OpenAIGPTImageModel(OPENAI_API_KEY, use_pro_model=True)
        _generate_tool = GenerateImageTool(_openai_model_fast)

    if GEMINI_API_KEY:
        # 构造失败（如未装 google-genai）只跳过该引擎，不炸全局初始化
        try:
            _gemini_model_flash = GeminiImageModel(GEMINI_API_KEY, use_pro_model=False)
            _gemini_model_pro = GeminiImageModel(GEMINI_API_KEY, use_pro_model=True)
            if not _generate_tool:
                _generate_tool = GenerateImageTool(_gemini_model_flash)
        except ImportError as ex:
            log(f"Gemini 引擎不可用，已跳过: {ex}")

    if ZHIPU_API_KEY:
        glm_ocr_model = GlmOcrModel(ZHIPU_API_KEY)
        _layout_parsing_tool = LayoutParsingTool(glm_ocr_model)

    _models_initialized = True


ANALYZE_IMAGE_TOOL = {
    "name": "analyze_image",
    "description": """[Local MCP Tool] Image analysis using Qwen VL model (通义千问 VL).

This is a LOCAL MCP server tool (NOT the remote ZHIPU 4_5v_mcp service).

Supports multiple analysis types:
- general: Describe and understand images
- ocr: Extract text from images
- screenshot: Extract text from code/terminal screenshots
- visualization: Analyze charts, graphs, and dashboards

Multi-Image Support:
- reference_images: Optional list of reference images to provide context for analysis.
  Use this when you need to compare or analyze the main image with reference images.
  Example: Comparing current photo with previous photos to identify changes.

Use this tool when user wants to:
- Understand what's in an image
- Extract text from an image
- Analyze a screenshot (code, terminal, error messages)
- Read charts or data visualizations
- Compare an image with reference images""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "image_source": {
                "type": "string",
                "description": "Local file path or URL to the image"
            },
            "prompt": {
                "type": "string",
                "description": "What to analyze, extract, or understand from the image"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["general", "ocr", "screenshot", "visualization"],
                "description": "Type of analysis to perform",
                "default": "general"
            },
            "reference_images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of reference image paths or URLs to provide context for analysis"
            }
        },
        "required": ["image_source", "prompt"]
    }
}

COMPARE_IMAGES_TOOL = {
    "name": "compare_images",
    "description": """Compare two images to identify differences.

Use this tool when:
- Comparing expected vs actual UI (diff check)
- Comparing before/after images
- Verifying design implementation vs mockup
- Any side-by-side comparison task""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "expected_image": {
                "type": "string",
                "description": "Reference image (mockup, expected, before)"
            },
            "actual_image": {
                "type": "string",
                "description": "Actual image (implementation, after)"
            },
            "prompt": {
                "type": "string",
                "description": "What aspects to focus on in the comparison"
            }
        },
        "required": ["expected_image", "actual_image", "prompt"]
    }
}

GENERATE_IMAGE_TOOL = {
    "name": "generate_image",
    "description": """Generate an image from text prompt.

Engine Selection (via engine parameter):
- openai (default when OPENAI_API_KEY is set): GPT Image 2.5 by OpenAI
  - Fast: gpt-image-2.5-flare (speed-first, default)
  - Pro: gpt-image-2.5-sunburst (editing-precision, set pro=true)
  - Quality tiers: low / medium / high / xhigh / max
- gemini: Gemini image models by Google
  - Flash (gemini-3.1-flash-image-preview): faster
  - Pro (gemini-3-pro-image-preview): higher quality (pro=true)

Supports two modes:
- Text-to-Image: Generate from text prompt only
- Image-to-Image (img2img): Generate using reference image(s) as base
  (openai: sent to /images/edits; gemini: multi-reference up to 14 images)

Use this tool when user wants to:
- Create an image from text description
- Generate visual content based on a prompt
- Create artwork, illustrations, or designs
- Edit or transform an existing image (provide reference_images)

The generated image will be saved to a file and the path will be returned.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the image to generate"
            },
            "engine": {
                "type": "string",
                "enum": ["openai", "gemini"],
                "description": "Generation engine (default: openai if OPENAI_API_KEY configured, otherwise gemini)"
            },
            "output_path": {
                "type": "string",
                "description": "Path to save the generated image. If not provided, will save to default directory (files/生成图/) with auto-generated filename."
            },
            "filename": {
                "type": "string",
                "description": "Optional custom filename without path (e.g., 'my_image.png'). If not provided, auto-generated filename will be used."
            },
            "reference_images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of paths to reference images for img2img mode (local file paths)"
            },
            "quality": {
                "type": "string",
                "enum": ["low", "medium", "high", "xhigh", "max", "auto"],
                "description": "Output quality (openai engine only, default: auto). xhigh/max are GPT Image 2.5 exclusive tiers. Higher = slower + more expensive."
            },
            "size": {
                "type": "string",
                "description": "Output size as WIDTHxHEIGHT, e.g. 1024x1024, 1536x1024, 1024x1536, 2048x2048 (openai engine only)"
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["auto", "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1"],
                "description": "Image aspect ratio (default: auto). Auto lets the model choose based on content. Includes ultra-wide options (1:4, 4:1, 1:8, 8:1) for panorama or banner images. For openai engine it is mapped to the closest supported size."
            },
            "resolution": {
                "type": "string",
                "enum": ["512px", "1K", "2K", "4K"],
                "description": "Image resolution (default: 512px). 512px for thumbnails, 1K for web, 2K for high-quality, 4K for professional/print. For openai engine it is mapped to the closest supported size."
            },
            "pro": {
                "type": "boolean",
                "description": "Use Pro model for higher quality (default: false). openai: gpt-image-2.5-sunburst; gemini: gemini-3-pro-image-preview"
            },
            "thinking_level": {
                "type": "string",
                "enum": ["HIGH", "MINIMAL"],
                "description": "Thinking level (gemini engine only, default: MINIMAL). Use HIGH for more thoughtful, detailed results."
            }
        },
        "required": ["prompt"]
    }
}

GENERATE_IMAGE_BATCH_TOOL = {
    "name": "generate_image_batch",
    "description": """Generate multiple images from text prompts using Gemini 2.5 Flash.

Use this tool when user wants to:
- Create multiple images at once
- Generate variations of a concept
- Batch process image generation

All images will be saved to the specified or default directory.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of text descriptions for images to generate"
            },
            "output_dir": {
                "type": "string",
                "description": "Optional directory to save images (default: generated_images/)"
            },
            "style": {
                "type": "string",
                "enum": ["vivid", "natural"],
                "description": "Image style",
                "default": "vivid"
            },
            "quality": {
                "type": "string",
                "enum": ["standard", "hd"],
                "description": "Image quality",
                "default": "standard"
            }
        },
        "required": ["prompts"]
    }
}

ANALYZE_IMAGE_OCR_TOOL = {
    "name": "analyze_image_ocr",
    "description": """[Local MCP Tool] Document layout parsing and OCR using GLM-OCR model (智谱 GLM-OCR).

Uses Zhipu AI's GLM-OCR model for advanced document layout parsing,
which can identify document structure, tables, paragraphs, headers,
and extract text with layout information preserved.

This is different from analyze_image's ocr mode:
- analyze_image ocr: Basic text extraction using Qwen VL
- analyze_image_ocr: Advanced layout-aware document parsing using GLM-OCR

Use this tool when user wants to:
- Parse document structure (headers, paragraphs, tables, lists)
- Extract text while preserving layout/formatting information
- OCR scanned documents with complex layouts
- Convert document images to structured text

Supports both local file paths and URLs.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "image_source": {
                "type": "string",
                "description": "Local file path or URL to the document image"
            }
        },
        "required": ["image_source"]
    }
}


TOOLS = [
    ANALYZE_IMAGE_TOOL,
    COMPARE_IMAGES_TOOL,
    GENERATE_IMAGE_TOOL,
    GENERATE_IMAGE_BATCH_TOOL,
    ANALYZE_IMAGE_OCR_TOOL,
]


def _to_content(items) -> list[dict]:
    """Normalize tool results (dicts or objects with .text) to MCP content dicts."""
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"type": "text", "text": item.text})
    return out


def _err_content(text: str) -> list[dict]:
    return [{"type": "text", "text": text}]


async def run_tool(name: str, args: dict) -> list[dict]:
    """Dispatch a tool call. Returns MCP content items (dict form)."""

    known = {t["name"] for t in TOOLS}
    if name not in known:
        raise ValueError(f"未知工具: {name}")

    # Initialize models on first call
    await _ensure_models()

    if name == "analyze_image":
        return _to_content(await _analyze_tool.analyze_image(
            image_source=args["image_source"],
            prompt=args["prompt"],
            analysis_type=args.get("analysis_type", "general"),
            reference_images=args.get("reference_images")
        ))

    if name == "compare_images":
        return _to_content(await _analyze_tool.compare_images(
            expected_image=args["expected_image"],
            actual_image=args["actual_image"],
            prompt=args["prompt"]
        ))

    if name == "generate_image":
        from src.tools import GenerateImageTool

        # Select engine: openai (GPT Image 2.5) by default, fallback to gemini
        engine = args.get("engine")
        if engine not in ("openai", "gemini"):
            engine = "openai" if _openai_model_fast else "gemini"

        if engine == "openai" and not _openai_model_fast:
            return _err_content("❌ OpenAI engine not available. Please configure OPENAI_API_KEY in .env file.")
        if engine == "gemini" and not _gemini_model_flash:
            return _err_content("❌ Gemini engine not available. Please configure GEMINI_API_KEY in .env file.")

        # Select model based on pro parameter
        use_pro = args.get("pro", False)
        if engine == "openai":
            selected_model = _openai_model_pro if use_pro else _openai_model_fast
        else:
            selected_model = _gemini_model_pro if use_pro else _gemini_model_flash

        # Create tool instance with selected model
        tool = GenerateImageTool(selected_model)

        return _to_content(await tool.generate_image(
            prompt=args["prompt"],
            output_path=args.get("output_path"),
            reference_images=args.get("reference_images"),
            filename=args.get("filename"),
            quality=args.get("quality"),
            size=args.get("size"),
            aspect_ratio=args.get("aspect_ratio"),
            resolution=args.get("resolution"),
            thinking_level=args.get("thinking_level", "MINIMAL")
        ))

    if name == "generate_image_batch":
        if not _generate_tool:
            return _err_content("❌ Image generation not available. Please configure OPENAI_API_KEY or GEMINI_API_KEY in .env file.")
        return _to_content(await _generate_tool.generate_image_batch(
            prompts=args["prompts"],
            output_dir=args.get("output_dir"),
            style=args.get("style", "vivid"),
            quality=args.get("quality", "standard")
        ))

    if name == "analyze_image_ocr":
        if not _layout_parsing_tool:
            return _err_content("❌ Layout parsing not available. Please configure ZHIPU_API_KEY in .env file.")
        return _to_content(await _layout_parsing_tool.layout_parsing(
            image_source=args["image_source"]
        ))

    raise ValueError(f"未知工具: {name}")


def handle(msg: dict):
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if isinstance(requested, str) else PROTOCOL_VERSION
        reply(msg_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "notifications/initialized" or method == "notifications/cancelled":
        pass
    elif method == "tools/list":
        reply(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            content = asyncio.run(run_tool(name, args))
            reply(msg_id, {"content": content})
        except Exception as ex:
            log(f"工具 {name} 执行失败: {ex}")
            reply(msg_id, {
                "content": [{"type": "text", "text": f"工具执行失败: {ex}"}],
                "isError": True,
            })
    elif method == "ping":
        reply(msg_id, {})
    elif msg_id is not None:
        reply_error(msg_id, -32601, f"方法不存在: {method}")


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    log(f"{SERVER_INFO['name']} v{SERVER_INFO['version']} 已启动（stdio，等待客户端）")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as ex:
            reply_error(None, -32700, f"JSON 解析失败: {ex}")
            continue
        handle(msg)


if __name__ == "__main__":
    main()
