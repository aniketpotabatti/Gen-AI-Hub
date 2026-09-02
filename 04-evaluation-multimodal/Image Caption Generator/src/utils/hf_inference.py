import os
import requests
from typing import Optional, List
import torch
from PIL import Image
from io import BytesIO

API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{repo_id}"

class HFInferenceWrapper:
    """
    Thin wrapper that mimics enough of the 🤗 Transformers API
    to be used by the existing training / inference code.
    For training we only need a forward() that returns dummy logits
    (so the optimizer can step). For inference we call the
    `generate` endpoint which returns generated token IDs.
    """
    def __init__(self, repo_id: str, token: Optional[str] = None, device: str = "cpu"):
        self.repo_id = repo_id
        self.token = token
        self.device = device
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.api_url = API_URL_TEMPLATE.format(repo_id=repo_id)

    # ------------------------------------------------------------------
    # Dummy forward – the training loop only needs something that
    # returns a tensor with grads so loss.backward() works.
    # We'll return a zero tensor with the same shape as the
    # model's expected logits (batch_size x vocab_size).
    # ------------------------------------------------------------------
    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """
        pixel_values: Not used in dummy forward, but kept for compatibility.
        Returns a tensor of shape (batch_size, vocab_size) with requires_grad=True.
        """
        # We expect pixel_values to be a tensor; we can infer batch size from first dim if provided.
        if torch.is_tensor(pixel_values):
            batch_size = pixel_values.shape[0]
        else:
            # If pixel_values is a list or other, assume batch size 1
            batch_size = 1
        vocab_size = 30522  # BLIP vocab size (approx)
        logits = torch.zeros(batch_size, vocab_size, requires_grad=True)
        return logits.to(self.device)

    # ------------------------------------------------------------------
    # Generation – calls the HF Serverless Inference API.
    # The API expects a JSON with "inputs": <base64‑image> or raw bytes.
    # We'll send the image as PNG bytes and ask for textual output.
    # ------------------------------------------------------------------
    def generate(self, pixel_values: torch.Tensor, **generate_kwargs):
        """
        pixel_values: torch.Tensor of shape (B, 3, H, W) – we only support B=1 for simplicity.
        Returns: list of token ID tensors (as the original code expects).
        """
        if pixel_values.shape[0] != 1:
            raise ValueError("HFInferenceWrapper.generate currently supports batch size 1")

        # Convert tensor to PNG bytes
        img_tensor = pixel_values.squeeze(0)  # (3, H, W)
        img_tensor = img_tensor.permute(1, 2, 0).cpu().numpy()  # (H, W, 3)
        img_tensor = (img_tensor * 255).clip(0, 255).astype("uint8")
        img = Image.fromarray(img_tensor)
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # HF Inference API for image-to-text: use the "inputs" field with raw bytes.
        response = requests.post(
            self.api_url,
            headers=self.headers,
            data=img_bytes,
            timeout=60,
        )
        response.raise_for_status()
        # The API returns JSON like [{"generated_text": "a caption"}]
        json_out = response.json()
        caption = json_out[0]["generated_text"] if isinstance(json_out, list) else json_out.get("generated_text", "")

        # Turn caption into dummy token IDs (we just map each char to its ordinal)
        # The rest of the code expects a list of LongTensor(s) – we'll return one.
        token_ids = [torch.tensor([ord(c) for c in caption], dtype=torch.long)]
        return token_ids