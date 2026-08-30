"""
AI Data Analyst - the brain of the application.
Routes questions to the right strategy, generates answers, and suggests charts.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
from google import genai
from google.genai import types

from src.engine.vector_store import VectorStore
from src.utils.config import settings

_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "getattr": getattr,
    "hasattr": hasattr,
    "int": int,
    "isinstance": isinstance,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "pow": pow,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot be reached or returns a transport failure."""


def parse_model_json(raw: str) -> dict | None:
    """Best-effort parse of a model response that should contain a JSON object."""
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    candidates = [cleaned]
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def safe_execute(code: str, df: pd.DataFrame) -> dict:
    """Execute AI-generated pandas code with a restricted builtin set."""
    try:
        local_vars = {"df": df.copy(), "pd": pd, "np": np}
        exec(code, {"__builtins__": _SAFE_BUILTINS}, local_vars)
        return {"result": local_vars.get("result"), "error": None}
    except Exception as exc:
        return {"result": None, "error": f"{type(exc).__name__}: {exc}"}


def format_result(result) -> str:
    """Format execution result for display."""
    if result is None:
        return "No result returned."
    if isinstance(result, pd.DataFrame):
        table = result.head(20) if len(result) > 20 else result
        rendered = _to_table(table, index=False)
        if len(result) > 20:
            return f"{rendered}\n\n*...showing first 20 of {len(result)} rows*"
        return rendered
    if isinstance(result, pd.Series):
        return _to_table(result, index=True)
    return str(result)


def _to_table(obj: pd.DataFrame | pd.Series, index: bool) -> str:
    try:
        if isinstance(obj, pd.DataFrame):
            return obj.to_markdown(index=index)
        return obj.to_markdown()
    except (ImportError, AttributeError):
        return obj.to_string()


def _normalize_code(code) -> str:
    if isinstance(code, list):
        return "\n".join(str(line) for line in code)
    return str(code or "").strip()


