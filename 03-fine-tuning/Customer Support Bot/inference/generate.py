#!/usr/bin/env python
"""
Text generation pipeline with streaming support.
"""
import torch
from transformers import TextStreamer

def generate_response(model, tokenizer, prompt, max_new_tokens=256, temperature=0.7, top_p=0.9):
    """
    Generate a response from the model given a prompt.
    Yields tokens via TextStreamer for streaming.
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    
    # Generate
    _ = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        do_sample=True,
        streamer=streamer,
        pad_token_id=tokenizer.eos_token_id
    )

if __name__ == "__main__":
    from inference.model_loader import load_model
    model, tokenizer = load_model()
    test_prompt = "<|system|>You are a helpful customer support agent.\n\n<|user|>How do I track my order?\n\n<|assistant|>"
    print("Generating response:")
    generate_response(model, tokenizer, test_prompt)