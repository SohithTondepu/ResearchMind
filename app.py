import time

import streamlit as st

from tools import review_metadata, search_papers_bucketed
from report_engine import generate_report_for_paper

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchMind · AI Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8e4dc;
}
.stApp {
    background: #0a0a0f;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(255,140,50,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(255,80,30,0.08) 0%, transparent 55%);
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1200px; }

.hero { text-align: center; padding: 3.5rem 0 2.5rem; position: relative; }
.hero-eyebrow {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 500;
    letter-spacing: 0.25em; text-transform: uppercase; color: #ff8c32;
    margin-bottom: 1rem; opacity: 0.9;
}
.hero h1 {
    font-family: 'Syne', sans-serif; font-size: clamp(2.8rem, 6vw, 5rem);
    font-weight: 800; line-height: 1.0; letter-spacing: -0.03em;
    color: #f0ebe0; margin: 0 0 1rem;
}
.hero h1 span { color: #ff8c32; }
.hero-sub {
    font-size: 1.05rem; font-weight: 300; color: #a09890;
    max-width: 560px; margin: 0 auto; line-height: 1.65;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,140,50,0.3), transparent);
    margin: 2rem 0;
}
.input-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,140,50,0.15);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 2rem;
    backdrop-filter: blur(8px);
}
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,140,50,0.25) !important;
    border-radius: 10px !important; color: #f0ebe0 !important;
    font-family: 'DM Sans', sans-serif !important; font-size: 1rem !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: #ff8c32 !important; box-shadow: 0 0 0 3px rgba(255,140,50,0.12) !important;
}
.stTextInput > label {
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important;
    letter-spacing: 0.15em !important; text-transform: uppercase !important;
    color: #ff8c32 !important; font-weight: 500 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #ff8c32 0%, #ff5a1a 100%) !important;
    color: #0a0a0f !important; font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important; font-size: 0.95rem !important; letter-spacing: 0.04em !important;
    border: none !important; border-radius: 10px !important; padding: 0.7rem 2.2rem !important;
    cursor: pointer !important; transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s !important;
    box-shadow: 0 4px 20px rgba(255,140,50,0.3) !important; width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) !important; box-shadow: 0 8px 28px rgba(255,140,50,0.4) !important;
    opacity: 0.95 !important;
}
.stButton > button:active { transform: translateY(0) !important; }

