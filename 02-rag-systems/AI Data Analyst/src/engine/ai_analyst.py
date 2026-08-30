"""
AI Data Analyst - the brain of the application.
Routes questions to the right strategy, generates answers, and suggests charts.
"""

import json

import pandas as pd
import google.generativeai as genai

from src.engine.vector_store import VectorStore
from src.utils.config import settings


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot be reached or returns a transport failure."""


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
        genai.configure(api_key=api_key)
        self.model = settings.gemini_model
        self.vector_store = vector_store or VectorStore(api_key=api_key)

    def _generate(self, prompt: str, system_instruction: str = "", temperature: float = 0.2) -> str:
        """Send a prompt to Gemini and return the text response."""
        try:
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_instruction if system_instruction else None,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1500,
                )
            )
            response = model.generate_content(prompt)
            return response.text or ""
        except Exception as exc:
            raise GeminiServiceError(
                "Gemini could not be reached from this machine. "
                "Check your network, proxy, firewall, or API access."
            ) from exc

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
            "4. Do NOT use print(). Do NOT import pandas (it's already imported as pd).\n"
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
            raw = self._generate(prompt, system_instruction=system, temperature=0.1)
        except GeminiServiceError as exc:
            return {
                "answer": str(exc),
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

        try:
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return {
                "answer": f"I understood your question but had trouble formatting the response. Here's my raw analysis:\n\n{raw}",
                "code": "",
                "result": None,
                "chart_suggestion": None,
            }

        code = parsed.get("code", "")
        explanation = parsed.get("explanation", "")
        chart_type = parsed.get("chart_type", "none")
        chart_config = parsed.get("chart_config", {})

        exec_result = self._safe_execute(code, df)
        if exec_result["error"]:
            return {
                "answer": f"I tried to analyze your data but ran into an error:\n\n`{exec_result['error']}`\n\n{explanation}",
                "code": code,
                "result": None,
                "chart_suggestion": None,
            }

        result = exec_result["result"]
        formatted_result = self._format_result(result)

        return {
            "answer": f"{explanation}\n\n**Result:**\n{formatted_result}",
            "code": code,
            "result": result,
            "chart_suggestion": {
                "type": chart_type,
                "config": chart_config,
            }
            if chart_type != "none"
            else None,
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
                if result["result"] is not None:
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
        if result in ("data", "document", "hybrid"):
            return result
        return "hybrid"

    def _describe_dataframe(self, df: pd.DataFrame) -> str:
        """Create a concise schema description for the AI."""
        lines = [f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n"]
        lines.append("Columns:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].count()
            sample = str(df[col].dropna().iloc[0]) if non_null > 0 else "N/A"
            if len(sample) > 50:
                sample = sample[:50] + "..."
            lines.append(f"  - {col} ({dtype}): {non_null} non-null, sample: {sample}")

        lines.append(f"\nFirst 3 rows:\n{df.head(3).to_string()}")
        return "\n".join(lines)

    def _safe_execute(self, code: str, df: pd.DataFrame) -> dict:
        """Execute AI-generated pandas code safely."""
        try:
            local_vars = {"df": df.copy(), "pd": pd}
            exec(code, {"__builtins__": {}}, local_vars)
            return {"result": local_vars.get("result"), "error": None}
        except Exception as e:
            return {"result": None, "error": f"{type(e).__name__}: {str(e)}"}

    def _format_result(self, result) -> str:
        """Format execution result for display."""
        if result is None:
            return "No result returned."
        if isinstance(result, pd.DataFrame):
            if len(result) > 20:
                return f"{result.head(20).to_markdown(index=False)}\n\n*...showing first 20 of {len(result)} rows*"
            return result.to_markdown(index=False)
        if isinstance(result, pd.Series):
            return result.to_markdown()
        return str(result)
