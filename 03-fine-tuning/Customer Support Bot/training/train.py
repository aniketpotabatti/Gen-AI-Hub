#!/usr/bin/env python
"""
Fine-tuning script using QLoRA and SFTTrainer.
"""
import os
import yaml
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

def main():
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    model_name = config["model_name_or_path"]
    output_dir = config["output_dir"]
    max_seq_length = config["max_seq_length"]
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    
    # Base model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    # LoRA config
    lora_config = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        target_modules=config["target_modules"],
        lora_dropout=config["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load dataset (assuming prepared JSONL)
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "customer_support_chat.jsonl"))
    dataset = load_dataset("json", data_files=data_path, split="train")
    
    # Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
        args=transformers.TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=config["per_device_train_batch_size"],
            gradient_accumulation_steps=config["gradient_accumulation_steps"],
            num_train_epochs=config["num_train_epochs"],
            learning_rate=config["learning_rate"],
            fp16=config.get("fp16", False),
            logging_steps=config["logging_steps"],
            save_steps=config["save_steps"],
            warmup_steps=config["warmup_steps"],
            lr_scheduler_type=config["lr_scheduler_type"],
            optim=config["optimizer"],
            report_to="none"
        ),
    )
    
    trainer.train()
    
    # Save adapter
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model saved to {output_dir}")

if __name__ == "__main__":
    main()