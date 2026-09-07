#!/usr/bin/env python
"""
Gradio Chat UI for the Customer Support Bot.
"""
import sys
from pathlib import Path
import threading
import gradio as gr

ROOT = Path(__file__).resolve().parents[1]   # …/Customer Support Bot
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inference.model_loader import load_model
from inference.generate import generate_response

model, tokenizer = None, None
lock = threading.Lock()

def load_model_once():
    global model, tokenizer
    if model is None:
        with lock:
            if model is None:
                model, tokenizer = load_model(adapter_path="./merged_model")
    return model, tokenizer

def respond(message, history, temperature, top_p, max_new_tokens):
    """
    Gradio chatbot callback.
    """
    model, tokenizer = load_model_once()
    # Build prompt from history
    prompt = "<|system|>You are a helpful customer support agent.\n\n"
    for user_msg, assistant_msg in history:
        prompt += f"<|user|>{user_msg}\n\n<|assistant|>{assistant_msg}\n\n"
    prompt += f"<|user|>{message}\n\n<|assistant|>"
    
    # Generate response
    response = ""
    def stream_token(token):
        nonlocal response
        response += token
    # We'll use generate_response which streams via print; instead capture via callback.
    # Simpler: call generate and return full response.
    # For simplicity, we generate without streaming here.
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output = model.generate(
        **inputs,
        max_new_tokens=int(max_new_tokens),
        temperature=float(temperature),
        top_p=float(top_p),
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    response_text = tokenizer.decode(output[0], skip_special_tokens=True)
    # Extract assistant part
    if "<|assistant|>" in response_text:
        response_text = response_text.split("<|assistant|>")[-1].strip()
    return response_text

def clear_chat():
    return None, []

with gr.Blocks() as demo:
    gr.Markdown("# Customer Support Bot")
    with gr.Row():
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(label="Conversation", height=500)
            with gr.Row():
                txt = gr.Textbox(show_label=False, placeholder="Type your message here...", lines=1)
                submit_btn = gr.Button("Send")
            with gr.Row():
                clear_btn = gr.Button("Clear Chat")
        with gr.Column(scale=1):
            gr.Markdown("## Settings")
            temperature = gr.Slider(minimum=0.1, maximum=2.0, value=0.7, step=0.1, label="Temperature")
            top_p = gr.Slider(minimum=0.1, maximum=1.0, value=0.9, step=0.05, label="Top-p")
            max_new_tokens = gr.Slider(minimum=50, maximum=512, value=256, step=10, label="Max New Tokens")
            gr.Markdown("## Intent Category (placeholder)")
            intent_box = gr.Textbox(label="Detected Intent", interactive=False)
    
    # Event handlers
    def user_input(message, history):
        return "", history + [[message, None]]
    
    def bot_response(history, temperature, top_p, max_new_tokens):
        if not history:
            return history
        user_msg = history[-1][0]
        bot_msg = respond(user_msg, history[:-1], temperature, top_p, max_new_tokens)
        history[-1][1] = bot_msg
        return history
    
    txt.submit(user_input, [txt, chatbot], [txt, chatbot]).then(
        bot_response, [chatbot, temperature, top_p, max_new_tokens], chatbot
    )
    submit_btn.click(user_input, [txt, chatbot], [txt, chatbot]).then(
        bot_response, [chatbot, temperature, top_p, max_new_tokens], chatbot
    )
    clear_btn.click(clear_chat, None, [chatbot, intent_box], queue=False)

if __name__ == "__main__":
    demo.queue()
    demo.launch()