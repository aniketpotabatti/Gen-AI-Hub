import torch
from src.models.blip_encoder import BLIPEncoder
from src.models.gpt2_decoder import GPT2Decoder
from src.models.image_caption_model import ImageCaptionModel

def test_encoder():
    print("Testing BLIPEncoder...")
    encoder = BLIPEncoder()
    dummy_image = torch.randn(1, 3, 224, 224)  # batch size 1, 3 channels, 224x224
    features = encoder.encode_image(dummy_image)
    print(f"Encoded features shape: {features.shape}")

def test_decoder():
    print("Testing GPT2Decoder...")
    decoder = GPT2Decoder()
    dummy_prefix = torch.randn(1, 10, 768)  # batch size 1, seq_len 10, encoder dim 768
    # For simplicity, just check forward pass
    logits = decoder.forward(dummy_prefix, torch.randint(0, 50257, (1, 10)))  # dummy target ids
    print(f"Logits shape: {logits.shape}")

def test_full_model():
    print("Testing ImageCaptionModel...")
    model = ImageCaptionModel()
    dummy_image = torch.randn(1, 3, 224, 224)
    dummy_caption = torch.randint(0, 50257, (1, 10))  # batch size 1, seq_len 10
    loss = model(dummy_image, dummy_caption)
    print(f"Loss: {loss.item()}")

if __name__ == "__main__":
    test_encoder()
    test_decoder()
    test_full_model()
    print("All tests passed!")