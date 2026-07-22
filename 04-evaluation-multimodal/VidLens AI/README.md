# 🎬VidLens AI

A Streamlit application that combines video analysis using Google Gemini 2.5 with live web search powered by DuckDuckGo. This agent enables users to upload videos, ask questions, and receive detailed answers grounded in both visual content and up-to-date web information.

**Created**: May 2025

---

## Features

- Video understanding powered by Gemini 2.5 Flash and Pro models.
- Support for multiple video formats including MP4, MOV, AVI, MKV, and WebM.
- Real-time web research integration via DuckDuckGo to provide enriched answers.
- Interactive multi-turn chat interface with history tracking.
- Streaming responses for real-time output.

---

## Repository Structure

```
VidLens AI/
├── app.py           # Main Streamlit web application interface
├── agent.py         # Core agent orchestration logic combining Gemini and search
├── utils.py         # Helper functions for video upload and search result formatting
├── requirements.txt # Python package dependencies
└── Note.txt         # Project description reference
```

---

## Prerequisites

- Python 3.10+ installed on your system.
- A Google AI Studio API key (obtainable from https://aistudio.google.com/).

---

## Installation

1. Clone or download this repository.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Application

1. Start the Streamlit application:

```bash
streamlit run app.py
```

2. Open the application in your browser (typically at http://localhost:8501).
3. Enter your Google AI Studio API key in the sidebar and click "Apply Settings".
4. Upload a video file, click "Upload & Process Video", and begin chatting.
