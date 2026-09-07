#!/usr/bin/env python
"""
Load base model and LoRA adapter for inference.
"""
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

def load_model(adapter_path=None, base_model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
    """
    Load the base model and optionally merge with LoRA adapter.
    If adapter_path is provided, loads the adapter and merges it.
    """
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model in 4-bit for efficient inference
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    if adapter_path and os.path.exists(adapter_path):
        print(f"Loading LoRA adapter from {adapter_path}")
        model = PeftModel.from_pretrained(base_model, adapter_path)
        model = model.merge_and_unload()
        print("Adapter merged.")
    else:
        model = base_model
        print("No adapter loaded; using base model only.")
    
    return model, tokenizer

if __name__ == "__main__":
    # Example usage
    model, tokenizer = load_model(adapter_path="./merged_model")
    print("Model and tokenizer ready.")