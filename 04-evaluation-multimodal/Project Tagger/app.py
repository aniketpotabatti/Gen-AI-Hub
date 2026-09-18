"""Streamlit web app for multimodal product tagging.

Tabs:
  1. Tag Single   - upload image + description -> validated JSON tags.
  2. Batch Tag    - upload CSV/JSONL -> tag all -> preview + download JSONL.
  3. Evaluate     - predictions vs ground-truth JSONL -> metric report.

Run from this folder:
    streamlit run app.py
Enter the provider's API key in the sidebar (only for cloud providers).
"""

import io
import json
import logging
import sys
import tempfile
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.evaluation import align_records, evaluate  # noqa: E402
from src.pipeline.tagging_pipeline import TaggingPipeline  # noqa: E402
from src.prompts.loader import load_few_shot_examples  # noqa: E402
from src.schemas.product import ProductInput  # noqa: E402
from src.tagger.factory import available_providers, create_tagger  # noqa: E402

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Product Tagger", page_icon="🏷️", layout="wide")
st.title("🏷️ Multimodal Product Tagger")
st.caption("Image + description → validated JSON tags (Gemini, GPT-4o, Claude, local LLaVA).")

with st.sidebar:
    st.header("⚙️ Model settings")
    provider = st.selectbox("Provider", options=available_providers(), index=0)
    api_key = st.text_input(
        f"{provider.capitalize()} API key",
        type="password",
        help="Only needed for cloud providers (Gemini / OpenAI / Anthropic). "
        "The 'local' provider (Ollama) needs no key.",
    )
    model_override = st.text_input("Model override (optional)", value="")
    use_few_shot = st.checkbox("Use few-shot examples", value=False)
    max_concurrency = st.slider("Batch concurrency", 1, 8, 4)
    st.divider()
    st.caption(
        "Enter the key for the selected provider only — one key is enough. "
        "Keys are kept in this browser session and never stored."
    )


@st.cache_resource(show_spinner=False)
def _get_tagger(provider_name: str, key: str, model_name: str, few_shot: bool):
    """Cache the tagger per config combo (avoids re-auth on every rerun)."""
    kwargs = {}
    if key.strip():
        kwargs["api_key"] = key.strip()
    if model_name.strip():
        kwargs["model"] = model_name.strip()
    if few_shot:
        kwargs["few_shot_examples"] = load_few_shot_examples()
    return create_tagger(provider=provider_name or None, **kwargs)


def _get_pipeline() -> TaggingPipeline | None:
    """Build a pipeline, or surface a missing-key / invalid-config error in the UI."""
    if provider != "local" and not api_key.strip():
        st.warning(f"⚠️ Enter your {provider.capitalize()} API key in the sidebar.")
        return None
    try:
        tagger = _get_tagger(provider, api_key, model_override, use_few_shot)
    except ValueError as exc:
        st.error(f"⚠️ {exc}")
        return None
    return TaggingPipeline(tagger=tagger, max_concurrency=max_concurrency)


def _format_tag_value(value) -> str:
    return ", ".join(value) if isinstance(value, list) else (value or "—")


def _render_tags(tags: dict | None) -> None:
    if not tags:
        st.warning("No tags returned.")
        return
    core, visual, audience = st.columns(3)
    with core:
        st.subheader("Core")
        for key in ("category", "subcategory", "brand"):
            st.metric(key, tags.get(key) or "—")
    with visual:
        st.subheader("Visual")
        for key in ("color", "material", "pattern", "style"):
            st.write(f"**{key}:** {_format_tag_value(tags.get(key))}")
    with audience:
        st.subheader("Audience & use")
        for key in ("gender", "age_group", "size", "usage_occasion", "is_waterproof"):
            st.write(f"**{key}:** {_format_tag_value(tags.get(key))}")
    with st.expander("Raw JSON"):
        st.json(tags)


def _parse_jsonl_upload(upload) -> list[dict]:
    if not upload:
        return []
    return [
        json.loads(line)
        for line in upload.getvalue().decode("utf-8").splitlines()
        if line.strip()
    ]


def _parse_batch_upload(batch_file) -> list[dict]:
    try:
        if Path(batch_file.name).suffix.lower() == ".csv":
            return pd.read_csv(io.BytesIO(batch_file.getvalue())).to_dict(orient="records")
        return _parse_jsonl_upload(batch_file)
    except Exception as exc:  # noqa: BLE001 - surfaced in the UI
        st.error(f"Could not parse input file: {exc}")
        return []


def _rows_to_products(rows: list[dict]) -> list[ProductInput]:
    products: list[ProductInput] = []
    skipped = 0
    for i, row in enumerate(rows):
        try:
            img = row.get("image") or row.get("image_path")
            products.append(
                ProductInput(
                    product_id=str(row.get("product_id", row.get("id", f"row-{i}"))),
                    image_path=Path(str(img)) if img else None,
                    image_base64=row.get("image_base64"),
                    description=row.get("description"),
                )
            )
        except ValueError as exc:
            skipped += 1
            st.warning(f"Skipping row {i}: {exc}")
    if skipped:
        st.info(f"Skipped {skipped} invalid rows.")
    return products


def _show_cost_summary(pipeline: TaggingPipeline) -> None:
    summary = pipeline.cost_summary()
    st.caption(
        f"Session: {summary['requests']} requests · "
        f"${summary['total_cost_usd']:.6f} total."
    )


