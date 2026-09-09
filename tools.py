"""
tools.py — deterministic, non-LLM building blocks: Semantic Scholar search,
established/recent bucketing, and source content retrieval (HTML + PDF).

No LLM is used anywhere in this file. Ranking and bucketing are plain
arithmetic on metadata returned by the Semantic Scholar Graph API.
"""

import io
import os
import re
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

S2_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")  # optional — works fine unset
S2_BASE = "https://api.semanticscholar.org/graph/v1"

# Recent-bucket window, per locked design: under 1.5 years old.
RECENT_WINDOW_DAYS = int(1.5 * 365)

# Bonus added to citation count for established-bucket ranking when a paper's
# venue matches a known top-tier list. Same idea as the earlier credibility_score.
TOP_TIER_VENUES = {
    "nature", "science", "neurips", "icml", "acl", "nejm", "cell", "pnas",
    "ieee", "acm", "lancet", "jama",
}
VENUE_BONUS = 20

PAPER_FIELDS = ",".join([
    "paperId", "title", "abstract", "authors", "year", "venue",
    "citationCount", "externalIds", "openAccessPdf", "publicationTypes",
    "fieldsOfStudy", "publicationDate", "url",
])


def _s2_headers():
    headers = {"Accept": "application/json"}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    return headers


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _s2_get(path: str, params: dict) -> dict:
    resp = requests.get(f"{S2_BASE}/{path}", headers=_s2_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _venue_bonus(venue: str) -> int:
    if not venue:
        return 0
    v = venue.lower()
    return VENUE_BONUS if any(tier in v for tier in TOP_TIER_VENUES) else 0


def _credibility_score(paper: dict) -> float:
    return (paper.get("citationCount") or 0) + _venue_bonus(paper.get("venue") or "")


def _publication_date(paper: dict):
    raw = paper.get("publicationDate")
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    year = paper.get("year")
    if year:
        return date(year, 1, 1)
    return None


def _is_recent(paper: dict, cutoff: date) -> bool:
    pub_date = _publication_date(paper)
    return pub_date is not None and pub_date >= cutoff


def search_established(topic: str, k: int, exclude_ids: set, cutoff: date) -> list:
    """Bulk-search endpoint, sorted server-side by citation count. Excludes
    anything younger than `cutoff` and anything already claimed by the
    recent bucket."""
    if k <= 0:
        return []
    params = {
        "query": topic,
        "fields": PAPER_FIELDS,
        "sort": "citationCount:desc",
        "limit": min(100, max(k * 4, 20)),  # pull a wider pool to rank/filter from
    }
    data = _s2_get("paper/search/bulk", params)
    candidates = data.get("data", []) or []

    established = []
    for p in candidates:
        if p.get("paperId") in exclude_ids:
            continue
        if _is_recent(p, cutoff):
            continue  # belongs in the recent bucket, not here
        established.append(p)

    established.sort(key=_credibility_score, reverse=True)
    return established[:k]


def search_recent(topic: str, k: int, cutoff: date) -> list:
    """Regular relevance-search endpoint (not bulk) — bulk search has no
    relevance sort, only paperId/citationCount/publicationDate. This endpoint
    returns results in S2's default relevance order, which is what the
    'recent' bucket is meant to rank by."""
    if k <= 0:
        return []
    year_floor = cutoff.year
    params = {
        "query": topic,
        "fields": PAPER_FIELDS,
        "year": f"{year_floor}-",
        "limit": min(100, max(k * 4, 20)),
    }
    data = _s2_get("paper/search", params)
    candidates = data.get("data", []) or []

    recent = [p for p in candidates if _is_recent(p, cutoff)]
    # relevance order is whatever S2 already returned it in — just truncate
    return recent[:k]


def search_papers_bucketed(topic: str, k: int = 10, recent_fraction: float = 0.4) -> dict:
    """Deterministic, non-LLM search + bucketing.

    Returns {"recent": [...], "established": [...]} — each item is the raw
    Semantic Scholar paper dict plus a "_bucket" key. No overlap between the
    two lists. Established list excludes anything in the recent list.
    """
    k_recent = max(0, round(k * recent_fraction))
    k_established = max(0, k - k_recent)

    cutoff = date.today() - timedelta(days=RECENT_WINDOW_DAYS)

    recent = search_recent(topic, k_recent, cutoff)
    recent_ids = {p.get("paperId") for p in recent if p.get("paperId")}

    established = search_established(topic, k_established, recent_ids, cutoff)

    for p in recent:
        p["_bucket"] = "recent"
    for p in established:
        p["_bucket"] = "established"

    return {"recent": recent, "established": established}


def citations_per_year(paper: dict) -> float:
    pub_date = _publication_date(paper)
    if not pub_date:
        return 0.0
    age_years = max((date.today() - pub_date).days / 365.0, 1 / 365.0)
    return round((paper.get("citationCount") or 0) / age_years, 2)


def clean_abstract(abstract, max_chars: int = 900) -> str:
    """Whitespace-normalize and sentence-safe truncate. Never returns raw
    unbounded text."""
    if not abstract:
        return "No abstract available."
    text = re.sub(r"\s+", " ", abstract).strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(". ")
    if last_period > max_chars * 0.5:
        truncated = truncated[: last_period + 1]
    return truncated + " […]"


def format_authors(authors) -> str:
    if not authors:
        return "Unknown authors"
    names = [a.get("name", "") for a in authors if a.get("name")]
    if len(names) <= 3:
        return ", ".join(names)
    return ", ".join(names[:3]) + " et al."


def review_metadata(paper: dict) -> dict:
    """Everything the review card needs, pre-computed and clean — no raw
    full text, ever, at this stage."""
    is_open = bool((paper.get("openAccessPdf") or {}).get("url"))
    fields = paper.get("fieldsOfStudy") or []
    return {
        "paper_id": paper.get("paperId"),
        "title": paper.get("title") or "Untitled",
        "authors": format_authors(paper.get("authors")),
        "venue": paper.get("venue") or "Unknown venue",
        "year": paper.get("year"),
        "citation_count": paper.get("citationCount") or 0,
        "citations_per_year": citations_per_year(paper) if paper.get("_bucket") == "recent" else None,
        "is_open_access": is_open,
        "field_of_study": fields[0] if fields else None,
        "bucket": paper.get("_bucket"),
        "abstract": clean_abstract(paper.get("abstract")),
        "url": paper.get("url"),
        "pdf_url": (paper.get("openAccessPdf") or {}).get("url"),
    }


# ── Full-text retrieval (used only after a paper is accepted, for report generation) ──

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _fetch(url: str):
    return requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})


