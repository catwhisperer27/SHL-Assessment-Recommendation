"""
main.py — SHL Assessment Recommendation API v2.1

JSON format matches Appendix 2 of the assignment spec exactly:
  - GET  /healthy   → {"status": "healthy"}
  - POST /recommend → {"recommended_assessments": [{url, name, adaptive_support,
                        description, duration, remote_support, test_type}, ...]}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import uvicorn, re, requests, time
from rank_bm25 import BM25Okapi

load_dotenv()

from embedder import Embedder
from reranker import Reranker
from catalogue import ASSESSMENTS

app = FastAPI(title="SHL Assessment Recommendation API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────
ASSESSMENTS_FILTERED = [
    a for a in ASSESSMENTS if a.get("category") == "Individual Test Solutions"
]
print(f"[Startup] Individual Test Solutions: {len(ASSESSMENTS_FILTERED)}")

embedder = Embedder()
embedder.precompute(ASSESSMENTS_FILTERED)

def _bm25_doc(a):
    return f"{a.get('name','')} {' '.join(a.get('test_types',[]))} {a.get('description','')}".lower()

bm25_corpus = [_bm25_doc(a).split() for a in ASSESSMENTS_FILTERED]
bm25_index  = BM25Okapi(bm25_corpus)

def bm25_search(query: str, top_k: int = 50) -> list[dict]:
    scores = bm25_index.get_scores(query.lower().split())
    top    = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [{"assessment": ASSESSMENTS_FILTERED[i], "embed_score": float(scores[i])} for i in top]

reranker = Reranker(assessments=ASSESSMENTS_FILTERED)
print("[Startup] Ready")


# ── Schemas — match PDF Appendix 2 exactly ───────────────────────────────────

class RecommendRequest(BaseModel):
    query: str

# Each assessment object in the response — field names must match PDF exactly
class AssessmentOut(BaseModel):
    url:              str                # "Valid URL in string"
    name:             str                # "Name of the assessment"
    adaptive_support: str                # "Yes" or "No"
    description:      str                # "Detailed description"
    duration:         Optional[int]      # Integer minutes (null if unknown)
    remote_support:   str                # "Yes" or "No"
    test_type:        List[str]          # ["Knowledge & Skills"] — array of strings

# Top-level response wrapper
class RecommendResponse(BaseModel):
    recommended_assessments: List[AssessmentOut]


# ── URL fetching ──────────────────────────────────────────────────────────────

def is_url(text: str) -> bool:
    t = text.strip()
    return t.startswith("http://") or t.startswith("https://") or t.startswith("www.")

def fetch_jd_from_url(url: str) -> str:
    from bs4 import BeautifulSoup
    if url.startswith("www."):
        url = "https://" + url
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(400, f"URL timed out: {url}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(400, f"Could not connect to: {url}")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(400, f"URL returned error: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    main = (
        soup.find("main") or soup.find("article") or
        soup.find(class_=re.compile(r"job|description|content|posting", re.I)) or
        soup.find("body")
    )
    text = re.sub(r"\s+", " ", (main or soup).get_text(separator=" ", strip=True))
    if len(text) < 50:
        raise HTTPException(400, "Could not extract meaningful text from URL.")
    return text[:3000]


# ── RRF ───────────────────────────────────────────────────────────────────────

def rrf(rankings: list[list[dict]], k: int = 60) -> list[dict]:
    scores, items = {}, {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            url         = item["assessment"]["url"]
            scores[url] = scores.get(url, 0) + 1 / (k + rank + 1)
            items[url]  = item
    return [items[u] for u in sorted(scores, key=scores.get, reverse=True)]


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _recommend(query: str, top_k: int = 10) -> list[dict]:
    # Step 1: Injection (rules + semantic analysis)
    injected      = reranker.get_injected(query, bm25_search_fn=bm25_search)
    injected_urls = {c["assessment"]["url"] for c in injected}

    # Step 2: Hybrid retrieval + RRF
    vec_results  = embedder.score(query, ASSESSMENTS_FILTERED)[:50]
    bm25_results = bm25_search(query, top_k=50)
    fused        = rrf([vec_results, bm25_results])
    extra        = [c for c in fused if c["assessment"]["url"] not in injected_urls]
    candidates   = (injected + extra)[:25]

    # Step 3: LLM reranking
    try:
        results, _ = reranker.rerank(query, candidates, top_k=top_k)
    except RuntimeError:
        results = candidates[:top_k]

    # Step 4: Balance — ensure ≥1 personality test for mixed tech+soft queries
    q        = query.lower()
    has_tech = any(w in q for w in ["developer","engineer","analyst","java","python","sql","data"])
    has_soft = any(w in q for w in ["team","collaborat","communicat","leadership","stakeholder"])
    if has_tech and has_soft:
        result_urls = {r["assessment"]["url"] for r in results}
        has_p = any("Personality & Behaviour" in r["assessment"].get("test_types",[]) for r in results)
        if not has_p:
            opq = next(
                (a for a in ASSESSMENTS_FILTERED
                 if "Personality & Behaviour" in a.get("test_types",[])
                 and a["url"] not in result_urls),
                None,
            )
            if opq:
                results = results[:-1] + [{"assessment": opq, "embed_score": 0.5}]

    return results


def _fmt(item: dict) -> AssessmentOut:
    """Format assessment to match PDF Appendix 2 field names exactly."""
    a = item["assessment"]
    return AssessmentOut(
        url              = a.get("url", ""),
        name             = a.get("name", ""),
        adaptive_support = "Yes" if a.get("adaptive") else "No",
        description      = a.get("description", ""),
        duration         = a.get("duration_minutes"),      # Integer or null
        remote_support   = "Yes" if a.get("remote_testing") else "No",
        test_type        = a.get("test_types", []),        # List of strings
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/healthy")
def health():
    """Healthy check — returns {"status": "healthy"} as per PDF spec."""
    return {"status": "healthy"}


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    """
    Accepts: {"query": "JD text or URL"}
    Returns: {"recommended_assessments": [...]} — 1-10 assessments

    Matches Appendix 2 response format exactly.
    """
    raw = req.query.strip()

    if not raw:
        raise HTTPException(400, "Query cannot be empty.")
    if len(raw) < 5:
        raise HTTPException(400, "Query too short. Please provide a job title or description.")

    # URL input: fetch the JD text from the page
    if is_url(raw):
        query_text = await run_in_threadpool(fetch_jd_from_url, raw)
    else:
        query_text = raw

    results = await run_in_threadpool(_recommend, query_text, 10)

    if not results:
        raise HTTPException(500, "No recommendations generated.")

    return RecommendResponse(
        recommended_assessments=[_fmt(r) for r in results[:10]]
    )


@app.get("/")
def root():
    return {
        "status":      "ok",
        "api":         "SHL Assessment Recommendation",
        "version":     "2.1.0",
        "assessments": len(ASSESSMENTS_FILTERED),
        "endpoints": {
            "healthy":    "GET  /healthy",
            "recommend": "POST /recommend  — body: {\"query\": \"your JD or URL\"}"
        }
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
