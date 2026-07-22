"""
agent.py — Core agent logic for VidLens AI.

Orchestrates:
1. DuckDuckGo web search for real-time context
2. Gemini 2.5 Flash / Pro for video + text understanding
3. Streaming combined response
"""

from __future__ import annotations

from typing import Iterator

from duckduckgo_search import DDGS
from google import genai
from google.genai import types

from utils import format_search_results, upload_video_to_gemini

SYSTEM_PROMPT = """You are an advanced multimodal AI research assistant with two capabilities:

1. **Video Understanding** — Analyse scenes, objects, on-screen text, actions, and emotions.
2. **Web-Augmented Reasoning** — Combine visual findings with live web search results.

Guidelines:
- Ground every answer in what you directly observe in the video.
- When web results are provided, cite them naturally and integrate them with your visual analysis.
- Be structured (bullet points / numbered lists) and concise but thorough.
- If the video doesn't cover the question and the web has no relevant context, say so clearly.
"""


class VideoSearchAgent:
    """Combines Gemini 2.5 video understanding with DuckDuckGo web search."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self._video_file: object | None = None  # cached Gemini File object

    # ── Video ──────────────────────────────────────────────────────────────

    @property
    def has_video(self) -> bool:
        return self._video_file is not None

    def upload_video(self, video_bytes: bytes, file_name: str) -> None:
        """Upload *video_bytes* and cache the resulting Gemini File object."""
        self._video_file = upload_video_to_gemini(self.client, video_bytes, file_name)

    # ── Web search ─────────────────────────────────────────────────────────

    def _web_search(self, query: str, max_results: int) -> list[dict]:
        """Return DuckDuckGo text results; on error return a single error entry."""
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as exc:  # noqa: BLE001
            return [{"title": "Search error", "href": "", "body": str(exc)}]

    # ── Inference ──────────────────────────────────────────────────────────

    def run(
        self,
        user_query: str,
        chat_history: list[dict],
        enable_web_search: bool = True,
        search_results_count: int = 5,
    ) -> Iterator[str]:
        """
        Run the agent and yield streamed response text chunks.

        Args:
            user_query:          Current user question.
            chat_history:        Full conversation so far (including current user turn).
            enable_web_search:   Whether to augment the prompt with web results.
            search_results_count: Number of DuckDuckGo results to fetch.
        """
        # 1. Build prompt parts
        prompt_parts: list = []

        if self.has_video:
            prompt_parts.append(self._video_file)

        if enable_web_search:
            web_context = format_search_results(
                self._web_search(user_query, max_results=search_results_count)
            )
            if web_context:
                prompt_parts.append(
                    f"Up-to-date web search results for context:\n\n{web_context}\n\n---\n\n"
                    f"Use both the video and web context to answer the question below.\n"
                )

        prompt_parts.append(f"User Question: {user_query}")

        # 2. Convert prior turns to Gemini Content history (exclude current user turn)
        history = [
            types.Content(
                role="user" if t["role"] == "user" else "model",
                parts=[types.Part(text=t["content"])],
            )
            for t in chat_history[:-1]
        ]

        # 3. Stream response
        chat = self.client.chats.create(
            model=self.model_id,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.4,
                max_output_tokens=8192,
            ),
            history=history,
        )

        for chunk in chat.send_message_stream(prompt_parts):
            if chunk.text:
                yield chunk.text
