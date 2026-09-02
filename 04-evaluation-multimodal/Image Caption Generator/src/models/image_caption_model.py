"""
Image Caption Generator model combining BLIP encoder and GPT-2 decoder
"""

import torch
import torch.nn as nn
from typing import Optional, Tuple
import logging

from .blip_encoder import BLIPEncoder
from .gpt2_decoder import GPT2Decoder

logger = logging.getLogger(__name__)

class ImageCaptionModel(nn.Module):
    def __init__(self, 
                 blip_model_name: str = "Salesforce/blip-image-captioning-base",
                 gpt2_model_name: str = "gpt2",
                 prefix_length: int = 10,
                 device: Optional[str] = None):
        super().__init__()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Initializing ImageCaptionModel")
        
        self.encoder = BLIPEncoder(model_name=blip_model_name, device=self.device)
        self.decoder = GPT2Decoder(model_name=gpt2_model_name, 
                                   encoder_hidden_size=self.encoder.model.config.hidden_size,
                                   prefix_length=prefix_length,
                                   device=self.device)
        
        logger.info("ImageCaptionModel initialized")
    
    def forward(self, images, input_ids, attention_mask):
        """
        Forward pass for training.
        
        Args:
            images: batch of images (PIL list or tensor)
            input_ids: target caption tokens
            attention_mask: attention mask for target caption
            
        Returns:
            logits from decoder
        """
        # Get encoder outputs
        encoder_outputs = self.encoder.encode_image(images)  # (batch_size, seq_len, hidden)
        # Get decoder logits
        logits = self.decoder(encoder_outputs, input_ids, attention_mask)
        return logits
    
    @torch.no_grad()
    def generate(self, images, 
                 max_length: int = 50,
                 num_beams: int = 4,
                 temperature: float = 1.0,
                 top_p: float = 0.9,
                 do_sample: bool = True,
                 **kwargs):
        """
        Generate captions for images.
        """
        encoder_outputs = self.encoder.encode_image(images)
        generated_ids = self.decoder.generate(encoder_outputs,
                                              max_length=max_length,
                                              num_beams=num_beams,
                                              temperature=temperature,
                                              top_p=top_p,
                                              do_sample=do_sample,
                                              **kwargs)
        # Decode token ids to text
        captions = self.decoder.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
        return captions

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model = ImageCaptionModel()
    print("ImageCaptionModel initialized successfully")