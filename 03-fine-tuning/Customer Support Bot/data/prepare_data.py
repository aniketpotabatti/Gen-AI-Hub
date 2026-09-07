#!/usr/bin/env python
"""
Data preparation script for the Customer Support Bot project.
Downloads the Bitext dataset from Hugging Face Hub and converts it to chat‑template format.
"""

import os
from datasets import load_dataset

def main():
    # Dataset name on HF Hub
    dataset_name = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
    
    # Load dataset
    print(f"Loading dataset {dataset_name}...")
    dataset = load_dataset(dataset_name, split="train")
    
    # Define chat template
    def format_example(example):
        return {
            "text": f"<|system|>You are a helpful customer support agent.\n\n<|user|>{example['instruction']}\n\n<|assistant|>{example['response']}"
        }
    
    formatted = dataset.map(format_example, remove_columns=dataset.column_names)
    
    # Save as JSONL
    output_dir = os.path.join(os.path.dirname(__file__))
    output_path = os.path.join(output_dir, "customer_support_chat.jsonl")
    formatted.to_json(output_path, lines=True)
    print(f"Saved formatted dataset to {output_path}")

if __name__ == "__main__":
    main()