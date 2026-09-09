"""
report_engine.py — orchestrates the per-paper report generation pipeline,
shared by app.py (Streamlit) and pipeline.py (CLI) so the two don't drift.

This is the one place with any "agentic" shape in the project: a fixed,
bounded multi-pass loop (never open-ended, never picks its own step count
or tools). Everything upstream of this (search, bucketing, scraping,
human review) is plain deterministic code with no LLM involvement.
"""

from agents import critic_chain_deep, critic_chain_light, writer_chain, writer_revision_chain
from tools import fetch_full_text

OPEN_ACCESS_PASSES = 2  # fixed, not score-gated
CLOSED_PASSES = 1       # fixed, no numeric score


def _format_metadata(meta: dict) -> str:
    lines = [
        f"Title: {meta['title']}",
        f"Authors: {meta['authors']}",
        f"Venue: {meta['venue']} ({meta['year']})",
        f"Citations: {meta['citation_count']}",
    ]
    if meta.get("citations_per_year") is not None:
        lines.append(f"Citations/year: {meta['citations_per_year']}")
    lines.append(f"Open access: {'yes' if meta['is_open_access'] else 'no'}")
    if meta.get("field_of_study"):
        lines.append(f"Field: {meta['field_of_study']}")
    return "\n".join(lines)


def generate_report_for_paper(topic: str, paper_meta: dict) -> dict:
    """Runs the full report pipeline for ONE accepted paper.

    Returns:
    {
        "paper_id": ...,
        "title": ...,
        "is_open_access": bool,
        "content_type": "pdf" | "html" | "abstract",
        "passes": [{"report": str, "critique": str, "score": str|None}, ...],
        "final_report": str,
        "final_critique": str,
        "final_score": str | None,
        "used_abstract_only": bool,
    }
    """
    fetched = fetch_full_text(paper_meta)
    source_text = fetched["content"]
    content_type = fetched["content_type"]
    used_abstract_only = content_type == "abstract"

    metadata_block = _format_metadata(paper_meta)
    passes = []

    if paper_meta["is_open_access"] and not used_abstract_only:
        # ── Deep path: 2 fixed passes, scored, full-text faithfulness check ──
        report_v1 = writer_chain.invoke({
            "topic": topic,
            "metadata": metadata_block,
            "source_type": content_type,
            "research": source_text,
        })
        critique_v1 = critic_chain_deep.invoke({
            "metadata": metadata_block,
            "source": source_text,
            "report": report_v1,
        })
        passes.append({"report": report_v1, "critique": critique_v1})

        report_v2 = writer_revision_chain.invoke({
            "topic": topic,
            "metadata": metadata_block,
            "source_type": content_type,
            "research": source_text,
            "previous_report": report_v1,
            "critic_feedback": critique_v1,
        })
        critique_v2 = critic_chain_deep.invoke({
            "metadata": metadata_block,
            "source": source_text,
            "report": report_v2,
        })
        passes.append({"report": report_v2, "critique": critique_v2})

        final_report = report_v2
        final_critique = critique_v2

    else:
        # ── Light path: 1 pass, no score, abstract-only faithfulness check ──
        report_v1 = writer_chain.invoke({
            "topic": topic,
            "metadata": metadata_block,
            "source_type": "abstract",
            "research": paper_meta["abstract"],
        })
        critique_v1 = critic_chain_light.invoke({
            "metadata": metadata_block,
            "source": paper_meta["abstract"],
            "report": report_v1,
        })
        passes.append({"report": report_v1, "critique": critique_v1})

        final_report = report_v1
        final_critique = critique_v1

    return {
        "paper_id": paper_meta["paper_id"],
        "title": paper_meta["title"],
        "is_open_access": paper_meta["is_open_access"],
        "content_type": content_type,
        "used_abstract_only": used_abstract_only,
        "passes": passes,
        "final_report": final_report,
        "final_critique": final_critique,
    }
