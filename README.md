# Image MCP Server

通用图像 MCP 服务器，支持多个 AI 模型的图像理解和生成。

[English](README_EN.md) | [简体中文](README.md)

## 功能

- **图像理解**：描述图像内容、回答图像相关问题
- **多图识别**：支持多张参考图片的上下文分析
- **OCR**：从图像中提取文字（支持代码截图、终端输出）
- **文档版面解析**：基于 GLM-OCR 的版面感知 OCR（可选）
- **数据可视化分析**：分析图表、仪表盘
- **图像对比**：UI 差异检查、前后对比
- **图像生成**：OpenAI GPT Image 2.5（默认引擎），支持文生图与参考图编辑

## 支持的模型

### 图像理解
- **通义千问 VL（Qwen VL）**：`qwen3.5-plus` - 支持图像理解和深度思考

### 图像生成（默认引擎：OpenAI）
- **GPT Image 2.5 快速档**：`gpt-image-2.5-flare`（默认，速度优先）
- **GPT Image 2.5 精修档**：`gpt-image-2.5-sunburst`（编辑精度优先，设置 `pro=true`）
- **画质档位**：`low` / `medium` / `high` / `xhigh` / `max`
- **中转站支持**：通过 `OPENAI_BASE_URL` 指向任意 OpenAI 兼容端点（含 OpenRouter 自动适配）
- **备选引擎**：Gemini（`engine="gemini"`，Flash / Pro 两档）
- **可扩展**：智谱 AI、Stable Diffusion 等

**模型配置**：可通过环境变量 `OPENAI_IMAGE_MODEL_FAST` / `OPENAI_IMAGE_MODEL_PRO` / `GEMINI_FLASH_MODEL` / `GEMINI_PRO_MODEL` 自定义模型名称

## 安装

```bash
# 安装依赖
cd image-mcp
pip install -e .

# 必需依赖
pip install httpx Pillow python-dotenv

# 可选：使用 Gemini 备选引擎时需要
pip install google-generativeai
```

**注意**：协议层为手写 MCP（JSON-RPC 2.0 over stdio），无需任何第三方 MCP 框架

## 配置

### 1. 环境变量

编辑 `.env` 文件（参考 `.env.example`）：

```bash
# 通义千问 VL（图像理解）- 必需
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# OpenAI GPT Image 2.5（图像生成，默认引擎）
OPENAI_API_KEY=your_openai_api_key_here

# 中转 / 代理端点（可选，走 OpenAI 官方则留空）
# 例如第三方中转站: https://api.example-relay.com/v1（兼容 OpenRouter）
OPENAI_BASE_URL=

# GPT Image 2.5 模型配置（可选）
OPENAI_IMAGE_MODEL_FAST=gpt-image-2.5-flare
OPENAI_IMAGE_MODEL_PRO=gpt-image-2.5-sunburst

# Gemini（可选备选引擎，engine="gemini" 时使用）
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_FLASH_MODEL=gemini-3.1-flash-image-preview
GEMINI_PRO_MODEL=gemini-3-pro-image-preview

# 智谱 AI（文档版面解析 OCR，可选）
ZHIPU_API_KEY=your_zhipu_api_key_here
```

**获取 API Key**：
- 通义千问 VL：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
- OpenAI：https://platform.openai.com/api-keys
- Gemini：https://aistudio.google.com/app/apikey
- 智谱 AI：https://open.bigmodel.cn/

### 2. MCP 配置

在 `.mcp.json` 中添加：

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

> Windows 下如遇路径问题，可将 `command` 指向 venv 内 python.exe 绝对路径，或使用 `cmd /c cd /d <路径> && python -m src.server` 的方式启动。

## 工具

### analyze_image
通用图像分析工具（看图工具），支持：
- **general**：通用描述和理解
- **ocr**：文字识别（中英文）
- **screenshot**：代码/终端截图提取
- **visualization**：数据可视化分析

**多图支持**：
- `reference_images`：可选的参考图片列表，为主图片分析提供上下文
  - 用于对比分析、变化检测、风格参考等场景
  - 支持本地文件路径和 URL
  - 示例：对比当前照片与历史照片，识别变化

参数：
- `image_source`：本地文件路径或 URL（主图片）
- `prompt`：分析指令或问题
- `analysis_type`：分析类型（默认：general）
- `reference_images`：参考图片路径列表（可选）

示例：
```python
# 单图分析
analyze_image(
    image_source="photo.jpg",
    prompt="这张图片里有什么？"
)

# 多图识别 - 对比分析
analyze_image(
    image_source="current_photo.jpg",
    prompt="与之前的照片相比，有哪些变化？",
    reference_images=["photo1.jpg", "photo2.jpg", "photo3.jpg"]
)

# 多图识别 - 风格参考
analyze_image(
    image_source="new_design.jpg",
    prompt="这个设计是否与参考风格一致？",
    reference_images=["style_reference1.jpg", "style_reference2.jpg"]
)
```

### compare_images
对比两张图片的差异：
- UI 差异检查
- 前后对比
- 设计验证

参数：
- `expected_image`：参考图片路径
- `actual_image`：实际图片路径
- `prompt`：对比指令

### generate_image ✨
生成图像。默认引擎为 OpenAI GPT Image 2.5（需配置 `OPENAI_API_KEY`），`engine="gemini"` 可切换 Gemini（需 `GEMINI_API_KEY`）

