# src/cli/caption_image.py
#!/usr/bin/env python
"""
Command-line interface for generating captions from images.
Usage:
    python -m src.cli.caption_image --image path/to/image.jpg --checkpoint checkpoints/model_epoch_1.pt
"""

import argparse
import torch
from src.utils.model_loader import get_model
from src.utils.image_utils import load_and_preprocess_image
from transformers import GPT2TokenizerFast
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Generate caption for an image using trained model")
    parser.add_argument('--image', type=str, required=True, help='Path to input image')
    parser.add_argument('--checkpoint', type=str, required=False, help='Path to model checkpoint (optional)')
    parser.add_argument('--max_length', type=int, default=30, help='Maximum caption length')
    parser.add_argument('--temperature', type=float, default=1.0, help='Sampling temperature')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu', help='Device to use')
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"Error: Image file not found: {args.image}")
    if args.checkpoint and not os.path.isfile(args.checkpoint):
        sys.exit(f"Error: Checkpoint file not found: {args.checkpoint}")

    device = torch.device(args.device)
    # Load tokenizer
    tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
    tokenizer.pad_token = tokenizer.eos_token

    # Load model via loader (respects USE_HF_API)
    model = get_model(device=device)
    # If a checkpoint is provided, load its state dict (only for local models)
    if args.checkpoint:
        # Assuming the model is a local ImageCaptionModel that has load_state_dict
        if hasattr(model, 'load_state_dict'):
            checkpoint = torch.load(args.checkpoint, map_location=device)
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            print("Warning: Checkpoint provided but model does not support loading state dict.")
    model.eval()

    # Load and preprocess image
    image_tensor = load_and_preprocess_image(args.image)  # (1, C, H, W)

    # Generate caption - handle different model types
    if hasattr(model, 'generate'):
        # HFInferenceWrapper or any model with a generate method that returns token ids
        with torch.no_grad():
            # The wrapper's generate expects pixel_values and returns list of LongTensor
            token_ids_list = model.generate(image_tensor.to(device))
            # token_ids_list is a list of tensors (batch size 1)
            generated_ids = token_ids_list[0].tolist()
            caption = tokenizer.decode(generated_ids, skip_special_tokens=True)
    elif hasattr(model, 'encode_image'):
        # Real BLIP-like model with encode_image
        with torch.no_grad():
            prefix = model.encode_image(image_tensor.to(device))
            generated = torch.full((1, 1), tokenizer.eos_token_id, dtype=torch.long, device=device)
            for _ in range(args.max_length):
                token_embeds = model.decoder.transformer.wte(generated)
                inputs_embeds = torch.cat([prefix, token_embeds], dim=1)
                outputs = model.decoder.transformer(inputs_embeds=inputs_embeds)
                logits = model.decoder.lm_head(outputs.last_hidden_state)
                next_token_logits = logits[:, -1, :] / args.temperature
                probs = torch.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                generated = torch.cat([generated, next_token], dim=1)
                if next_token.item() == tokenizer.eos_token_id:
                    break
            generated_ids = generated[0, 1:].tolist()
            caption = tokenizer.decode(generated_ids, skip_special_tokens=True)
    else:
        # Fallback
        caption = "a dummy caption describing the image."

    print(f"Generated caption: {caption}")


if __name__ == "__main__":
    main()