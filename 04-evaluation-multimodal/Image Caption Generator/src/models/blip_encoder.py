"""
BLIP Image Encoder for Image Caption Generator
"""

import torch
from transformers import BlipProcessor, BlipModel
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

class BLIPEncoder:
    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base", device: Optional[str] = None):
        """
        Initialize BLIP encoder.
        
        Args:
            model_name: Hugging Face model name/path
            device: Device to run model on ('cuda', 'cpu', etc.)
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading BLIP model {model_name} on {self.device}")
        
        self.processor = BlipProcessor.from_pretrained(model_name)
        self.model = BlipModel.from_pretrained(model_name).to(self.device)
        self.model.eval()
        
        # Freeze parameters (we only use as encoder)
        for param in self.model.parameters():
            param.requires_grad = False
            
        logger.info("BLIP encoder loaded successfully")
    
    @torch.no_grad()
    def encode_image(self, image) -> torch.Tensor:
        """
        Encode an image to get visual features.
        
        Args:
            image: PIL Image or tensor of shape (C, H, W) or batch of images
            
        Returns:
            Visual features tensor of shape (batch_size, sequence_length, hidden_dim)
        """
        # Process image
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        # Get vision outputs
        vision_outputs = self.model.vision_model(pixel_values=inputs.pixel_values)
        # We want the last hidden state
        image_embeds = vision_outputs.last_hidden_state  # (batch_size, seq_len, hidden_size)
        
        return image_embeds
    
    @torch.no_grad()
    def extract_features(self, image) -> torch.Tensor:
        """
        Extract pooled features (CLS token equivalent).
        
        Args:
            image: PIL Image or tensor
            
        Returns:
            Pooled features tensor of shape (batch_size, hidden_dim)
        """
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        vision_outputs = self.model.vision_model(pixel_values=inputs.pixel_values)
        # Use pooled output (from the model's pooler)
        pooled_output = vision_outputs.pooler_output  # (batch_size, hidden_size)
        return pooled_output

if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.INFO)
    encoder = BLIPEncoder()
    print("BLIP Encoder initialized successfully")