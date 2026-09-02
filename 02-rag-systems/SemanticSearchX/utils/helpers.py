import os
from pathlib import Path

def ensure_dir(directory: str):
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_device():
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"