def _extract_pdf_text(content: bytes, max_chars: int = 12000) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "PDF text extraction unavailable (pypdf not installed)."

    try:
        reader = PdfReader(io.BytesIO(content))
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] if text else "PDF contained no extractable text."
    except Exception as e:
        return f"Could not parse PDF: {e}"


def _extract_html_text(html: str, max_chars: int = 12000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:max_chars] if text else "Scraped page contained no readable text."


def fetch_full_text(paper_meta: dict) -> dict:
    """For an ACCEPTED paper only. Returns
    {"is_open_access": bool, "content": str, "content_type": "pdf"|"html"|"abstract"}.

    Open-access -> tries the PDF first, falls back to the S2 landing page HTML.
    Closed -> just returns the abstract; caller is responsible for the
    "report will be based on abstract only" confirmation before using this.
    """
    if not paper_meta["is_open_access"]:
        return {
            "is_open_access": False,
            "content": paper_meta["abstract"],
            "content_type": "abstract",
        }

    pdf_url = paper_meta.get("pdf_url")
    if pdf_url:
        try:
            resp = _fetch(pdf_url)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" in content_type.lower() or pdf_url.lower().endswith(".pdf"):
                text = _extract_pdf_text(resp.content)
                if text and "Could not parse PDF" not in text and "unavailable" not in text:
                    return {"is_open_access": True, "content": text, "content_type": "pdf"}
            else:
                text = _extract_html_text(resp.text)
                return {"is_open_access": True, "content": text, "content_type": "html"}
        except requests.RequestException:
            pass  # fall through to landing-page attempt below

    landing_url = paper_meta.get("url")
    if landing_url:
        try:
            resp = _fetch(landing_url)
            resp.raise_for_status()
            text = _extract_html_text(resp.text)
            return {"is_open_access": True, "content": text, "content_type": "html"}
        except requests.RequestException as e:
            return {
                "is_open_access": True,
                "content": paper_meta["abstract"],
                "content_type": "abstract",
                "note": f"Full text fetch failed ({e}); falling back to abstract.",
            }

    return {"is_open_access": True, "content": paper_meta["abstract"], "content_type": "abstract"}
