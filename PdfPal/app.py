"""
Author: @aniketpotabatti
Project: PdfPal
Created: 2024-01-15
"""

import streamlit as st
from llm import generate_answer
import os
from typing import List


def main():
    st.set_page_config(page_title="PdfPal", page_icon="📃")
    
    # State Initialization - Must be done first
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Custom CSS for chat interface
    st.markdown("""
    <style>
    .user-message { 
        display: flex; 
        justify-content: flex-end; 
        margin-bottom: 10px; 
    }
    .assistant-message { 
        display:flex ;
        justify-content: flex-start; 
        margin-bottom: 10px; 
    }
    .user-message div {
        background-color: rgba(255, 255, 255, 0.2);
        padding: 15px; 
        border-radius: 10px; 
        max-width: 100%;
        word-wrap: break-word; 
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    .assistant-message div {
        padding: 15px; 
        border-radius: 10px; 
        max-width: 100%;
        word-wrap: break-word; 
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    /* Responsive design */
    @media (max-width: 768px) {
        .user-message div, .assistant-message div {
            max-width: 85%;
            padding: 12px;
            font-size: 0.9rem;
        }
        .stSidebar {
            width: 100% !important;
        }
    }
    @media (max-width: 480px) {
        .user-message div, .assistant-message div {
            max-width: 95%;
            padding: 10px;
            font-size: 0.85rem;
        }
        h1 {
            font-size: 2rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar: Inputs & Actions
    with st.sidebar:
        st.title("Menu")
        uploaded_pdfs = st.file_uploader("Upload PDFs", accept_multiple_files=True, type="pdf")
        url_text = st.text_area("Enter URLs (one per line)")

        if st.button("Process Documents"):
            urls = [u.strip() for u in url_text.split('\n') if u.strip()]
            if uploaded_pdfs or urls:
                with st.spinner("Processing content..."):
                    from utils import process_content
                    process_content(uploaded_pdfs, urls)
                    st.success("Done!")
            else:
                st.warning("Add PDFs or URLs first.")

        if st.button("Clear Data"):
            st.session_state.chat_history = []
            if os.path.exists("faiss_index"):
                import shutil
                shutil.rmtree("faiss_index")
            st.rerun()

    # Main Content: Header & Chat
    st.markdown("""
    <div style="position: fixed; top: 0; left: 0; right: 0; z-index: 100; background-color: #1A1A1A; height: 60px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); display: flex; align-items: center; justify-content: center;">
        <h1 style="font-size: 2.5rem; font-weight: 700; margin: 0; line-height: 1; color: white;">PdfPal</h1>
        <p style="font-style: italic; font-size: 0.9rem; color: #0DB2BF; position: absolute; bottom: -2px; right: 630px; margin: 0;">powered by groq</p>
    </div>
    """, unsafe_allow_html=True)

    # Add spacing for fixed header
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    
    # Render History
    for role, msg in st.session_state.chat_history:
        css_class = "user-message" if role == "user" else "assistant-message"
        st.markdown(f'<div class="{css_class}"><div>{msg}</div></div>', unsafe_allow_html=True)

    # Chat Input
    if user_input := st.chat_input("Ask about your documents..."):
        # Show User Message
        st.session_state.chat_history.append(("user", user_input))
        st.markdown(f'<div class="user-message"><div>{user_input}</div></div>', unsafe_allow_html=True)

        # Generate & Show Answer
        response = generate_answer(user_input)
        if response:
            st.session_state.chat_history.append(("assistant", response))
            st.markdown(f'<div class="assistant-message"><div>{response}</div></div>', unsafe_allow_html=True)
            st.rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.stop()

