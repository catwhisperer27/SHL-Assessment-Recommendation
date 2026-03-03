"""
embedder.py — ChromaDB + BM25 hybrid retrieval with RRF
Uses all-mpnet-base-v2 (stronger than MiniLM for semantic similarity)
"""

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi


def build_doc_text(a: dict) -> str:
    name = a.get("name", "")
    types = " ".join(a.get("test_types", []))
    levels = " ".join(a.get("job_levels", []))
    desc = a.get("description", "")
    return f"{name} {name} {types} {levels} {desc}"  # name repeated for weight


class Embedder:

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        print("[Embedder] Setting up ChromaDB + BM25...")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
        self.client = chromadb.PersistentClient(path="./catalogue_db")
        self.collection = self.client.get_or_create_collection(
            name="shl_assessments_mpnet",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        self.assessments: list[dict] = []
        self.bm25 = None
        print("[Embedder] Ready")

    def precompute(self, assessments: list[dict]):
        self.assessments = assessments
        corpus = [build_doc_text(a).lower().split() for a in assessments]
        self.bm25 = BM25Okapi(corpus)
        print(f"[Embedder] BM25 built — {len(corpus)} docs")

        if self.collection.count() == 0:
            print(f"[Embedder] Building ChromaDB ({len(assessments)} docs)...")
            for i in range(0, len(assessments), 100):
                batch = assessments[i:i+100]
                self.collection.add(
                    ids=[a["url"] for a in batch],
                    documents=[build_doc_text(a) for a in batch],
                    metadatas=[{
                        "name": a["name"], "url": a["url"],
                        "duration": a.get("duration_minutes") or 0,
                        "test_types": ", ".join(a.get("test_types", [])),
                    } for a in batch],
                )
            print(f"[Embedder] ChromaDB built — {self.collection.count()} vectors")
        else:
            print(f"[Embedder] ChromaDB loaded — {self.collection.count()} vectors")

    def bm25_search(self, query: str, top_k: int = 50) -> list[dict]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [{"assessment": self.assessments[i], "embed_score": round(float(scores[i]), 4)} for i in top]

    def vector_search(self, query: str, top_k: int = 50) -> list[dict]:
        url_map = {a["url"]: a for a in self.assessments}
        res = self.collection.query(query_texts=[query], n_results=min(top_k, self.collection.count()))
        results = []
        if res["ids"] and res["ids"][0]:
            for url, dist in zip(res["ids"][0], res["distances"][0]):
                a = url_map.get(url)
                if a:
                    results.append({"assessment": a, "embed_score": round(1 - dist, 4)})
        return results

    def _rrf(self, rankings: list[list], k: int = 60) -> list:
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}
        for ranking in rankings:
            for rank, item in enumerate(ranking):
                url = item["assessment"]["url"]
                scores[url] = scores.get(url, 0.0) + 1.0 / (k + rank + 1)
                items[url] = item
        return [items[url] for url in sorted(scores, key=scores.get, reverse=True)]

    def score(self, query: str, assessments: list[dict], max_duration: int = None) -> list[dict]:
        """Multi-variant hybrid retrieval: vector + BM25 + RRF."""
        all_rankings = []

        # Vector + BM25 on main query
        all_rankings.append(self.vector_search(query, top_k=50))
        all_rankings.append(self.bm25_search(query, top_k=50))

        # Duration filter note — handled in reranker scoring, not hard filter
        fused = self._rrf(all_rankings)

        print(f"[Embedder] Fused top3: {[r['assessment']['name'][:28] for r in fused[:3]]}")
        return fused