**引擎与模型选择**（OpenAI，默认）：
- 快速档（默认）：`gpt-image-2.5-flare` - 速度优先
- 精修档：`gpt-image-2.5-sunburst` - 编辑精度优先（设置 `pro=true`）

**画质档位**（`quality`）：`low` / `medium`（默认）/ `high` / `xhigh` / `max`

支持两种模式：
- **Text-to-Image**：纯文本生成图像
- **Image-to-Image (img2img)**：使用参考图片生成新图像（编辑走 `/images/edits`，像素级保留）

参数：
- `prompt`：文本描述（必需）
- `engine`：生成引擎 - `openai`（默认，配置了 `OPENAI_API_KEY` 时）/ `gemini`
- `pro`：精修档开关（默认 false）
- `quality`：画质档位（OpenAI 引擎）
- `output_path`：保存路径（可选，默认自动生成在 `files/generated_images/`）
- `reference_images`：参考图片路径列表（可选）
- `aspect_ratio`：图像比例 - `1:1`, `16:9`, `9:16`, `21:9` 等
- `resolution`：图像分辨率 - `1K`, `2K`（默认）, `4K`

示例：
```python
# Text-to-Image：纯文本生成（默认 1:1, 2K, medium 画质）
generate_image(
    prompt="一只可爱的小猫在花园里"
)

# 精修档 + 高画质
generate_image(
    prompt="风景画，山脉和湖泊",
    pro=True,
    quality="high",
    aspect_ratio="16:9"
)

# Image-to-Image：参考图编辑
generate_image(
    prompt="把这只猫变成卡通风格",
    reference_images=["path/to/cat.jpg"]
)

# 切换 Gemini 引擎
generate_image(
    prompt="赛博朋克城市夜景",
    engine="gemini"
)
```

### generate_image_batch ✨
批量生成多张图像

参数：
- `prompts`：文本描述列表（必需）
- `output_dir`：保存目录（可选，默认 `generated_images/`）
- `style`：图像风格
- `quality`：图像质量

示例：
```python
# 批量生成
generate_image_batch(
    prompts=["猫", "狗", "鸟"],
    output_dir="my_images"
)
```

## 架构

可插拔的模型设计，方便添加新的 AI 模型：

```
src/
├── server.py          # MCP 服务器主入口
├── models/
│   ├── base.py        # 基础模型接口
│   ├── qwen.py        # 通义千问 VL（图像理解）
│   └── gemini.py      # Gemini（图像生成备选引擎）
└── tools/
    ├── analyze.py     # 图像分析工具
    └── generate.py    # 图像生成工具
```

## 松耦合设计

所有模型都实现 `BaseImageModel` 接口：

```python
class BaseImageModel(ABC):
    @abstractmethod
    async def analyze_image(...): pass

    @abstractmethod
    async def ocr(...): pass

    @abstractmethod
    async def generate_image(...): pass
```

这样可以轻松切换或添加新模型，无需修改工具层代码。

## 使用示例

### 基础图像分析
```python
# 分析图片内容
analyze_image(
    image_source="photo.jpg",
    prompt="这张图片里有什么？"
)
```

### 多图识别 - 对比分析
```python
# 对比当前照片与历史照片
analyze_image(
    image_source="current_photo.jpg",
    prompt="与之前的照片相比，有哪些变化？",
    reference_images=[
        "photo_morning.jpg",
        "photo_noon.jpg",
        "photo_evening.jpg"
    ]
)

# 设计风格对比
analyze_image(
    image_source="new_design.jpg",
    prompt="这个新设计是否与参考风格保持一致？",
    reference_images=[
        "style_guide1.jpg",
        "style_guide2.jpg"
    ]
)
```

### OCR 文字识别
```python
# 提取文字
analyze_image(
    image_source="screenshot.png",
    prompt="提取所有文字",
    analysis_type="ocr"
)
```

### 图像生成
```python
# Text-to-Image：从零生成（默认 1:1, 2K）
generate_image(
    prompt="一只在太空中游泳的鲸鱼，星云背景"
)

# Text-to-Image：自定义比例
generate_image(
    prompt="赛博朋克城市夜景，霓虹灯",
    aspect_ratio="21:9",
    resolution="4K"
)

# Image-to-Image：多参考图生成
generate_image(
    prompt="生成一张结合这些风格的新图片",
    reference_images=[
        "style1.jpg",
        "style2.jpg",
        "style3.jpg"
    ]
)
```

## 扩展新模型

1. 在 `src/models/` 创建新模型类，继承 `BaseImageModel`
2. 实现所有抽象方法
3. 在 `src/server.py` 中注册新模型

示例：

```python
# src/models/my_model.py
from .base import BaseImageModel

class MyImageModel(BaseImageModel):
    async def analyze_image(self, ...):
        # 你的实现
        pass

    async def ocr(self, ...):
        pass

    async def generate_image(self, ...):
        pass
```

## 故障排查

### MCP 无法连接
- 检查 `.env` 文件中的 API Key 是否正确
- 确认所有依赖已安装：`pip install httpx Pillow python-dotenv`

### 图像生成失败
- OpenAI 引擎：确认已配置 `OPENAI_API_KEY`（走中转站时还需 `OPENAI_BASE_URL`）
- Gemini 引擎：确认已配置 `GEMINI_API_KEY`
- 检查网络连接（适配器内置 3 次重试）
- 查看 API 配额限制

## License

MIT
