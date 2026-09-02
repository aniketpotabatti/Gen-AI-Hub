# src/api/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import torch
from src.utils.model_loader import get_model
from src.utils.image_utils import load_and_preprocess_image
from transformers import GPT2TokenizerFast
import io
from PIL import Image

app = FastAPI(title="Image Caption Generator API")

# Load model and tokenizer globally (in practice, use lifespan events)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = get_model(device=device)
# For demo, we assume model is already trained; we'll load dummy weights if needed.
try:
    # Attempt to load a checkpoint if exists
    checkpoint_path = "checkpoints/model_epoch_1.pt"  # adjust as needed
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
except Exception as e:
    print(f"No checkpoint loaded: {e}")
model.eval()

tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
tokenizer.pad_token = tokenizer.eos_token

class CaptionResponse(BaseModel):
    caption: str

def generate_caption_from_tensor(image_tensor: torch.Tensor, max_length: int = 30, temperature: float = 1.0) -> str:
    # If model has encode_image (real BLIP model), use the original logic
    if hasattr(model, 'encode_image'):
        model.eval()
        with torch.no_grad():
            # Encode image
            prefix = model.encode_image(image_tensor.to(device))  # (1, prefix_len, dim)
            # Start with BOS token (GPT-2 uses 50256 as eos_token_id, bos_token_id is same as eos?)
            # GPT-2 tokenizer doesn't have a dedicated BOS; we use eos_token_id as BOS for simplicity.
            generated = torch.full((1, 1), tokenizer.eos_token_id, dtype=torch.long, device=device)
            for _ in range(max_length):
                # Get embeddings for generated tokens so far
                token_embeds = model.decoder.transformer.wte(generated)  # (1, seq_len, dim)
                # Concatenate prefix and token embeddings
                inputs_embeds = torch.cat([prefix, token_embeds], dim=1)  # (1, prefix_len+seq_len, dim)
                # Forward through decoder to get logits for next token
                outputs = model.decoder.transformer(inputs_embeds=inputs_embeds)
                logits = model.decoder.lm_head(outputs.last_hidden_state)  # (1, seq_len, vocab_size)
                next_token_logits = logits[:, -1, :] / temperature
                # Sample next token
                probs = torch.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)  # (1, 1)
                # Append generated token
                generated = torch.cat([generated, next_token], dim=1)
                # Stop if EOS token generated
                if next_token.item() == tokenizer.eos_token_id:
                    break
            # Remove the initial BOS token
            generated_ids = generated[0, 1:].tolist()
            caption = tokenizer.decode(generated_ids, skip_special_tokens=True)
            return caption
    else:
        # Dummy model fallback: just return a fixed caption
        return "a dummy caption describing the image."

@app.post("/caption", response_model=CaptionResponse)
async def caption_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    image_bytes = await file.read()
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")
    image_tensor = load_and_preprocess_image(image)  # returns (1, C, H, W)
    caption = generate_caption_from_tensor(image_tensor)
    return CaptionResponse(caption=caption)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)