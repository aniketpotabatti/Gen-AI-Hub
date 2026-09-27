"""Default reproducible benchmark suite for SemanticSearchX."""
from typing import List
from evaluation.robustness import RobustnessTestCase


def build_default_robustness_suite(
    sample_chunk_id: str,
    error_chunk_id: str,
    arch_chunk_id: str,
) -> List[RobustnessTestCase]:
    """Build test cases covering all 11 required robustness dimensions."""
    return [
        # 1. Short query
        RobustnessTestCase(
            category="short",
            query="ML",
            relevant_chunks={sample_chunk_id},
            description="Extremely short 2-character query",
        ),
        # 2. Long verbose query
        RobustnessTestCase(
            category="long_verbose",
            query="I am a researcher studying artificial intelligence algorithms and would like to understand what machine learning means in the context of systems learning from data",
            relevant_chunks={sample_chunk_id},
            description="Verbose query with conversational filler",
        ),
        # 3. Ambiguous query
        RobustnessTestCase(
            category="ambiguous",
            query="learning systems",
            relevant_chunks={sample_chunk_id},
            description="Ambiguous multi-sense query",
        ),
        # 4. Typos and misspellings
        RobustnessTestCase(
            category="typos",
            query="how to retreive vectors from vectordb with embedings?",
            relevant_chunks={sample_chunk_id, arch_chunk_id},
            description="Multiple common retrieval typos",
        ),
        # 5. Exact identifiers
        RobustnessTestCase(
            category="exact_identifier",
            query="CODE-42",
            relevant_chunks={error_chunk_id},
            description="Exact error code identifier",
        ),
        # 6. Numerical query
        RobustnessTestCase(
            category="numerical",
            query="42 error code meaning",
            relevant_chunks={error_chunk_id},
            description="Query centered on numbers",
        ),
        # 7. Temporal query
        RobustnessTestCase(
            category="temporal",
            query="what is the latest error CODE-42 update",
            relevant_chunks={error_chunk_id},
            description="Temporal framing for recent changes",
        ),
        # 8. Multi-hop / compound query
        RobustnessTestCase(
            category="multi_hop",
            query="What is machine learning and what is CODE-42?",
            relevant_chunks={sample_chunk_id, error_chunk_id},
            description="Compound query targeting multiple separate chunks",
        ),
        # 9. Multi-turn conversational query
        RobustnessTestCase(
            category="multi_turn",
            query="how do I fix it?",
            relevant_chunks={error_chunk_id},
            description="Conversational follow-up requiring coreference resolution",
            conversation_history=[
                {"role": "user", "content": "I encountered CODE-42 in indexing."},
                {"role": "assistant", "content": "CODE-42 indicates missing files."},
            ],
        ),
        # 10. Out-of-domain query
        RobustnessTestCase(
            category="out_of_domain",
            query="quantum entanglement thermodynamics astrophysics",
            relevant_chunks=set(),
            description="Completely foreign topic with no corpus match",
            is_unanswerable=True,
        ),
        # 11. Negative / unanswerable query
        RobustnessTestCase(
            category="negative_unanswerable",
            query="How to bake a chocolate cake in Python?",
            relevant_chunks=set(),
            description="Completely unrelated baking query",
            is_unanswerable=True,
        ),
    ]