class AIAnalyst:
    """
    Core AI engine that:
    - Answers questions about uploaded documents
    - Analyzes CSV data using pandas
    - Suggests and generates visualizations
    """

    def __init__(self, api_key: str | None = None, vector_store: VectorStore | None = None):
        if not api_key:
            raise ValueError("An API key is required to initialize the analyst.")
        self.client = genai.Client(api_key=api_key)
        self.model = settings.gemini_model
        self.vector_store = vector_store or VectorStore(api_key=api_key)

    def _generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
        json_mode: bool = False,
        max_output_tokens: int = 2048,
    ) -> str:
        """Send a prompt to Gemini and return the text response."""
        config_kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:
            raise GeminiServiceError(
                "Gemini could not complete this request. "
                f"Check your API key, model access, and network. ({type(exc).__name__}: {exc})"
            ) from exc

        text = _response_text(response)
        if text:
            return text
        raise GeminiServiceError("Gemini returned an empty response. Try rephrasing the question.")

    def ask_document(self, question: str, chat_history: list[dict] | None = None) -> dict:
        """Answer a question using retrieved document context."""
        results = self.vector_store.search(question, top_k=settings.top_k)

        if not results:
            return {
                "answer": "I don't have any documents to search through yet. Please upload some PDFs first.",
                "sources": [],
                "context_used": [],
            }

        context_parts = []
        sources = []
        for i, r in enumerate(results):
            context_parts.append(f"[Source {i + 1}] {r['text']}")
            source_info = {
                "source": r["metadata"].get("source", "Unknown"),
                "score": r["score"],
                "chunk_index": r["metadata"].get("chunk_index", "?"),
            }
            if source_info not in sources:
                sources.append(source_info)

        context = "\n\n".join(context_parts)
        system = (
            "You are an AI Data Analyst. Answer the user's question based ONLY on the "
            "provided context. If the context doesn't contain enough information, say so. "
            "Always cite which source(s) you used with [Source N] notation."
        )

        history_text = ""
        if chat_history:
            recent = chat_history[-6:]
            history_parts = []
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_parts.append(f"{role}: {msg['content']}")
            history_text = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join(history_parts) + "\n"

        prompt = f"CONTEXT:\n{context}\n{history_text}\nQUESTION: {question}"

        try:
            answer = self._generate(prompt, system_instruction=system, temperature=0.2)
        except GeminiServiceError as exc:
            return {
                "answer": str(exc),
                "sources": sources,
                "context_used": context_parts,
            }

        return {
            "answer": answer,
            "sources": sources,
            "context_used": context_parts,
        }

    def ask_data(self, question: str, df: pd.DataFrame, chat_history: list[dict] | None = None) -> dict:
        """Answer a question about a pandas DataFrame."""
        schema = self._describe_dataframe(df)

        system = (
            "You are an AI Data Analyst. The user has a pandas DataFrame called `df`.\n\n"
            f"DATAFRAME SCHEMA:\n{schema}\n\n"
            "RULES:\n"
            "1. Write Python/pandas code to answer the question.\n"
            "2. Store the final answer in a variable called `result`.\n"
            "3. The `result` should be a simple value, Series, or small DataFrame (under 50 rows).\n"
            "4. Do NOT use print(). Do NOT import pandas (it's already imported as pd). "
            "numpy is available as np.\n"
            "5. Do NOT modify the original DataFrame.\n"
            "6. After the code, suggest a chart type if the result is visualizable.\n\n"
            "Respond in this exact JSON format (no markdown fences):\n"
            '{"code": "your pandas code here", "explanation": "plain English explanation", '
            '"chart_type": "bar|line|pie|scatter|heatmap|none", '
            '"chart_config": {"x": "column", "y": "column", "title": "Chart Title"}}'
        )

        history_text = ""
        if chat_history:
            recent = chat_history[-6:]
            history_parts = []
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_parts.append(f"{role}: {msg['content']}")
            history_text = "PREVIOUS CONVERSATION:\n" + "\n".join(history_parts) + "\n\n"

        prompt = f"{history_text}QUESTION: {question}"

        try:
            raw = self._generate(
                prompt,
                system_instruction=system,
                temperature=0.1,
                json_mode=True,
                max_output_tokens=4096,
            )
        except GeminiServiceError as exc:
            return {
                "answer": str(exc),
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

        parsed = parse_model_json(raw)
        if parsed is None:
            parsed = _regex_extract(raw)

        if not parsed:
            return {
                "answer": (
                    "I understood your question but had trouble formatting the response. "
                    f"Here's my raw analysis:\n\n{raw[:1200]}{'...' if len(raw) > 1200 else ''}"
                ),
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

        code = _normalize_code(parsed.get("code", ""))
        explanation = str(parsed.get("explanation") or "").strip()
        chart_type = str(parsed.get("chart_type") or "none").strip().lower()
        chart_config = parsed.get("chart_config") or {}
        if not isinstance(chart_config, dict):
            chart_config = {}

        if not code:
            return {
                "answer": explanation or "I could not generate analysis code for that question.",
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

        exec_result = safe_execute(code, df)
        if exec_result["error"]:
            return {
                "answer": (
                    "I tried to analyze your data but ran into an error:\n\n"
                    f"`{exec_result['error']}`\n\n{explanation}"
                ).strip(),
                "code": code,
                "result": None,
                "chart_suggestion": None,
            }

        result = exec_result["result"]
        formatted = format_result(result)
        answer = f"{explanation}\n\n**Result:**\n{formatted}" if explanation else f"**Result:**\n{formatted}"

        return {
            "answer": answer,
            "code": code,
            "result": result,
            "chart_suggestion": {"type": chart_type, "config": chart_config} if chart_type != "none" else None,
        }

    def ask(
        self,
        question: str,
        df: pd.DataFrame | None = None,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """Smart question router that decides whether to query documents or data."""
        has_docs = self.vector_store.collection.count() > 0
        has_data = df is not None and not df.empty

        try:
            if has_data and has_docs:
                route = self._classify_question(question, df)
                if route == "data":
                    return self.ask_data(question, df, chat_history)
                if route == "document":
                    return self.ask_document(question, chat_history)

                result = self.ask_data(question, df, chat_history)
                if result.get("result") is not None:
                    return result
                return self.ask_document(question, chat_history)

            if has_data:
                return self.ask_data(question, df, chat_history)
            if has_docs:
                return self.ask_document(question, chat_history)
            return {
                "answer": "No data available yet. Please upload a CSV file or PDF document to get started.",
                "sources": [],
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }
        except GeminiServiceError as exc:
            return {
                "answer": str(exc),
                "sources": [],
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

    def _classify_question(self, question: str, df: pd.DataFrame) -> str:
        """Classify whether a question is about data, documents, or both."""
        columns = ", ".join(df.columns.tolist())
        system = (
            "Classify the user's question into one of: 'data', 'document', 'hybrid'.\n"
            f"The user has a CSV with columns: {columns}\n"
            "They also have PDF documents uploaded.\n"
            "Respond with ONLY one word: data, document, or hybrid."
        )
        try:
            result = self._generate(question, system_instruction=system, temperature=0).strip().lower()
        except GeminiServiceError:
            return "hybrid"

        token = re.split(r"[^a-z]+", result, maxsplit=1)[0] if result else ""
        if token in ("data", "document", "hybrid"):
            return token
        for option in ("hybrid", "document", "data"):
            if option in result:
                return option
        return "hybrid"

    def _describe_dataframe(self, df: pd.DataFrame) -> str:
        """Create a concise schema description for the AI."""
        lines = [f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n"]
        lines.append("Columns:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = int(df[col].count())
            sample = str(df[col].dropna().iloc[0]) if non_null > 0 else "N/A"
            if len(sample) > 50:
                sample = sample[:50] + "..."
            lines.append(f"  - {col} ({dtype}): {non_null} non-null, sample: {sample}")

        lines.append(f"\nFirst 3 rows:\n{df.head(3).to_string()}")
        return "\n".join(lines)


def _response_text(response) -> str:
    """Extract text from a google-genai response without raising on empty/blocked output."""
    text = getattr(response, "text", None)
    if text:
        return text
    try:
        candidates = getattr(response, "candidates", None) or []
        parts = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                value = getattr(part, "text", None)
                if value:
                    parts.append(value)
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _regex_extract(raw: str) -> dict | None:
    """Last-resort field extraction when the model returns almost-JSON."""
    explanation_match = re.search(r'"explanation"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
    code_match = re.search(r'"code"\s*:\s*"((?:\\.|[^"\\])*)"', raw, re.DOTALL)
    chart_type_match = re.search(r'"chart_type"\s*:\s*"([^"]*)"', raw)

    if not (explanation_match or code_match):
        return None

    def _unescape(value: str) -> str:
        return value.encode("utf-8").decode("unicode_escape")

    parsed: dict = {}
    if explanation_match:
        parsed["explanation"] = _unescape(explanation_match.group(1))
    if code_match:
        parsed["code"] = _unescape(code_match.group(1))
    if chart_type_match:
        parsed["chart_type"] = chart_type_match.group(1)
    return parsed