.step-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.5rem 1.8rem; margin-bottom: 1.2rem;
    position: relative; overflow: hidden; transition: border-color 0.3s;
}
.step-card.active { border-color: rgba(255,140,50,0.4); background: rgba(255,140,50,0.04); }
.step-card.done { border-color: rgba(80,200,120,0.3); background: rgba(80,200,120,0.03); }
.step-card.error { border-color: rgba(220,60,60,0.4); background: rgba(220,60,60,0.05); }
.step-card::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    border-radius: 14px 0 0 14px; background: rgba(255,255,255,0.05); transition: background 0.3s;
}
.step-card.active::before { background: #ff8c32; }
.step-card.done::before { background: #50c878; }
.step-card.error::before { background: #dc3c3c; }
.step-header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.3rem; }
.step-num {
    font-family: 'DM Mono', monospace; font-size: 0.68rem; font-weight: 500;
    letter-spacing: 0.15em; color: #ff8c32; opacity: 0.7;
}
.step-title { font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700; color: #f0ebe0; }
.step-status { margin-left: auto; font-family: 'DM Mono', monospace; font-size: 0.68rem; letter-spacing: 0.1em; }
.status-waiting { color: #555; }
.status-running { color: #ff8c32; }
.status-done { color: #50c878; }
.status-error { color: #dc3c3c; }

.result-panel {
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.8rem 2rem; margin-top: 1rem; margin-bottom: 1.5rem;
}
.result-panel-title {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 500;
    letter-spacing: 0.2em; text-transform: uppercase; color: #ff8c32;
    margin-bottom: 1rem; padding-bottom: 0.7rem; border-bottom: 1px solid rgba(255,140,50,0.15);
}
.result-content {
    font-size: 0.92rem; line-height: 1.8; color: #cdc8bf;
    white-space: pre-wrap; font-family: 'DM Sans', sans-serif;
}
.report-panel {
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,140,50,0.2);
    border-radius: 16px; padding: 2rem 2.5rem; margin-top: 1rem;
}
.feedback-panel {
    background: rgba(255,255,255,0.025); border: 1px solid rgba(80,200,120,0.2);
    border-radius: 16px; padding: 2rem 2.5rem; margin-top: 1rem;
}
.panel-label {
    font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em;
    text-transform: uppercase; margin-bottom: 1.2rem; padding-bottom: 0.7rem;
}
.panel-label.orange { color: #ff8c32; border-bottom: 1px solid rgba(255,140,50,0.15); }
.panel-label.green { color: #50c878; border-bottom: 1px solid rgba(80,200,120,0.15); }
.stSpinner > div { color: #ff8c32 !important; }
details summary {
    font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important;
    color: #a09890 !important; letter-spacing: 0.1em !important; cursor: pointer;
}
.section-heading { font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 700; color: #f0ebe0; margin: 2rem 0 1rem; }
.notice {
    font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #605850;
    text-align: center; margin-top: 3rem; letter-spacing: 0.08em;
}
.error-box {
    font-family: 'DM Mono', monospace; font-size: 0.8rem; color: #ff9e9e;
    background: rgba(220,60,60,0.08); border: 1px solid rgba(220,60,60,0.25);
    border-radius: 10px; padding: 1rem 1.2rem; margin-top: 1rem;
}
.warn-box {
    font-family: 'DM Mono', monospace; font-size: 0.8rem; color: #ffcf9e;
    background: rgba(255,140,50,0.08); border: 1px solid rgba(255,140,50,0.25);
    border-radius: 10px; padding: 1rem 1.2rem; margin-top: 1rem;
}
.bucket-tag {
    display: inline-block; font-family: 'DM Mono', monospace; font-size: 0.62rem;
    letter-spacing: 0.12em; text-transform: uppercase; padding: 0.15rem 0.55rem;
    border-radius: 5px; margin-left: 0.6rem; vertical-align: middle;
}
.bucket-tag.established { background: rgba(255,140,50,0.12); color: #ff8c32; }
.bucket-tag.recent { background: rgba(80,200,120,0.12); color: #50c878; }
.lock-tag {
    display: inline-block; font-family: 'DM Mono', monospace; font-size: 0.62rem;
    letter-spacing: 0.1em; padding: 0.15rem 0.55rem; border-radius: 5px;
    background: rgba(220,60,60,0.1); color: #ff9e9e; margin-left: 0.6rem; vertical-align: middle;
}
.meta-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem 1.5rem;
    font-size: 0.82rem; color: #cdc8bf; margin: 0.8rem 0 1rem;
}
.meta-grid b { color: #f0ebe0; }
</style>
""", unsafe_allow_html=True)

STEPS = ["search", "review", "reports"]


# ── Helper: render a step card ────────────────────────────────────────────────
def step_card(num: str, title: str, state: str, desc: str = ""):
    status_map = {
        "waiting": ("WAITING", "status-waiting"),
        "running": ("● RUNNING", "status-running"),
        "done": ("✓ DONE", "status-done"),
        "error": ("✕ ERROR", "status-error"),
    }
    label, cls = status_map.get(state, ("", ""))
    card_cls = {"running": "active", "done": "done", "error": "error"}.get(state, "")
    st.markdown(f"""
    <div class="step-card {card_cls}">
        <div class="step-header">
            <span class="step-num">{num}</span>
            <span class="step-title">{title}</span>
            <span class="step-status {cls}">{label}</span>
        </div>
        {"<div style='font-size:0.82rem;color:#706860;margin-top:0.3rem;'>"+desc+"</div>" if desc else ""}
    </div>
    """, unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
defaults = {
    "running": False,
    "done": False,
    "error": None,
    "current_topic": "",
    "k": 10,
    "recent_pct": 40,
    "candidates": None,     # ordered list of review_metadata dicts (established, then recent)
    "review_index": 0,      # which candidate is currently being reviewed
    "decisions": {},        # paper_id -> "accepted" | "rejected"
    "review_done": False,
    "accepted": [],         # list of accepted review_metadata dicts, in review order
    "report_gen_index": 0,  # which accepted paper we're generating a report for
    "reports": [],          # list of generate_report_for_paper() results, in completion order
    "pending_abstract_confirm": False,  # True while waiting on the abstract-only warning confirm
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Semantic Scholar · Gemini</div>
    <h1>Research<span>Mind</span></h1>
    <p class="hero-sub">
        Deterministic credibility-ranked search across established and recent
        papers, human-reviewed one at a time, with an independent AI-written
        and AI-critiqued report generated for every source you accept.
    </p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

# ── Layout: input left, pipeline right ───────────────────────────────────────
col_input, col_spacer, col_pipeline = st.columns([5, 0.5, 4])

with col_input:
    with st.container(border=True):
        topic = st.text_input(
            "Research Topic",
            placeholder="e.g. Quantum computing breakthroughs in 2025",
            key="topic_input",
            label_visibility="visible",
        )
        k_input = st.number_input(
            "Total candidates (K, max 10)",
            min_value=1, max_value=10, value=st.session_state.k, step=1,
            help="Total number of papers to retrieve and review, split between "
                 "the established and recent buckets below.",
        )
        recent_pct_input = st.slider(
            "Recent-bucket share",
            min_value=0, max_value=100, value=st.session_state.recent_pct, step=10,
            help="% of K reserved for recent papers (under 1.5 years old, ranked by "
                 "relevance). The rest is the established bucket (ranked by citations).",
            format="%d%%",
        )
        run_btn = st.button("⚡ Run Research Pipeline", use_container_width=True)

    st.markdown("""
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1.5rem;">
    <span style="font-family:'DM Mono',monospace;font-size:0.68rem;color:#605850;letter-spacing:0.1em;">TRY →</span>
    """, unsafe_allow_html=True)
    examples = ["LLM agents 2025", "CRISPR gene editing", "Fusion energy progress"]
    for ex in examples:
        st.markdown(f"""
        <span style="
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.08);
            border-radius:6px;
            padding:0.25rem 0.7rem;
            font-size:0.75rem;
            color:#a09890;
            font-family:'DM Sans',sans-serif;
            cursor:default;
        ">{ex}</span>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_pipeline:
    st.markdown('<div class="section-heading">Pipeline</div>', unsafe_allow_html=True)

    def step_state(step: str) -> str:
        if st.session_state.error and st.session_state.error[0] == step:
            return "error"
        if step == "search":
            if st.session_state.candidates is not None:
                return "done"
            return "running" if st.session_state.running else "waiting"
        if step == "review":
            if st.session_state.review_done:
                return "done"
            if st.session_state.candidates is not None:
                return "running"
            return "waiting"
        if step == "reports":
            if st.session_state.review_done and st.session_state.accepted:
                if st.session_state.report_gen_index >= len(st.session_state.accepted):
                    return "done"
                return "running"
            if st.session_state.review_done and not st.session_state.accepted:
                return "done"
            return "waiting"
        return "waiting"

    step_card("01", "Search & Bucket", step_state("search"),
               "Semantic Scholar, deterministic — established vs. recent")
    step_card("02", "Human Review", step_state("review"),
               "You review every candidate; accept as many as you like")
    step_card("03", "Report Generation", step_state("reports"),
               "One independent Writer+Critic report per accepted paper")

# ── Kick off a new run ────────────────────────────────────────────────────────
if run_btn:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        st.session_state.running = True
        st.session_state.done = False
        st.session_state.error = None
        st.session_state.current_topic = topic
        st.session_state.k = int(k_input)
        st.session_state.recent_pct = int(recent_pct_input)
        st.session_state.candidates = None
        st.session_state.review_index = 0
        st.session_state.decisions = {}
        st.session_state.review_done = False
        st.session_state.accepted = []
        st.session_state.report_gen_index = 0
        st.session_state.reports = []
        st.session_state.pending_abstract_confirm = False
        st.rerun()

# ── Step-machine ────────────────────────────────────────────────────────────
# One atomic action per script rerun, same live-update pattern as before.
if st.session_state.running and not st.session_state.error:
    topic_val = st.session_state.current_topic

    try:
        # Step 1 — Search & bucket (deterministic, no LLM), runs once.
        if st.session_state.candidates is None:
            with st.spinner(f"🔍 Searching Semantic Scholar for the top {st.session_state.k} candidates…"):
                buckets = search_papers_bucketed(
                    topic_val,
                    k=st.session_state.k,
                    recent_fraction=st.session_state.recent_pct / 100,
                )
                established = [review_metadata(p) for p in buckets["established"]]
                recent = [review_metadata(p) for p in buckets["recent"]]
                # Established shown/reviewed first, then recent.
                st.session_state.candidates = established + recent
            st.rerun()

        # Step 2 handled entirely by the review UI block below (needs button
        # clicks, so it can't auto-advance inside this try block).

        # Step 3 — Report generation: one paper per rerun, so each finished
        # report renders immediately instead of waiting for all of them.
        elif st.session_state.review_done and st.session_state.accepted:
            idx = st.session_state.report_gen_index
            if idx < len(st.session_state.accepted):
                meta = st.session_state.accepted[idx]

                # Closed-access papers need an explicit confirm before we
                # spend a generation on an abstract-only report.
                if not meta["is_open_access"] and not st.session_state.pending_abstract_confirm:
                    st.session_state.pending_abstract_confirm = True
                    st.rerun()
                elif not meta["is_open_access"] and st.session_state.pending_abstract_confirm:
                    pass  # waiting on the confirm buttons rendered below
                else:
                    with st.spinner(f"✍️ Generating report {idx + 1}/{len(st.session_state.accepted)}: {meta['title'][:60]}…"):
                        result = generate_report_for_paper(topic_val, meta)
                        st.session_state.reports.append(result)
                    st.session_state.report_gen_index += 1
                    st.rerun()
            else:
                st.session_state.running = False
                st.session_state.done = True
                st.rerun()

    except Exception as e:
        if st.session_state.candidates is None:
            failed_step = "search"
        elif not st.session_state.review_done:
            failed_step = "review"
        else:
            failed_step = "reports"
        st.session_state.error = (failed_step, str(e))
        st.session_state.running = False
        st.rerun()

# ── Human review loop: walk every candidate, never stop early ────────────────
if (
    st.session_state.running
    and st.session_state.candidates is not None
    and not st.session_state.review_done
):
    idx = st.session_state.review_index
    candidates = st.session_state.candidates

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if idx >= len(candidates):
        st.session_state.review_done = True
        st.rerun()
    else:
        c = candidates[idx]
        bucket_cls = "established" if c["bucket"] == "established" else "recent"
        lock_html = '<span class="lock-tag">🔒 abstract only</span>' if not c["is_open_access"] else ""
        cite_line = f"{c['citation_count']} citations"
        if c["citations_per_year"] is not None:
            cite_line += f" &nbsp;·&nbsp; {c['citations_per_year']}/year"

        st.markdown(f"""
        <div class="result-panel">
            <div class="result-panel-title">
                📄 Candidate {idx + 1}/{len(candidates)}
                <span class="bucket-tag {bucket_cls}">{c['bucket']}</span>
                {lock_html}
            </div>
            <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#f0ebe0;margin-bottom:0.5rem;">
                {c['title']}
            </div>
            <div class="meta-grid">
                <div><b>Authors:</b> {c['authors']}</div>
                <div><b>Venue/Year:</b> {c['venue']} ({c['year'] or '—'})</div>
                <div><b>Citations:</b> {cite_line}</div>
                <div><b>Field:</b> {c['field_of_study'] or '—'}</div>
            </div>
            <div class="result-content">{c['abstract']}</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Satisfied — accept this source", use_container_width=True, key=f"accept_{idx}"):
                st.session_state.decisions[c["paper_id"]] = "accepted"
                st.session_state.accepted.append(c)
                st.session_state.review_index += 1
                st.rerun()
        with c2:
            has_more = idx + 1 < len(candidates)
            if st.button(
                "➡️ Reject — next candidate" if has_more else "➡️ Reject — that was the last one",
                use_container_width=True, key=f"reject_{idx}",
            ):
                st.session_state.decisions[c["paper_id"]] = "rejected"
                st.session_state.review_index += 1
                st.rerun()

# ── Abstract-only confirm gate (before spending a generation on a closed paper) ──
if st.session_state.pending_abstract_confirm and st.session_state.report_gen_index < len(st.session_state.accepted):
    meta = st.session_state.accepted[st.session_state.report_gen_index]
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="warn-box">
        ⚠ "<b>{meta['title']}</b>" doesn't have full text available —
        the report will be based on the abstract only, and won't get a numeric
        critic score (a single abstract-only review pass instead of two full-text passes).
    </div>
    """, unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("Proceed with abstract-only report", use_container_width=True):
            st.session_state.pending_abstract_confirm = False
            st.rerun()
    with cc2:
        if st.button("Skip this paper", use_container_width=True):
            st.session_state.pending_abstract_confirm = False
            st.session_state.report_gen_index += 1
            st.rerun()

# ── Error display ──────────────────────────────────────────────────────────────
if st.session_state.error:
    step_name, msg = st.session_state.error
    st.markdown(f"""
    <div class="error-box">
        ⚠ The <b>{step_name}</b> step failed: {msg}<br>
        Check your API keys (GOOGLE_API_KEY, optionally SEMANTIC_SCHOLAR_API_KEY) and network access, then try again.
    </div>
    """, unsafe_allow_html=True)
    if st.button("Reset"):
        for key, val in defaults.items():
            st.session_state[key] = val
        st.rerun()

# ── Results: every accepted paper's report, shown as soon as it's ready ──────
if st.session_state.reports:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Reports</div>', unsafe_allow_html=True)

    for i, result in enumerate(st.session_state.reports):
        access_tag = "Open access — full text" if result["is_open_access"] and not result["used_abstract_only"] else "Abstract only"
        with st.expander(f"📄 Report {i + 1}: {result['title']}  ·  {access_tag}", expanded=(i == 0)):
            for p_idx, p in enumerate(result["passes"]):
                pass_label = f"Pass {p_idx + 1}"
                with st.container(border=True):
                    st.markdown(f'<div class="panel-label orange">📝 {pass_label} — Report</div>', unsafe_allow_html=True)
                    st.markdown(p["report"])
                with st.container(border=True):
                    st.markdown(f'<div class="panel-label green">🧐 {pass_label} — Critic Feedback</div>', unsafe_allow_html=True)
                    st.markdown(p["critique"])

            st.download_button(
                label="⬇ Download Final Report (.md)",
                data=result["final_report"],
                file_name=f"report_{i+1}_{int(time.time())}.md",
                mime="text/markdown",
                key=f"dl_{i}",
            )

    if st.session_state.done:
        st.success(f"Done — generated {len(st.session_state.reports)} report(s) from "
                    f"{len(st.session_state.accepted)} accepted source(s).")
elif st.session_state.review_done and not st.session_state.accepted:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.info("No candidates were marked satisfactory — nothing to generate. Adjust K or the topic and run again.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="notice">
    ResearchMind · Semantic Scholar search · Gemini Writer/Critic chains · Built with Streamlit
</div>
""", unsafe_allow_html=True)
