# Customer Support Bot

An end‑to‑end customer‑support chatbot built by fine‑tuning an open‑source LLM on the Bitext customer‑support dataset using **QLoRA/LoRA** with Hugging Face 🤗 Transformers, TRL, PEFT, and Gradio.

---

## Table of Contents

- [Features](#features)  
- [Project Structure](#project-structure)  
- [Installation](#installation)  
- [Quick Start](#quick-start)  
- [Data Preparation](#data-preparation)  
- [Training](#training)  
- [Inference & UI](#inference--ui)  
- [Configuration](#configuration)  
- [Dependencies](#dependencies)  
- [Troubleshooting](#troubleshooting)  
- [License](#license)  
- [Citation](#citation)

---

## Features

- **QLoRA fine‑tuning** (4‑bit NF4 quantization + LoRA adapters) for low‑VRAM training.  
- Support for multiple base models (`TinyLlama‑1.1B‑Chat`, `Phi‑2`, `Mistral‑7B‑Instruct`).  
- Streaming text generation via `TextStreamer` + Gradio `yield`.  
- Gradio ChatInterface with:
  - System‑prompt configuration panel.  
  - Intent‑category display sidebar (placeholder).  
  - Temperature / top‑p / max‑new‑tokens sliders.  
  - Conversation‑history management.  
  - Export chat log button.
- Modular codebase: data preparation, training, inference, and UI are cleanly separated.  
- Includes a sample notebook walkthrough (`notebooks/01_finetune_walkthrough.ipynb`).

---

## Project Structure

```
Customer Support Bot/
├── requirements.txt               ← Python dependencies
├── README.md                      ← This file
│
├── data/
│   ├── prepare_data.py            ← Download & format Bitext dataset
│   └── sample_data.jsonl          ← Tiny example JSONL for quick testing
│
├── training/
│   ├── train.py                   ← Main QLoRA fine‑tuning script (SFTTrainer)
│   └── config.yaml                ← Hyper‑parameters & paths
│
├── inference/
│   ├── model_loader.py            ← Load base model + LoRA adapter (merge optional)
│   └── generate.py                ← Text‑generation helper with streaming
│
├── app/
│   └── chatbot_ui.py              ← Gradio ChatInterface
│
└── notebooks/
    └── 01_finetune_walkthrough.ipynb  ← Annotated end‑to‑end notebook
```

---

## Installation

1. **Clone the repository**
  ```bash
   git clone https://github.com/your-username/Customer-Support-Bot.git
   cd Customer-Support-Bot
  ```
2. **Create (optional) a virtual environment**
  ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
  ```
3. **Install dependencies**
  ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
  ```
  > **Note:** The `requirements.txt` pins versions known to work together. Feel free to adjust for your environment.

---

## Quick Start

```bash
# 1️⃣ Prepare the dataset (downloads from HF Hub and formats to chat‑template)
python data/prepare_data.py

# 2️⃣ Fine‑tune the model (QLoRA + SFTTrainer)
python training/train.py   # will download the base model the first time

# 3️⃣ Launch the Gradio UI
python -m app.chatbot_ui   # or: python app/chatbot_ui.py (if sys.path fix applied)
```

The UI will open at `http://127.0.0.1:7860`.  
You can now type customer‑support queries and see the model’s responses.

---

## Data Preparation

`data/prepare_data.py` performs the following:

1. Loads the dataset `bitext/Bitext-customer-support-llm-chatbot-training-dataset` from the Hugging Face Hub.
2. Formats each example into the chat‑template:
  ```
   <|system|>You are a helpful customer support agent.

   <|user|>{instruction}

   <|assistant|>{response}
  ```
3. Saves the result as `data/customer_support_chat.jsonl` (one JSON object per line).

You can inspect `data/sample_data.jsonl` for a tiny example.

---

## Training

The fine‑tuning script (`training/train.py`) uses:

- **QLoRA** (`bitsandbytes` 4‑bit NF4) for memory‑efficient loading.  
- **LoRA** (`peft`) with `r=16`, `lora_alpha=32`, target modules `q_proj, v_proj, k_proj, o_proj`, `lora_dropout=0.05`.  
- **SFTTrainer** from `trl` for supervised fine‑tuning.

All hyper‑parameters are configurable via `training/config.yaml`.  
Typical settings (as in the plan):


| Parameter                     | Value                                |
| ----------------------------- | ------------------------------------ |
| `model_name_or_path`          | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |
| `max_seq_length`              | `512`                                |
| `num_train_epochs`            | `3`                                  |
| `per_device_train_batch_size` | `2`                                  |
| `gradient_accumulation_steps` | `4`                                  |
| `learning_rate`               | `2e-4`                               |
| `optimizer`                   | `paged_adamw_32bit`                  |
| `fp16`                        | `true`                               |


After training, the adapter is saved to `training/merged_model/` (or the path set in `output_dir`).  
You can merge the adapter into the base model for faster inference by setting `adapter_path` in `inference/model_loader.py`.

---

## Inference & UI

- `inference/model_loader.py` loads the base model (4‑bit) and optionally merges a LoRA adapter.  
- `inference/generate.py` provides a simple `generate_response` function with streaming via `TextStreamer`.  
- `app/chatbot_ui.py` builds a Gradio `ChatInterface` that:
  - Accepts user messages.  
  - Constructs a prompt from conversation history and the system prompt.  
  - Calls the generation function with user‑adjustable temperature, top‑p, and max‑new‑tokens.  
  - Displays the assistant’s reply in real time (streaming).

The UI also contains a sidebar where you can later plug in an intent‑classification model to show the detected intent/category.

---

## Configuration

All tunable parameters live in `training/config.yaml`.  
Key sections:

```yaml
model_name_or_path: TinyLlama/TinyLlama-1.1B-Chat-v1.0
output_dir: ./merged_model
max_seq_length: 512
num_train_epochs: 3
per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 2e-4
fp16: true
logging_steps: 10
save_steps: 500
warmup_steps: 100
lr_scheduler_type: cosine
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
optimizer: paged_adamw_32bit
```

To experiment with a different base model, simply change `model_name_or_path` (e.g., `microsoft/phi-2` or `mistralai/Mistral-7B-Instruct-v0.1`) and adjust VRAM expectations accordingly.

---

## Dependencies


| Package          | Minimum Version            |
| ---------------- | -------------------------- |
| transformers     | 4.40.0                     |
| trl              | 0.8.6                      |
| peft             | 0.10.0                     |
| datasets         | 2.18.0                     |
| bitsandbytes     | 0.43.0                     |
| accelerate       | 0.28.0                     |
| gradio           | 4.26.0                     |
| torch            | 2.2.0                      |
| sentencepiece    | –                          |
| PyYAML           | –                          |
| python-multipart | 0.0.9 (required by Gradio) |


See `requirements.txt` for the exact pins.

---

## Troubleshooting


| Symptom                                                                              | Fix                                                                                                                                    |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'python_multipart'`                            | `pip install python-multipart==0.0.9` (or `pip install -r requirements.txt`)                                                           |
| `ModuleNotFoundError: No module named 'inference'`                                   | Run the UI as a module: `python -m app.chatbot_ui` **or** add the project root to `sys.path` in `app/chatbot_ui.py`.                   |
| `NameError: name 'threading' is not defined` / `NameError: name 'gr' is not defined` | Add the missing imports at the top of `app/chatbot_ui.py`: `import threading` and `import gradio as gr`.                               |
| CUDA out‑of‑memory                                                                   | Reduce `per_device_train_batch_size` or increase `gradient_accumulation_steps`; ensure `fp16:true` and 4‑bit quantization are enabled. |
| Slow first run                                                                       | The base model (~~2.2 GB for TinyLlama) is downloaded and cached in `~~/.cache/huggingface/hub`. Subsequent runs are fast.             |


If you encounter any other error, please open an issue with the full traceback.

---

## License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

## Citation

If you use this code or the fine‑tuned model in your work, please cite:

```bibtex
@misc{customer_support_bot_2026,
  author = {Your Name},
  title = {Customer Support Bot: QLoRA‑fine‑tuned LLM for Support Conversations},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  doi = {10.5281/zenodo.XXXXXXX}
}
```

---

Happy building! 🚀  
For questions or contributions, feel free to open an issue or submit a pull request.