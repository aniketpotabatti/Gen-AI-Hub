"""
GPT-2 Decoder with optional style conditioning for Image Caption Generator
"""

import torch
import torch.nn as nn
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import logging

logger = logging.getLogger(__name__)

class GPT2Decoder(nn.Module):
    def __init__(self, model_name="gpt2", encoder_hidden_size=768, prefix_length=10, device=None):
        super().__init__()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.prefix_length = prefix_length
        self.encoder_hidden_size = encoder_hidden_size
        
        logger.info(f"Loading GPT-2 model {model_name} on {self.device}")
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.transformer = GPT2LMHeadModel.from_pretrained(model_name)
        self.transformer.to(self.device)
        
        self.proj = nn.Linear(encoder_hidden_size, self.transformer.config.n_embd * prefix_length)
        self.layer_norm = nn.LayerNorm(self.transformer.config.n_embd)
        
        for param in self.transformer.parameters():
            param.requires_grad = False
        
        logger.info("GPT-2 decoder initialized")
    
    def forward(self, encoder_outputs, input_ids, attention_mask):
        batch_size = encoder_outputs.size(0)
        encoder_pooled = encoder_outputs.mean(dim=1)
        prefix_embeddings = self.proj(encoder_pooled)
        prefix_embeddings = prefix_embeddings.view(batch_size, self.prefix_length, self.transformer.config.n_embd)
        prefix_embeddings = self.layer_norm(prefix_embeddings)
        
        token_embeddings = self.transformer.transformer.wte(input_ids)
        embeddings = torch.cat([prefix_embeddings, token_embeddings], dim=1)
        
        prefix_attention = torch.ones(batch_size, self.prefix_length, device=self.device)
        attention_mask = torch.cat([prefix_attention, attention_mask], dim=1)
        
        outputs = self.transformer.transformer(inputs_embeds=embeddings, attention_mask=attention_mask)
        logits = self.transformer.lm_head(outputs.last_hidden_state)
        return logits
    
    @torch.no_grad()
    def generate(self, encoder_outputs, max_length=50, num_beams=4, temperature=1.0, top_p=0.9, do_sample=True, **kwargs):
        batch_size = encoder_outputs.size(0)
        encoder_pooled = encoder_outputs.mean(dim=1)
        prefix_embeddings = self.proj(encoder_pooled)
        prefix_embeddings = prefix_embeddings.view(batch_size, self.prefix_length, self.transformer.config.n_embd)
        prefix_embeddings = self.layer_norm(prefix_embeddings)
        
        prefix_attention = torch.ones(batch_size, self.prefix_length, device=self.device)
        
        generated_ids = self.transformer.generate(
            inputs_embeds=prefix_embeddings,
            attention_mask=prefix_attention,
            max_length=max_length + self.prefix_length,
            num_beams=num_beams,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            **kwargs
        )
        return generated_ids[:, self.prefix_length:]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    decoder = GPT2Decoder()
    print("GPT-2 Decoder initialized successfully")