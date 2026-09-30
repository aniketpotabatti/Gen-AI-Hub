"""Phase 5 tests: Query intelligence modules, rewriting, expansion, decomposition, HyDE, difficulty, and adaptive integration."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query_intelligence.rewriter import QueryRewriter
from query_intelligence.expander import QueryExpander
from query_intelligence.decomposer import QueryDecomposer
from query_intelligence.hyde import HyDEGenerator
from query_intelligence.entity_extractor import EntityExtractor
from query_intelligence.difficulty import estimate_query_difficulty
from tests.test_phase4 import _adaptive_toy


def test_query_rewriter_normalization():
    rewriter = QueryRewriter()
    q = "how to retreive vectors from vectordb with embedings?"
    normalized = rewriter.normalize(q)
    assert "retrieve" in normalized
    assert "embeddings" in normalized
    assert "vector database" in normalized


def test_query_rewriter_history_coreference():
    rewriter = QueryRewriter()
    history = [
        {"role": "user", "content": "I am experiencing error CODE-42 in the indexing process."},
        {"role": "assistant", "content": "CODE-42 means the index vector file is missing."},
    ]
    follow_up = "How can I fix it?"
    rewritten = rewriter.rewrite_with_history(follow_up, history)
    assert "CODE-42" in rewritten


def test_query_expander_domain_synonyms():
    expander = QueryExpander()
    expanded = expander.expand("dense retrieval latency")
    assert "vector" in expanded or "search" in expanded or "response time" in expanded


def test_query_decomposer_multiquery():
    decomposer = QueryDecomposer()
    res1 = decomposer.decompose("What is dense retrieval and how does BM25 work?")
    assert len(res1) == 2

    res2 = decomposer.decompose("dense versus sparse retrieval")
    assert len(res2) == 2


def test_hyde_generation():
    hyde = HyDEGenerator()
    doc = hyde.generate("What is reciprocal rank fusion?")
    assert "reciprocal rank fusion" in doc
    assert len(doc) > 30

    custom = HyDEGenerator(generator_fn=lambda q: f"Synthesized answer for {q}")
    assert custom.generate("test") == "Synthesized answer for test"


def test_entity_extractor():
    extractor = EntityExtractor()
    text = 'Look up CODE-42 in /var/log/app.py and check version v2.1 for "connection refused"'
    entities = extractor.extract(text)
    assert "CODE-42" in entities["codes"]
    assert "v2.1" in entities["versions"]
    assert any("app.py" in p for p in entities["paths"])
    assert "connection refused" in entities["quotes"]


def test_estimate_query_difficulty():
    easy = estimate_query_difficulty("CODE-42 failure")
    assert easy["level"] == "easy"
    assert easy["score"] < 0.5

    hard = estimate_query_difficulty("tell me something about that thing")
    assert hard["level"] in ("medium", "hard")
    assert hard["score"] >= 0.5


def test_adaptive_retriever_with_intelligence():
    ad = _adaptive_toy()
    # Test normalization & entity reporting
    res = ad.search("retreive CODE-42 from vectordb", k=2, enable_intelligence=True)
    assert "intelligence" in res
    intel = res["intelligence"]
    assert "CODE-42" in intel["entities"]["codes"]
    assert "vector database" in intel["processed_query"]

    # Test conversation history coreference
    history = [{"role": "user", "content": "Encountered CODE-42 failure"}]
    res_conv = ad.search("how to solve it?", k=2, conversation_history=history, enable_intelligence=True)
    assert "CODE-42" in res_conv["intelligence"]["processed_query"]
    assert res_conv["results"][0]["chunk_id"] == "c1"
