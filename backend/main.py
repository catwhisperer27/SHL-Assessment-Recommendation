"""
SHL Assessment Recommendation Engine — FastAPI Backend v3
Pipeline: Query → Injection (rules + semantic) → Hybrid Retrieval → LLM Rerank → Results
LLMs: Cerebras llama-3.3-70b (primary) → Gemini 2.0 Flash (fallback) → Retrieval order
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import uvicorn, re, requests
from bs4 import BeautifulSoup

load_dotenv()

from embedder import Embedder
from reranker import Reranker
from catalogue import ASSESSMENTS

app = FastAPI(title="SHL Assessment Recommendation API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

INDIVIDUAL_ASSESSMENTS = [a for a in ASSESSMENTS if a.get("category") == "Individual Test Solutions"]
print(f"[Startup] Individual Test Solutions: {len(INDIVIDUAL_ASSESSMENTS)}")

embedder = Embedder()
embedder.precompute(INDIVIDUAL_ASSESSMENTS)

reranker = Reranker(assessments=INDIVIDUAL_ASSESSMENTS)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

class AssessmentOut(BaseModel):
    url: str
    name: str
    adaptive_support: str
    description: str
    duration: Optional[int]
    remote_support: str
    test_type: list[str]

class RecommendResponse(BaseModel):
    recommended_assessments: list[AssessmentOut]


# ── URL fetching ──────────────────────────────────────────────────────────────

def is_url(text: str) -> bool:
    return bool(re.match(r"^https?://", text.strip())) or bool(re.match(r"^www\.", text.strip()))

def fetch_text_from_url(url: str) -> str:
    if url.startswith("www."): url = "https://" + url
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(400, f"URL timed out: {url}")
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script","style","nav","header","footer","aside"]): tag.decompose()
    main = (soup.find("main") or soup.find("article")
            or soup.find(class_=re.compile(r"job|description|content|posting", re.I))
            or soup.find("body"))
    text = re.sub(r"\s+", " ", (main or soup).get_text(separator=" ", strip=True))
    if len(text) < 50:
        raise HTTPException(400, "Could not extract meaningful text from URL.")
    return text[:3000]


# ── Helper ────────────────────────────────────────────────────────────────────

def fmt(a: dict) -> AssessmentOut:
    return AssessmentOut(
        url=a.get("url", ""),
        name=a.get("name", ""),
        adaptive_support="Yes" if a.get("adaptive", False) else "No",
        description=a.get("description", ""),
        duration=a.get("duration_minutes"),
        remote_support="Yes" if a.get("remote_testing", False) else "No",
        test_type=a.get("test_types", []),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "assessments": len(INDIVIDUAL_ASSESSMENTS)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "version": "3.0",
        "pipeline": "Injection (rules+semantic) + ChromaDB/BM25/RRF + Cerebras/Gemini rerank",
        "assessments": len(INDIVIDUAL_ASSESSMENTS),
    }

@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    """
    POST /recommend
    Body: {"query": "job description or URL", "max_results": 10}

    Pipeline:
    1. Extract text (URL or plain text)
    2. Phase 1 injection: hardcoded rules for known patterns
    3. Phase 2 injection: LLM semantic analysis → skills BM25 + type anchors
    4. Hybrid retrieval: vector + BM25 + RRF fills remaining pool
    5. LLM rerank top-15 (Cerebras → Gemini → retrieval order)
    6. Return top-10
    """
    raw = req.query.strip()
    if not raw or len(raw) < 5:
        raise HTTPException(400, "Query too short.")

    query_text = fetch_text_from_url(raw) if is_url(raw) else raw
    top_k = max(1, min(req.max_results or 10, 10))

    # Duration constraint
    max_dur = None
    m = re.search(r"\b(\d+)\s*(?:minutes?|mins?|hours?|hrs?)\b", query_text, re.I)
    if m:
        val = int(m.group(1))
        if "hour" in m.group(0).lower(): val *= 60
        max_dur = val
        print(f"[API] Duration constraint: ≤{max_dur}min")

    # Step 1: Get injected candidates (rules + semantic)
    injected = reranker.get_injected(query_text, bm25_search_fn=embedder.bm25_search)

    # Step 2: Hybrid retrieval fills remaining slots
    expanded_query = reranker.expand_query(query_text)
    fused = embedder.score(expanded_query, INDIVIDUAL_ASSESSMENTS, max_duration=max_dur)

    # Merge: injected first (guaranteed), RRF fills rest
    injected_urls = {item["assessment"]["url"] for item in injected}
    remaining = [item for item in fused if item["assessment"]["url"] not in injected_urls]
    candidates = (injected + remaining)[:25]

    if not candidates:
        raise HTTPException(500, "No matching assessments found.")

    # Step 3: LLM rerank
    reranked, _ = reranker.rerank(query_text, candidates, top_k=top_k)

    results = [fmt(item["assessment"]) for item in reranked[:10]]
    if not results:
        raise HTTPException(500, "Could not generate recommendations.")

    return RecommendResponse(recommended_assessments=results)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)