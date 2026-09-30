"""Unit tests for Phase 8: Retrieval Failure Analysis."""
import pytest
from failure_analysis.models import FailureCategory
from failure_analysis.categorizer import FailureCategorizer
from failure_analysis.reporter import FailureBenchmarkReporter


@pytest.fixture
def sample_corpus():
    chunks = {
        "c_doc1": "Convolutional networks are widely utilized in computer vision and visual recognition tasks.",
        "c_doc2": "System error CODE-42 occurs when memory buffer exhausts limits in production instances.",
        "c_doc3": "short",  # Poor chunking candidate
        "c_doc4": "Quantum computing uses qubits and superposition to process calculations.",
    }
    metadatas = {
        "c_doc1": {"category": "ml", "env": "prod"},
        "c_doc2": {"category": "infra", "env": "prod"},
        "c_doc3": {"category": "misc", "env": "staging"},
        "c_doc4": {"category": "physics", "env": "research"},
    }
    return chunks, metadatas


def test_success_diagnosis(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="What is computer vision?",
        retrieved_results=[{"chunk_id": "c_doc1"}],
        expected_relevant_ids={"c_doc1"},
    )
    assert diag.category == FailureCategory.NO_FAILURE
    assert diag.confidence == 1.0


def test_missing_document(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="Where is the payment gateway document?",
        retrieved_results=[{"chunk_id": "c_doc1"}],
        expected_relevant_ids={"c_missing_123"},
    )
    assert diag.category == FailureCategory.MISSING_DOCUMENT
    assert "missing_chunks" in diag.diagnostics
    assert "Ingest and index" in diag.recommended_action


def test_out_of_corpus_query(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="How to cook pasta carbonara?",
        retrieved_results=[{"chunk_id": "c_doc1"}],
        expected_relevant_ids=set(),
        is_known_out_of_corpus=True,
    )
    assert diag.category == FailureCategory.OUT_OF_CORPUS_QUERY


def test_metadata_filter_failure(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    # c_doc2 has env="prod", filter requests env="staging"
    diag = categorizer.diagnose(
        query="explain CODE-42",
        retrieved_results=[],
        expected_relevant_ids={"c_doc2"},
        applied_metadata_filter={"env": "staging"},
    )
    assert diag.category == FailureCategory.METADATA_FILTER_FAILURE
    assert "c_doc2" in diag.diagnostics["excluded_chunks"]


def test_ranking_failure(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    # c_doc1 was in candidate pool, but reranker dropped it outside top-k
    candidate_pool = [{"chunk_id": "c_doc4"}, {"chunk_id": "c_doc1"}]
    retrieved_results = [{"chunk_id": "c_doc4"}]

    diag = categorizer.diagnose(
        query="neural network vision",
        retrieved_results=retrieved_results,
        expected_relevant_ids={"c_doc1"},
        candidate_pool=candidate_pool,
    )
    assert diag.category == FailureCategory.RANKING_FAILURE
    assert "c_doc1" in diag.diagnostics["candidate_pool_hits"]


def test_poor_chunking(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="what is short content",
        retrieved_results=[],
        expected_relevant_ids={"c_doc3"},
    )
    assert diag.category == FailureCategory.POOR_CHUNKING


def test_lexical_mismatch(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    # Query uses vocabulary completely disjoint from c_doc1 ("perceptrons", "optics")
    diag = categorizer.diagnose(
        query="perceptrons automated optics",
        retrieved_results=[],
        expected_relevant_ids={"c_doc1"},
    )
    assert diag.category == FailureCategory.LEXICAL_MISMATCH
    assert "HyDE" in diag.recommended_action or "expansion" in diag.recommended_action


def test_query_interpretation_failure(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="check CODE-42",
        retrieved_results=[],
        expected_relevant_ids={"c_doc2"},
        route_decision={"category": "conceptual", "strategies": ["dense"]},
    )
    assert diag.category == FailureCategory.QUERY_INTERPRETATION_FAILURE


def test_multi_hop_failure(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)

    diag = categorizer.diagnose(
        query="compare convolutional nets vs quantum computing",
        retrieved_results=[{"chunk_id": "c_doc1"}],
        expected_relevant_ids={"c_doc1", "c_doc4"},
        sub_query_results={"convolutional nets": ["c_doc1"], "quantum computing": []},
    )
    assert diag.category == FailureCategory.MULTI_HOP_FAILURE


def test_failure_benchmark_reporter(sample_corpus):
    chunks, metadatas = sample_corpus
    categorizer = FailureCategorizer(chunks, metadatas)
    reporter = FailureBenchmarkReporter(categorizer)

    test_queries = [
        {"query": "vision models", "expected_relevant_ids": {"c_doc1"}},
        {"query": "unknown topic", "expected_relevant_ids": {"c_missing_999"}},
    ]

    def mock_retriever(q, filter_dict=None):
        if "vision" in q:
            return {"results": [{"chunk_id": "c_doc1"}]}
        return {"results": []}

    report = reporter.analyze_evaluation_run(test_queries, mock_retriever)
    assert report["summary"]["total_queries"] == 2
    assert report["summary"]["successful_retrievals"] == 1
    assert report["summary"]["failed_retrievals"] == 1
    assert report["failure_counts"][FailureCategory.MISSING_DOCUMENT.value] == 1
