# Image Caption Generator

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

A state-of-the-art multimodal model that generates descriptive captions for images using a BLIP encoder and GPT‑2 decoder, with support for multilingual output, style control via LoRA adapters, and multiple interfaces (REST API, Streamlit UI, CLI).

Created on Mar 2025

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [REST API](#rest-api)
  - [Streamlit Web Interface](#streamlit-web-interface)
- [Configuration](#configuration)
- [Roadmap & Progress](#roadmap--progress)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Features
- **Dual‑Pipeline Architecture**: BLIP vision encoder + GPT‑2 text decoder.
- **Multilingual Support**: Generate captions in several languages.
- **Style Control**: Adjust caption style using LoRA adapters.
- **Multiple Interfaces**:
  - REST API (FastAPI)
  - Interactive Web UI (Streamlit)
  - Command‑line tool
- **Utilities**: Image preprocessing, batch processing, model loading, dataset helpers.
- **Extensible**: Easy to plug in new backbones or adapters.
- **Production Ready**: Docker support, health checks, monitoring (planned).

## Project Structure
```
Image Caption Generator/
│
├─ generate_caption.py          # Simple inference script
├─ test_import.py               # Import sanity check
├─ train_dummy.py               # Dummy training loop (for CI)
│
├─ src/
│   ├─ api/
│   │   ├─ main.py              # FastAPI entry point
│   │   └─ __init__.py
│   │
│   ├─ cli/
│   │   ├─ caption_image.py     # CLI command
│   │   └─ __init__.py
│   │
│   ├─ core/
│   │   └─ __init__.py
│   │
│   ├─ models/
│   │   ├─ blip_encoder.py      # BLIP vision encoder
│   │   ├─ gpt2_decoder.py      # GPT‑2 text decoder
│   │   ├─ image_caption_model.py # Combined model wrapper
│   │   └─ __init__.py
│   │
│   ├─ pipelines/
│   │   └─ __init__.py          # (single, batch, style transfer pipelines – WIP)
│   │
│   ├─ storage/
│   │   └─ __init__.py
│   │
│   ├─ ui/
│   │   └─ __init__.py
│   │
│   └─ utils/
│       ├─ dataset.py           # Dataset loading helpers
│       ├─ hf_inference.py      # HuggingFace inference wrapper
│       ├─ image_utils.py       # Image preprocessing & augmentation
│       ├─ model_loader.py      # Model checkpoint loading
│       └─ __init__.py
│
└─ tests/
    ├─ test_model.py            # Unit tests for core components
    └─ (more tests to be added)
```

## Installation
```bash
# Clone the repository
git clone https://github.com/your-username/image-caption-generator.git
cd image-caption-generator

# Create a virtual environment (recommended)
python -m venv venv
source venv/Scripts/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt


*If a `requirements.txt` is not yet present, install the core packages manually:*
```bash
pip install torch torchvision transformers accelerate fastapi uvicorn streamlit
```

## Usage
### Command Line Interface
```bash
python -m src.cli.caption_image --image path/to/image.jpg --output caption.txt
```
Options:
- `--image`: Path to input image.
- `--output`: File to save the generated caption (optional).
- `--language`: Target language for multilingual caption (default: `en`).
- `--style`: LoRA adapter name for style control (optional).

### REST API
Start the server:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
Endpoint: `POST /caption`
```json
{
  "image": "<base64‑encoded image>",
  "language": "es",
  "style": "poetic"
}
```
Response:
```json
{
  "caption": "Una descripción en español del contenido de la imagen."
}
```

### Streamlit Web Interface
```bash
streamlit run src/web/app.py
```
Upload an image, select language/style, and click **Generate**.

## Configuration
Configuration files can be placed in `src/utils/config.py` or passed via environment variables:
- `MODEL_DIR`: Directory containing pretrained checkpoints.
- `DEFAULT_LANGUAGE`: Default output language.
- `ENABLE_STYLE_CONTROL`: Toggle LoRA adapters.

## Roadmap & Progress
| Phase | Description | Status |
|-------|-------------|--------|
| **1. Project Setup** | Directory tree, git, venv, config files | ✅ Completed |
| **2. Core Model Components** | BLIP encoder, GPT‑2 decoder, model manager, confidence estimation, multilingual support, LoRA style control | 🟡 Partially Implemented (encoders/decoders ready; manager, confidence, multilingual, LoRA WIP) |
| **3. Utilities** | Image processing, batch processing, logging, config loading | 🟡 Partially Implemented (image utils, dataset, model loader present; batch & logging pending) |
| **4. Pipelines** | Single image, batch, style transfer pipelines | 🔴 Not Started (pipeline modules only have `__init__.py`) |
| **5. Interfaces** | FastAPI API, Streamlit UI, CLI | ✅ Completed (basic endpoints/UI/CLI functional) |
| **6. Testing & QA** | Unit, integration, E2E tests, benchmarks | 🟡 Partially Implemented (some unit tests exist) |
| **7. Production Ready** | Dockerfile, docker‑compose, monitoring, health checks, deployment scripts | 🔴 Not Started |

*Overall completion: ~45%*

## Testing
Run the existing test suite:
```bash
pytest -v
```
Add new tests under `tests/` following the same naming convention.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome-feature`).
3. Commit your changes (`git commit -m 'Add awesome feature'`).
4. Push to the branch (`git push origin feature/awesome-feature`).
5. Open a Pull Request.

Please follow the [PEP 8](https://pep8.org/) style guide and include tests for new functionality.

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- [BLIP: Bootstrapping Language‑Image Pretraining](https://arxiv.org/abs/2201.12086)
- [GPT‑2: Language Models are Unsupervised Multitask Learners](https://cdn.openai.com/better-language-models/gpt2_1.5b_dataset.pdf)
- [LoRA: Low‑Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- Hugging Face 🤗 Transformers team for the excellent libraries.
