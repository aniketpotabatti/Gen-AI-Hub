"""Retrieval Benchmark Arena: head-to-head comparison of retrieval pipelines.

Runs a labeled evaluation query set through the plan-specified pipeline ladder
and reports quality, system performance and cost side by side:

    Dense
    BM25
    Hybrid
    Hybrid + Reranker
    Adaptive
    Adaptive + Reranker

Quality : Recall@K, Precision@K, Hit Rate@K, MRR, nDCG@K, Context Precision@K
Perf    : p50/p95/p99 latency, mean latency, throughput (QPS)
Cost    : query-embedding passes, measured reranker pairs, estimated USD

Notes on measurement honesty:
- Reranker pairs are *measured* through a counting proxy injected per pipeline
  call (``HybridRetriever.search(reranker=...)``) so the live engine is never
  mutated while an arena run is in flight.
- Query embedding passes are *estimated* from the pipeline specification; the
  embedding model is resolved internally by the retriever and has no injection
  point. Multi-query adaptive fan-out therefore reports a lower bound.
- Latency percentiles are computed from the timings collected during the run
  itself rather than re-executing queries (avoids doubling model cost).
"""
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from evaluation.metrics import evaluate
from evaluation.profiler import estimate_costs

# Pipeline identifiers, in the leaderboard order defined by the project plan.
PIPELINE_ORDER: Tuple[str, ...] = (
    "dense",
    "bm25",
    "hybrid",
    "hybrid_rerank",
    "adaptive",
    "adaptive_rerank",
)

PIPELINE_LABELS: Dict[str, str] = {
    "dense": "Dense",
    "bm25": "BM25",
    "hybrid": "Hybrid",
    "hybrid_rerank": "Hybrid + Reranker",
    "adaptive": "Adaptive",
    "adaptive_rerank": "Adaptive + Reranker",
}

# Estimated dense embedding passes per query (see module docstring caveat).
EMBEDDING_PASSES_PER_QUERY: Dict[str, int] = {
    "dense": 1,
    "bm25": 0,
    "hybrid": 1,
    "hybrid_rerank": 1,
    "adaptive": 1,
    "adaptive_rerank": 1,
}

DEFAULT_KS: Tuple[int, ...] = (1, 3, 5)

_STOPWORDS = frozenset(
    """a an and are as at be been but by can could did do does for from had has have how
    in into is it its of on or should so than that the their then there these this to was
    were what when where which who why will with would you your i me my we our""".split()
)


@dataclass
class ArenaQuery:
    """A single evaluation probe with ground-truth relevant chunk ids."""

    query: str
    relevant_chunks: Set[str] = field(default_factory=set)
    category: str = "general"
    metadata_filter: Optional[Dict[str, Any]] = None
    description: str = ""


class CountingReranker:
    """Delegates to a real reranker while counting scored query/chunk pairs."""

    def __init__(self, reranker):
        self._reranker = reranker
        self.pairs = 0
        self.calls = 0

    def score(self, query: str, texts: List[str]) -> List[float]:
        texts = list(texts)
        self.pairs += len(texts)
        self.calls += 1
        return self._reranker.score(query, texts)


def _percentiles(values: List[float]) -> Dict[str, float]:
    """Summarize a latency sample in milliseconds (nearest-rank percentiles)."""
    if not values:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "mean_ms": 0.0}
    ordered = sorted(values)
    n = len(ordered)

    def pick(p: float) -> float:
        idx = max(0, min(int(p / 100.0 * n + 0.9999) - 1, n - 1))
        return ordered[idx]

    return {
        "p50_ms": round(pick(50.0), 3),
        "p95_ms": round(pick(95.0), 3),
        "p99_ms": round(pick(99.0), 3),
        "mean_ms": round(sum(ordered) / n, 3),
    }


