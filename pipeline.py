"""
pipeline.py — CLI mirror of app.py's flow:
  1. search + bucket (established, then recent)
  2. review every candidate one at a time (satisfied / reject), never stops early
  3. once review is done, generate a report for every "satisfied" paper,
     sequentially, printing each as it finishes
"""

from tools import review_metadata, search_papers_bucketed
from report_engine import generate_report_for_paper


def review_candidates(candidates: list) -> list:
    """Walks the full candidate list, one at a time. Returns the list of
    accepted (satisfied) review_metadata dicts. Never stops early."""
    accepted = []
    for idx, paper in enumerate(candidates):
        meta = review_metadata(paper)
        print("\n" + "=" * 60)
        print(f"[{idx + 1}/{len(candidates)}] ({meta['bucket']}) {meta['title']}")
        print("=" * 60)
        print(f"Authors: {meta['authors']}")
        print(f"Venue/Year: {meta['venue']} ({meta['year']})")
        cite_line = f"Citations: {meta['citation_count']}"
        if meta["citations_per_year"] is not None:
            cite_line += f"  (citations/year: {meta['citations_per_year']})"
        print(cite_line)
        print(f"Open access: {'yes' if meta['is_open_access'] else 'no — 🔒 abstract only'}")
        if meta["field_of_study"]:
            print(f"Field: {meta['field_of_study']}")
        print(f"\nAbstract:\n{meta['abstract']}")

        ans = input("\nSatisfied with this source? (y = accept it / n = next): ").strip().lower()
        if ans == "y":
            accepted.append(meta)
            print("-> accepted.")
        else:
            print("-> rejected, moving to next.")

    return accepted


def generate_all_reports(topic: str, accepted: list) -> list:
    """Sequential generation, one report at a time, printed as it completes."""
    results = []
    for idx, meta in enumerate(accepted):
        print("\n" + "#" * 60)
        print(f"Generating report {idx + 1}/{len(accepted)}: {meta['title']}")
        print("#" * 60)

        if not meta["is_open_access"]:
            print("\n⚠ This paper doesn't have full text available — "
                  "the report will be based on the abstract only.")
            confirm = input("Proceed anyway? (y/n): ").strip().lower()
            if confirm != "y":
                print("-> skipped.")
                continue

        result = generate_report_for_paper(topic, meta)
        results.append(result)

        print(f"\n--- Final Report ({meta['title']}) ---\n")
        print(result["final_report"])
        print(f"\n--- Final Critic Feedback ---\n")
        print(result["final_critique"])
        if result["used_abstract_only"]:
            print("\n(Note: this report was generated from the abstract only — "
                  "no numeric score, single review pass.)")

    return results


def run_research_pipeline(topic: str, k: int = 10, recent_fraction: float = 0.4) -> dict:
    state = {}
    try:
        print("\nSearching Semantic Scholar and bucketing results...")
        buckets = search_papers_bucketed(topic, k=k, recent_fraction=recent_fraction)
        # Established shown/reviewed first, then recent.
        ordered_candidates = buckets["established"] + buckets["recent"]

        if not ordered_candidates:
            print("No candidates found for this topic.")
            return state

        accepted = review_candidates(ordered_candidates)
        state["accepted"] = accepted

        if not accepted:
            print("\nNo sources were marked satisfactory — nothing to generate.")
            return state

        state["reports"] = generate_all_reports(topic, accepted)

    except Exception as e:
        print(f"\nPipeline failed: {e}")
        state["error"] = str(e)

    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ")
    if not topic.strip():
        print("No topic entered, exiting.")
    else:
        k_raw = input("How many total candidates to consider (max 10, default 10): ").strip()
        k = int(k_raw) if k_raw.isdigit() else 10
        k = min(k, 10)
        run_research_pipeline(topic, k=k)