def _show_eval_report(pred_records: list[dict], truth_records: list[dict]) -> None:
    preds, truths = align_records(pred_records, truth_records)
    report = evaluate(
        [r.get("tags", {}) or {} for r in preds],
        [r.get("tags", {}) or {} for r in truths],
        records=pred_records,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Exact-match ratio", f"{report['exact_match_ratio']:.2%}")
    m2.metric("Macro F1", f"{report['macro_f1']:.3f}")
    m3.metric("Hierarchical acc.", f"{report['hierarchical_accuracy_subcategory']:.2%}")
    attr_df = pd.DataFrame.from_dict(report["attributes"], orient="index")
    st.subheader("Per-attribute scores")
    st.dataframe(attr_df, use_container_width=True)
    st.bar_chart(attr_df["f1"])
    with st.expander("Full report JSON"):
        st.json(report)
    st.download_button(
        "⬇️ Download report (JSON)",
        data=json.dumps(report, indent=2),
        file_name="eval_report.json",
        mime="application/json",
    )


def _tag_single(uploaded, description: str, product_id: str) -> None:
    """Upload -> temp file -> tag -> render; cleanup always runs."""
    suffix = Path(uploaded.name).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = Path(tmp.name)
    try:
        with st.spinner(f"Tagging with {provider}…"):
            product = ProductInput(
                product_id=product_id or "product-001",
                image_path=tmp_path,
                description=description,
            )
            record = _get_pipeline().tag_one(product)
    except Exception as exc:  # noqa: BLE001 - surfaced in the UI
        logger.exception("Single-tag failed")
        st.error(f"Tagging failed: {exc}")
        with st.expander("Traceback"):
            st.code(traceback.format_exc())
        return
    finally:
        tmp_path.unlink(missing_ok=True)

    if record["error"]:
        st.error(f"Tagging failed: {record['error']}")
        return
    st.success(f"Tagged in {record['latency_s']}s")
    _render_tags(record["tags"])
    with st.expander("Usage"):
        st.json(record["usage"])
    st.download_button(
        "⬇️ Download result (JSON)",
        data=json.dumps(record, indent=2, default=str),
        file_name=f"{record['product_id']}_tags.json",
        mime="application/json",
    )


def _tag_batch(batch_file) -> None:
    pipeline = _get_pipeline()
    if pipeline is None:
        return
    products = _rows_to_products(_parse_batch_upload(batch_file))
    if not products:
        return
    with st.spinner(f"Tagging {len(products)} products…"):
        results = pipeline.tag_batch_sync(products)
    ok = sum(1 for r in results if r["error"] is None)
    st.success(f"Tagged {ok}/{len(results)} products.")
    st.dataframe(
        pd.DataFrame(
            {
                "product_id": r["product_id"],
                "category": (r["tags"] or {}).get("category"),
                "subcategory": (r["tags"] or {}).get("subcategory"),
                "error": r["error"],
                "latency_s": r["latency_s"],
            }
            for r in results
        ),
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Download results (JSONL)",
        data="\n".join(json.dumps(r, default=str) for r in results),
        file_name="tags.jsonl",
        mime="application/jsonl",
    )
    _show_cost_summary(pipeline)


tab_single, tab_batch, tab_eval = st.tabs(["Tag Single", "Batch Tag", "Evaluate"])

with tab_single:
    col_in, col_out = st.columns(2)
    with col_in:
        uploaded = st.file_uploader("Product image", type=["jpg", "jpeg", "png", "webp"])
        description = st.text_area("Description", value="Red cotton casual t-shirt for men")
        product_id = st.text_input("Product ID", value="product-001")
        if st.button("🏷️ Tag product", type="primary"):
            if not uploaded:
                st.warning("Please upload a product image first.")
            else:
                _tag_single(uploaded, description, product_id)
    with col_out:
        if uploaded:
            st.image(uploaded, caption="Input image", use_container_width=True)

with tab_batch:
    st.markdown("CSV columns: `product_id, image, description`. JSONL rows accept `image_base64`.")
    batch_file = st.file_uploader("Input file", type=["csv", "jsonl"])
    if st.button("🚀 Tag batch", type="primary"):
        if not batch_file:
            st.warning("Please upload a CSV or JSONL file first.")
        else:
            _tag_batch(batch_file)

with tab_eval:
    col_p, col_g = st.columns(2)
    with col_p:
        pred_file = st.file_uploader("Predictions JSONL", type=["jsonl"], key="preds")
    with col_g:
        truth_file = st.file_uploader("Ground-truth JSONL", type=["jsonl"], key="truths")
    if st.button("📄 Use sample ground truth for both"):
        sample = Path("data/input/sample_ground_truth.jsonl").read_text(encoding="utf-8")
        st.session_state["pred_records"] = [
            json.loads(line) for line in sample.splitlines() if line.strip()
        ]
        st.session_state["truth_records"] = st.session_state["pred_records"]
    if st.button("📊 Evaluate", type="primary"):
        pred_records = st.session_state.get("pred_records") or _parse_jsonl_upload(pred_file)
        truth_records = st.session_state.get("truth_records") or _parse_jsonl_upload(truth_file)
        if not pred_records or not truth_records:
            st.warning("Upload both files (or use the sample button) first.")
        else:
            _show_eval_report(pred_records, truth_records)


