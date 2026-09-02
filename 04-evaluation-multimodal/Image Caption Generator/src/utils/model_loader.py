import os
import torch
import torch.nn as nn
from typing import Any, Optional, Tuple

USE_HF_API = os.getenv("USE_HF_API", "0") == "1"
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_REPO = os.getenv("HF_API_REPO", "Salesforce/blip-image-captioning-base")

def get_model(device: str = "cpu"):
    """
    Returns a model-like object.
    If USE_HF_API is set, returns HFInferenceWrapper that talks to the Hugging Face Serverless Inference API.
    Otherwise returns a simple dummy model suitable for training (random weights).
    """
    if USE_HF_API:
        from .hf_inference import HFInferenceWrapper
        return HFInferenceWrapper(
            repo_id=HF_API_REPO,
            token=HF_API_TOKEN,
            device=device,
        )
    else:
        # Dummy model for training: we just need something that produces logits of shape (B, seq_len, vocab_size)
        # We'll mimic the interface expected by train_dummy.py: forward(images, input_ids, attention_mask) -> logits
        class DummyCaptionModel(nn.Module):
            def __init__(self, vocab_size=50257, max_len=30, dim=768):
                super().__init__()
                self.vocab_size = vocab_size
                self.max_len = max_len
                # a simple linear layer that maps image features to logits; we'll ignore actual image input
                self.dummy = nn.Linear(dim, vocab_size)
                # we also need to produce prefix-like outputs for generate (not used in training)
                self.prefix_len = 10
                self.prefix_dim = dim
                # For dummy generation, we'll use a fixed phrase
                from transformers import GPT2TokenizerFast
                self.tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.dummy_phrase = "a dummy caption"
                self.dummy_token_ids = torch.tensor(self.tokenizer.encode(self.dummy_phrase), dtype=torch.long)

            def forward(self, images, input_ids, attention_mask):
                """
                images: tensor or list (unused)
                input_ids: (B, seq_len)
                attention_mask: (B, seq_len)
                Returns logits of shape (B, seq_len, vocab_size)
                """
                batch_size = input_ids.shape[0]
                seq_len = input_ids.shape[1]
                # produce random logits
                logits = torch.randn(batch_size, seq_len, self.vocab_size, requires_grad=True)
                return logits.to(images.device if hasattr(images, 'device') else torch.device('cpu'))

            @torch.no_grad()
            def generate(self, images, max_length=30, num_beams=1, temperature=1.0, top_p=0.9, do_sample=True, **kwargs):
                """
                Dummy generation: returns fixed token ids for a dummy phrase.
                """
                batch_size = images.shape[0] if torch.is_tensor(images) else len(images)
                # Repeat the dummy token ids for each item in the batch
                # We'll return a list of tensors as expected by the captioning script.
                # The dummy_token_ids are 1D; we need to add batch dimension.
                generated = self.dummy_token_ids.unsqueeze(0).repeat(batch_size, 1)
                # Return as list of tensors (one per batch item) to match HFInferenceWrapper output format
                return [generated[i] for i in range(batch_size)]

        return DummyCaptionModel().to(device)