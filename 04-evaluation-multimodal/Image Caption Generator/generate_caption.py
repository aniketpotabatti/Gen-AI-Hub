import torch
from src.utils.model_loader import get_model
from src.utils.image_utils import load_and_preprocess_image
from transformers import GPT2TokenizerFast
from PIL import Image
import argparse
import os
from typing import List


def _caption_from_hf_wrapper(model, image_tensor: torch.Tensor, device: torch.device) -> str:
    """Generate caption using HFInferenceWrapper."""
    with torch.no_grad():
        token_ids_list: List[torch.Tensor] = model.generate(pixel_values=image_tensor.to(device))
        if not token_ids_list:
            return ""
        token_ids = token_ids_list[0]  # LongTensor
        # Token IDs are Unicode code points of the caption characters.
        return "".join(chr(int(_)) for _ in token_ids.tolist())


def _caption_from_local_model(
    model, image_tensor: torch.Tensor, tokenizer, device: torch.device, max_length: int, temperature: float
) -> str:
    """Generate caption using a local BLIP‑Encoder + GPT‑2 decoder model."""
    model.eval()
    with torch.no_grad():
        prefix = model.encode_image(image_tensor.to(device))  # (1, prefix_len, dim)

        generated = torch.full(
            (1, 1), tokenizer.eos_token_id, dtype=torch.long, device=device
        )  # start with BOS (using EOS token)

        for _ in range(max_length):
            token_embeds = model.decoder.transformer.wte(generated)  # (1, seq_len, dim)
            inputs_embeds = torch.cat([prefix, token_embeds], dim=1)  # (1, prefix_len+seq_len, dim)

            outputs = model.decoder.transformer(inputs_embeds=inputs_embeds)
            logits = model.decoder.lm_head(outputs.last_hidden_state)  # (1, seq_len, vocab_size)
            next_token_logits = logits[:, -1, :] / temperature

            probs = torch.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)  # (1, 1)

            generated = torch.cat([generated, next_token], dim=1)

            if next_token.item() == tokenizer.eos_token_id:
                break

        generated_ids = generated[0, 1:].tolist()
        return tokenizer.decode(generated_ids, skip_special_tokens=True)


def generate_caption(
    model,
    image_tensor: torch.Tensor,
    tokenizer,
    device: torch.device,
    max_length: int = 30,
    temperature: float = 1.0,
) -> str:
    """Unified caption generation dispatching to HF wrapper or local model."""
    # HFInferenceWrapper has a generate method; we detect it by type.
    from src.utils.hf_inference import HFInferenceWrapper

    if isinstance(model, HFInferenceWrapper):
        return _caption_from_hf_wrapper(model, image_tensor, device)

    # Fallback to local model (requires encode_image attribute)
    if hasattr(model, "encode_image"):
        return _caption_from_local_model(
            model, image_tensor, tokenizer, device, max_length, temperature
        )

    # Dummy model fallback
    return "a dummy caption describing the image."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate caption for an image using trained model"
    )
    parser.add_argument("--image_path", type=str, required=True, help="Path to input image")
    parser.add_argument(
        "--checkpoint", type=str, required=True, help="Path to model checkpoint"
    )
    parser.add_argument(
        "--max_length", type=int, default=30, help="Maximum caption length"
    )
    parser.add_argument(
        "--temperature", type=float, default=1.0, help="Sampling temperature"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to use",
    )
    args = parser.parse_args()

    device = torch.device(args.device)

    # Load tokenizer (GPT-2)
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token  # set pad token

    # Load model via model_loader
    model = get_model(device=device)
    # If not using HF API wrapper, load checkpoint weights
    from src.utils.hf_inference import HFInferenceWrapper

    if not isinstance(model, HFInferenceWrapper):
        checkpoint = torch.load(args.checkpoint, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
    if hasattr(model, "eval"):
        model.eval()

    # Load and preprocess image
    if not os.path.isfile(args.image_path):
        raise FileNotFoundError(f"Image not found: {args.image_path}")
    image_tensor = load_and_preprocess_image(args.image_path)  # (1, C, H, W)

    # Generate caption
    caption = generate_caption(
        model, image_tensor, tokenizer, device, max_length=args.max_length, temperature=args.temperature
    )

    print(f"Generated caption: {caption}")

    # Optionally display image with caption
    try:
        import matplotlib.pyplot as plt

        img = Image.open(args.image_path).convert("RGB")
        plt.imshow(img)
        plt.axis("off")
        plt.title(caption, fontsize=12)
        plt.show()
    except ImportError:
        pass  # matplotlib is optional


if __name__ == "__main__":
    main()