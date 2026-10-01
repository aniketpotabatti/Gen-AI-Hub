"""Tests for the dashboard's HTTP client and pure parsing helpers."""
import json

import httpx
import pytest

from dashboard.api_client import ApiError, SemanticSearchClient
from dashboard.parsing import parse_json_object, split_ids


def _client(handler) -> SemanticSearchClient:
    """Build a client whose transport is a MockTransport (no network)."""
    return SemanticSearchClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )


def test_health_parses_json():
    def handler(request):
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "healthy", "indexed_chunks": 3})

    with _client(handler) as client:
        assert client.health()["indexed_chunks"] == 3


def test_search_builds_expected_payload():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"query": "x", "results": []})

    with _client(handler) as client:
        client.search("hello", k=7, dense_weight=0.25, use_reranker=False, explain=True)

    assert captured["path"] == "/api/v1/search"
    assert captured["payload"] == {
        "query": "hello",
        "k": 7,
        "metadata_filter": None,
        "dense_weight": 0.25,
        "use_reranker": False,
        "explain": True,
        "bypass_cache": False,
    }


def test_corpus_sends_pagination_and_filter():
    captured = {}

    def handler(request):
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200, json={"total": 0, "offset": 0, "limit": 5, "chunks": []}
        )

    with _client(handler) as client:
        client.corpus(limit=5, offset=20, q="guide")

    assert captured["params"] == {"limit": "5", "offset": "20", "q": "guide"}


def test_corpus_omits_filter_when_blank():
    captured = {}

    def handler(request):
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200, json={"total": 0, "offset": 0, "limit": 5, "chunks": []}
        )

    with _client(handler) as client:
        client.corpus(limit=5)

    assert "q" not in captured["params"]


def test_error_detail_is_surfaced():
    def handler(request):
        return httpx.Response(409, json={"detail": "Corpus is empty"})

    with _client(handler) as client:
        with pytest.raises(ApiError) as excinfo:
            client.run_arena([{"query": "q"}])

    assert excinfo.value.status_code == 409
    assert "Corpus is empty" in str(excinfo.value)


def test_network_error_becomes_api_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with _client(handler) as client:
        with pytest.raises(ApiError):
            client.health()


def test_arena_html_returns_text():
    def handler(request):
        return httpx.Response(
            200, text="<html>ok</html>", headers={"content-type": "text/html"}
        )

    with _client(handler) as client:
        assert "ok" in client.arena_html()


def test_parse_json_object():
    assert parse_json_object("") == (None, None)
    assert parse_json_object('{"source": "handbook"}') == ({"source": "handbook"}, None)

    value, error = parse_json_object("[1, 2, 3]")
    assert value is None and error is not None

    value, error = parse_json_object("{not json}")
    assert value is None and error is not None


def test_split_ids():
    assert split_ids("") == []
    assert split_ids("a, b   c,d") == ["a", "b", "c", "d"]


@pytest.mark.asyncio
async def test_corpus_endpoint_lists_indexed_chunks():
    """The new /api/v1/corpus endpoint serves the dashboard's corpus explorer."""
    from api.app import app

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            await client.post(
                "/api/v1/index",
                json={
                    "chunks": [
                        {
                            "chunk_id": "dash_1",
                            "text": "Adaptive routing selects a retrieval pipeline.",
                            "metadata": {"source": "dash"},
                        },
                        {
                            "chunk_id": "dash_2",
                            "text": "BM25 ranks exact identifiers highly.",
                            "metadata": {"source": "dash"},
                        },
                    ]
                },
            )

            res = await client.get("/api/v1/corpus?limit=1&offset=0")
            assert res.status_code == 200
            body = res.json()
            assert body["total"] == 2
            assert len(body["chunks"]) == 1
            assert set(body["chunks"][0]) == {"chunk_id", "text", "metadata"}

            filtered = await client.get("/api/v1/corpus?q=BM25")
            assert filtered.status_code == 200
            ids = [chunk["chunk_id"] for chunk in filtered.json()["chunks"]]
            assert ids == ["dash_2"]