class RetrievalArena:
    """Executes the pipeline ladder over a labeled query set and compiles a report."""

    def __init__(
        self,
        hybrid,
        adaptive=None,
        reranker=None,
        candidate_k: int = 20,
        ks: Tuple[int, ...] = DEFAULT_KS,
        avg_query_tokens: int = 15,
        avg_chunk_tokens: int = 120,
    ):
        self.hybrid = hybrid
        self.adaptive = adaptive
        self.reranker = reranker if reranker is not None else getattr(hybrid, "reranker", None)
        self.candidate_k = candidate_k
        self.ks = tuple(ks)
        self.avg_query_tokens = avg_query_tokens
        self.avg_chunk_tokens = avg_chunk_tokens

    # ------------------------------------------------------------------ runners
    def _adaptive_available(self) -> bool:
        return self.adaptive is not None

    def _chunk_text(self, chunk_id: str, meta: Dict[str, Any]) -> str:
        return self.hybrid._full_text(chunk_id, meta or {})

    def _build_runners(
        self, selected: List[str]
    ) -> Tuple[Dict[str, Callable[[ArenaQuery, int], List[str]]], Dict[str, CountingReranker]]:
        """Create per-pipeline query runners bound to fresh measurement proxies."""
        runners: Dict[str, Callable[[ArenaQuery, int], List[str]]] = {}
        proxies: Dict[str, CountingReranker] = {}
        hybrid = self.hybrid

        def ids_of(results: List[Dict[str, Any]]) -> List[str]:
            return [r.get("chunk_id", "") for r in results]

        if "dense" in selected:
            def _dense(aq: ArenaQuery, k: int) -> List[str]:
                return ids_of(hybrid.search(
                    aq.query, k=k, candidate_k=self.candidate_k,
                    metadata_filter=aq.metadata_filter,
                    strategies=["dense"], rerank=False))
            runners["dense"] = _dense

        if "bm25" in selected:
            def _bm25(aq: ArenaQuery, k: int) -> List[str]:
                return ids_of(hybrid.search(
                    aq.query, k=k, candidate_k=self.candidate_k,
                    metadata_filter=aq.metadata_filter,
                    strategies=["bm25"], rerank=False))
            runners["bm25"] = _bm25

        if "hybrid" in selected:
            def _hybrid(aq: ArenaQuery, k: int) -> List[str]:
                return ids_of(hybrid.search(
                    aq.query, k=k, candidate_k=self.candidate_k,
                    metadata_filter=aq.metadata_filter, rerank=False))
            runners["hybrid"] = _hybrid

        if "hybrid_rerank" in selected and self.reranker is not None:
            h_proxy = CountingReranker(self.reranker)
            proxies["hybrid_rerank"] = h_proxy

            def _hybrid_rerank(aq: ArenaQuery, k: int) -> List[str]:
                return ids_of(hybrid.search(
                    aq.query, k=k, candidate_k=self.candidate_k,
                    metadata_filter=aq.metadata_filter, rerank=True, reranker=h_proxy))
            runners["hybrid_rerank"] = _hybrid_rerank

        if self._adaptive_available() and "adaptive" in selected:
            def _adaptive(aq: ArenaQuery, k: int) -> List[str]:
                out = self.adaptive.search(
                    query=aq.query, k=k, metadata_filter=aq.metadata_filter)
                return ids_of(out.get("results", []))
            runners["adaptive"] = _adaptive

        if self._adaptive_available() and "adaptive_rerank" in selected and self.reranker is not None:
            a_proxy = CountingReranker(self.reranker)
            proxies["adaptive_rerank"] = a_proxy

            def _adaptive_rerank(aq: ArenaQuery, k: int) -> List[str]:
                pool = self.adaptive.search(
                    query=aq.query, k=max(k, self.candidate_k),
                    metadata_filter=aq.metadata_filter).get("results", [])
                if not pool:
                    return []
                ids = ids_of(pool)
                metas = {r.get("chunk_id", ""): r.get("metadata", {}) for r in pool}
                texts = [self._chunk_text(cid, metas.get(cid, {})) for cid in ids]
                scores = a_proxy.score(aq.query, texts)
                order = sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)
                return [ids[i] for i in order[:k]]
            runners["adaptive_rerank"] = _adaptive_rerank

        return runners, proxies


    # -------------------------------------------------------------- execution
    def run(
        self,
        queries: List[ArenaQuery],
        k: int = 5,
        ks: Optional[List[int]] = None,
        pipelines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute every selected pipeline over the query set and build a report."""
        if not queries:
            raise ValueError("arena requires at least one evaluation query")

        ks_sorted = sorted({int(x) for x in (ks or list(self.ks))} | {int(k)})
        selected = [p for p in PIPELINE_ORDER if pipelines is None or p in pipelines]
        if not selected:
            raise ValueError(
                f"no valid pipelines selected; choose from {list(PIPELINE_ORDER)}")

        runners, proxies = self._build_runners(selected)
        selected = [p for p in selected if p in runners]
        if not selected:
            raise ValueError(
                "none of the selected pipelines can run "
                "(reranker/adaptive component unavailable)")

        counters: Dict[str, Dict[str, int]] = {
            p: {"embedding_passes": 0} for p in selected
        }
        latencies_ms: Dict[str, List[float]] = {p: [] for p in selected}
        rankings: Dict[str, Dict[str, List[str]]] = {p: {} for p in selected}
        per_query: Dict[str, Dict[str, Any]] = {p: {} for p in selected}

        # Untimed warmup so model/index caches do not skew the first sample.
        for name in selected:
            for aq in queries[: min(2, len(queries))]:
                try:
                    runners[name](aq, k)
                except Exception:
                    pass
        for name in selected:
            counters[name]["embedding_passes"] = 0
        for proxy in proxies.values():
            proxy.pairs = 0
            proxy.calls = 0

        for aq in queries:
            for name in selected:
                t0 = time.perf_counter()
                try:
                    ids = runners[name](aq, k)[:k]
                except Exception:
                    ids = []
                latencies_ms[name].append((time.perf_counter() - t0) * 1000.0)
                counters[name]["embedding_passes"] += EMBEDDING_PASSES_PER_QUERY[name]
                rankings[name][aq.query] = ids
                per_query[name][aq.query] = {
                    "category": aq.category,
                    "ranked": ids,
                    "relevant": sorted(aq.relevant_chunks),
                    "hit_at_k": bool(set(ids) & aq.relevant_chunks),
                }


        relevance = {aq.query: set(aq.relevant_chunks) for aq in queries}
        primary = f"ndcg@{k}"
        num_queries = len(queries)

        pipeline_rows: List[Dict[str, Any]] = []
        for name in selected:
            quality = evaluate(rankings[name], relevance, ks=ks_sorted)
            quality = {key: round(float(val), 4) for key, val in quality.items()}
            perf = _percentiles(latencies_ms[name])
            total_sec = sum(latencies_ms[name]) / 1000.0
            perf["throughput_qps"] = round(num_queries / total_sec, 2) if total_sec > 0 else 0.0
            perf["total_queries"] = num_queries
            rerank_pairs = proxies[name].pairs if name in proxies else 0
            cost = self._estimate_pipeline_cost(
                counters[name]["embedding_passes"], rerank_pairs)
            pipeline_rows.append({
                "name": name,
                "label": PIPELINE_LABELS[name],
                "quality": quality,
                "performance": perf,
                "cost": cost,
                "primary_metric": primary,
                "primary_score": quality.get(primary, 0.0),
            })

        ordered = sorted(
            pipeline_rows,
            key=lambda row: (
                -row["primary_score"],
                -row["quality"].get("mrr", 0.0),
                row["performance"]["mean_ms"],
            ),
        )
        leaderboard = []
        for rank, row in enumerate(ordered, start=1):
            row["rank"] = rank
            leaderboard.append({
                "rank": rank,
                "pipeline": row["name"],
                "label": row["label"],
                "score": row["primary_score"],
                "mrr": row["quality"].get("mrr", 0.0),
                "mean_ms": row["performance"]["mean_ms"],
                "estimated_cost_usd": row["cost"]["estimated_cost_usd"],
            })

        winners = {
            "quality": ordered[0]["name"] if ordered else None,
            "quality_metric": primary,
            "latency": min(ordered, key=lambda r: r["performance"]["mean_ms"])["name"] if ordered else None,
            "throughput": max(ordered, key=lambda r: r["performance"]["throughput_qps"])["name"] if ordered else None,
            "cost": min(ordered, key=lambda r: r["cost"]["estimated_cost_usd"])["name"] if ordered else None,
        }

        return {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "num_queries": num_queries,
                "corpus_size": len(self.hybrid.vector_store),
                "k": k,
                "ks": ks_sorted,
                "candidate_k": self.candidate_k,
                "pipeline_count": len(ordered),
                "primary_metric": primary,
            },
            "pipelines": ordered,
            "leaderboard": leaderboard,
            "winners": winners,
            "queries": [
                {
                    "query": aq.query,
                    "category": aq.category,
                    "num_relevant": len(aq.relevant_chunks),
                    "metadata_filter": aq.metadata_filter,
                }
                for aq in queries
            ],
            "per_query": per_query,
        }


    def _estimate_pipeline_cost(
        self, embedding_passes: int, rerank_pairs: int
    ) -> Dict[str, Any]:
        """Estimate token footprint and USD cost for one pipeline run.

        Indexing cost is excluded (it is corpus-wide, not per-pipeline); only
        query-side embedding and reranker scoring are attributed.
        """
        depth = (rerank_pairs / embedding_passes) if embedding_passes else 0.0
        costs = estimate_costs(
            num_queries=embedding_passes,
            avg_query_tokens=self.avg_query_tokens,
            num_indexed_chunks=0,
            avg_chunk_tokens=self.avg_chunk_tokens,
            candidate_depth_k=depth,
        )
        return {
            "estimated_query_embeddings": embedding_passes,
            "rerank_pairs": rerank_pairs,
            "embedding_tokens": costs["query_embedding_tokens"],
            "rerank_tokens": costs["total_reranker_tokens"],
            "query_embedding_cost_usd": costs["query_embedding_cost_usd"],
            "rerank_cost_usd": costs["reranker_cost_usd"],
            "estimated_cost_usd": costs["total_cost_usd"],
        }


# ------------------------------------------------------------------ reporting
def render_leaderboard(report: Dict[str, Any], title: str = "Retrieval Benchmark Arena") -> str:
    """Render a fixed-width text leaderboard for terminal output."""
    meta = report["meta"]
    primary = meta["primary_metric"]
    lines = [
        title,
        "=" * 78,
        f"Queries: {meta['num_queries']} | Corpus: {meta['corpus_size']} chunks | "
        f"K={meta['k']} | Primary metric: {primary}",
        "-" * 78,
        f"{'#':<3} {'Pipeline':<22} {primary:>10} {'MRR':>7} {'Mean ms':>9} {'QPS':>8} {'Cost $':>10}",
        "-" * 78,
    ]
    for row in report["leaderboard"]:
        lines.append(
            f"{row['rank']:<3} {row['label']:<22} {row['score']:>10.3f} {row['mrr']:>7.3f} "
            f"{row['mean_ms']:>9.2f} "
            f"{next(p['performance']['throughput_qps'] for p in report['pipelines'] if p['name'] == row['pipeline']):>8.1f} "
            f"{row['estimated_cost_usd']:>10.4f}"
        )
    winners = report["winners"]
    lines.append("-" * 78)
    lines.append(
        "Winners -> quality: {quality} | fastest: {latency} | throughput: {throughput} | cheapest: {cost}".format(
            quality=PIPELINE_LABELS.get(winners.get("quality"), winners.get("quality")),
            latency=PIPELINE_LABELS.get(winners.get("latency"), winners.get("latency")),
            throughput=PIPELINE_LABELS.get(winners.get("throughput"), winners.get("throughput")),
            cost=PIPELINE_LABELS.get(winners.get("cost"), winners.get("cost")),
        )
    )
    return "\n".join(lines)


def to_json(report: Dict[str, Any], indent: int = 2) -> str:
    """Serialize an arena report to JSON text."""
    return json.dumps(report, indent=indent, sort_keys=False)



# ------------------------------------------------------------------ dashboard
_DASHBOARD_CSS = """
:root{--bg:#0f1420;--panel:#161d2d;--line:#26304a;--ink:#e8edf7;--muted:#95a3c4;
--good:#33d69f;--warn:#ffb454;--bad:#ff6b6b;--accent:#5b8cff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif;padding:28px}
h1{margin:0 0 4px;font-size:24px}
h2{margin:28px 0 10px;font-size:16px;letter-spacing:.4px;text-transform:uppercase;color:var(--muted)}
.sub{color:var(--muted);margin-bottom:18px}
.cards{display:flex;flex-wrap:wrap;gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:12px 16px;min-width:190px}
.card .k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.card .v{font-size:18px;font-weight:600;margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--panel);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:13px}
th{background:#1b2437;color:var(--muted);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{height:9px;border-radius:5px;background:var(--accent);min-width:2px}
.barcell{width:190px}
.hit{color:var(--good);font-weight:600}
.miss{color:var(--bad)}
code{background:#1b2437;padding:1px 5px;border-radius:4px;color:#cfe0ff}
.foot{color:var(--muted);margin-top:26px;font-size:12px}
"""



def _bar_cell(value: float, best: float, width: int = 190) -> str:
    pct = 0.0 if best <= 0 else max(2.0, min(100.0, (value / best) * 100.0))
    return (f'<td class="barcell"><div class="bar" style="width:{pct:.1f}%;'
            f'max-width:{width}px"></div></td>')


def render_dashboard(report: Dict[str, Any], title: str = "Retrieval Benchmark Arena") -> str:
    """Render a self-contained HTML dashboard (inline CSS, no external assets)."""
    meta = report["meta"]
    primary = meta["primary_metric"]
    pipelines = report["pipelines"]
    winners = report["winners"]
    ks = meta["ks"]
    best_score = max((p["primary_score"] for p in pipelines), default=0.0)
    best_mrr = max((p["quality"].get("mrr", 0.0) for p in pipelines), default=0.0)

    parts: List[str] = []
    parts.append("<!DOCTYPE html>\n<html lang='en'>\n<head>\n<meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    parts.append(f"<title>{escape(title)}</title>")
    parts.append(f"<style>{_DASHBOARD_CSS}</style>\n</head>\n<body>")
    parts.append(f"<h1>{escape(title)}</h1>")
    parts.append(
        "<div class='sub'>Generated {gen} &middot; {nq} labeled queries &middot; "
        "{corpus} indexed chunks &middot; K={k} &middot; primary metric "
        "<code>{primary}</code></div>".format(
            gen=escape(str(meta["generated_at"])),
            nq=meta["num_queries"],
            corpus=meta["corpus_size"],
            k=meta["k"],
            primary=escape(primary),
        )
    )

    label_of = {p["name"]: p["label"] for p in pipelines}
    parts.append("<div class='cards'>")
    for key, caption in (
        ("quality", f"Best quality ({primary})"),
        ("latency", "Lowest mean latency"),
        ("throughput", "Highest throughput"),
        ("cost", "Lowest estimated cost"),
    ):
        winner = winners.get(key)
        parts.append(
            "<div class='card'><div class='k'>{c}</div><div class='v'>{v}</div></div>".format(
                c=escape(caption),
                v=escape(label_of.get(winner, "-")),
            )
        )
    parts.append("</div>")

    # Leaderboard
    parts.append("<h2>Leaderboard</h2>")
    parts.append("<table><thead><tr>")
    parts.append("<th class='num'>#</th><th>Pipeline</th>")
    parts.append(f"<th class='num'>{escape(primary)}</th><th>Quality</th>")
    parts.append("<th class='num'>MRR</th><th>MRR</th>")
    parts.append("<th class='num'>Recall</th><th class='num'>Hit rate</th>")
    parts.append("<th class='num'>Mean ms</th><th class='num'>QPS</th>")
    parts.append("<th class='num'>Cost USD</th><th class='num'>Rerank pairs</th>")
    parts.append("</tr></thead><tbody>")
    for row in report["leaderboard"]:
        full = next(p for p in pipelines if p["name"] == row["pipeline"])
        q = full["quality"]
        parts.append("<tr>")
        parts.append(f"<td class='num'>{row['rank']}</td>")
        parts.append(f"<td>{escape(row['label'])}</td>")
        parts.append(f"<td class='num'>{row['score']:.3f}</td>")
        parts.append(_bar_cell(row["score"], best_score))
        parts.append(f"<td class='num'>{q.get('mrr', 0.0):.3f}</td>")
        parts.append(_bar_cell(q.get("mrr", 0.0), best_mrr))
        recall_key = f"recall@{meta['k']}"
        hit_key = f"hit_rate@{meta['k']}"
        parts.append(f"<td class='num'>{q.get(recall_key, 0.0):.3f}</td>")
        parts.append(f"<td class='num'>{q.get(hit_key, 0.0):.3f}</td>")
        parts.append(f"<td class='num'>{row['mean_ms']:.2f}</td>")
        parts.append(f"<td class='num'>{full['performance']['throughput_qps']:.1f}</td>")
        parts.append(f"<td class='num'>{row['estimated_cost_usd']:.5f}</td>")
        parts.append(f"<td class='num'>{full['cost']['rerank_pairs']}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


    # Full quality matrix
    parts.append("<h2>Quality detail</h2>")
    parts.append("<table><thead><tr><th>Pipeline</th>")
    for kk in ks:
        parts.append(f"<th class='num'>R@{kk}</th><th class='num'>P@{kk}</th>"
                     f"<th class='num'>nDCG@{kk}</th>")
    parts.append("<th class='num'>MRR</th><th class='num'>CtxPrec</th></tr></thead><tbody>")
    for row in report["leaderboard"]:
        full = next(p for p in pipelines if p["name"] == row["pipeline"])
        q = full["quality"]
        parts.append(f"<tr><td>{escape(row['label'])}</td>")
        for kk in ks:
            parts.append(f"<td class='num'>{q.get(f'recall@{kk}', 0.0):.3f}</td>")
            parts.append(f"<td class='num'>{q.get(f'precision@{kk}', 0.0):.3f}</td>")
            parts.append(f"<td class='num'>{q.get(f'ndcg@{kk}', 0.0):.3f}</td>")
        parts.append(f"<td class='num'>{q.get('mrr', 0.0):.3f}</td>")
        ctx_key = f"context_precision@{meta['k']}"
        parts.append(f"<td class='num'>{q.get(ctx_key, 0.0):.3f}</td></tr>")
    parts.append("</tbody></table>")

    # Per-query drilldown for the leading pipeline
    per_query = report.get("per_query") or {}
    if report["leaderboard"] and per_query:
        top = report["leaderboard"][0]
        drill = per_query.get(top["pipeline"], {})
        if drill:
            parts.append(f"<h2>Per-query drilldown &mdash; {escape(top['label'])}</h2>")
            parts.append("<table><thead><tr><th>Category</th><th>Query</th>"
                         "<th class='num'>Hit</th><th>Ranked chunk ids</th>"
                         "<th>Relevant</th></tr></thead><tbody>")
            for query, detail in drill.items():
                cls = "hit" if detail.get("hit_at_k") else "miss"
                mark = "yes" if detail.get("hit_at_k") else "no"
                parts.append(
                    "<tr><td>{cat}</td><td>{q}</td><td class='num {cls}'>{mark}</td>"
                    "<td><code>{ranked}</code></td><td><code>{rel}</code></td></tr>".format(
                        cat=escape(str(detail.get("category", ""))),
                        q=escape(str(query)),
                        cls=cls, mark=mark,
                        ranked=escape(", ".join(detail.get("ranked", [])) or "-"),
                        rel=escape(", ".join(detail.get("relevant", [])) or "-"),
                    )
                )
            parts.append("</tbody></table>")

    parts.append(
        "<div class='foot'>Reranker pairs are measured through a counting proxy; "
        "query embedding passes and USD cost are estimates derived from the pipeline "
        "specification (indexing cost excluded). Latency percentiles are computed "
        "from the timed run itself.</div>")
    parts.append("</body>\n</html>")
    return "\n".join(parts)



# -------------------------------------------------------------- query builders
def build_arena_queries_from_test_cases(test_cases) -> List[ArenaQuery]:
    """Convert robustness test cases (or compatible objects) into arena queries."""
    arena_queries: List[ArenaQuery] = []
    for case in test_cases:
        arena_queries.append(
            ArenaQuery(
                query=case.query,
                relevant_chunks=set(case.relevant_chunks),
                category=case.category,
                description=getattr(case, "description", ""),
            )
        )
    return arena_queries


def build_self_labeled_queries(
    corpus_texts: Dict[str, str],
    max_queries: int = 10,
    max_terms: int = 6,
) -> List[ArenaQuery]:
    """Derive labeled queries heuristically from the indexed corpus.

    Each chunk yields one query built from its most significant terms and is
    labeled with its own chunk id. This is a smoke benchmark for the live
    dashboard - use explicit labeled queries for rigorous evaluation.
    """
    queries: List[ArenaQuery] = []
    for chunk_id in sorted(corpus_texts):
        text = corpus_texts.get(chunk_id) or ""
        terms: List[str] = []
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-\.]*", text):
            lowered = token.lower()
            if lowered in _STOPWORDS or len(lowered) < 4:
                continue
            if lowered not in terms:
                terms.append(lowered)
            if len(terms) >= max_terms:
                break
        if len(terms) < 2:
            continue
        queries.append(
            ArenaQuery(
                query=" ".join(terms),
                relevant_chunks={chunk_id},
                category="self_labeled",
                description=f"Auto-labeled probe for chunk {chunk_id}",
            )
        )
        if len(queries) >= max_queries:
            break
    return queries

