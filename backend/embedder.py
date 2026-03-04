"""
embedder.py — Loads pre-computed matrix from .npy files on Render.
Falls back to full model if files not found (local dev).

Memory on Render free tier:
  Before: all-mpnet-base-v2 = ~420MB → OOM
  After:  .npy matrix load  = ~2.4MB → fits easily in 512MB
  
Still needs the model for QUERY encoding (~80MB with MiniLM).
Assessment vectors are pre-computed — model never runs for those.
"""

import numpy as np
import json
import os


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._cache   = {}
        self._matrix  = None
        self._urls    = []
        self.model    = None
        self._model_name = model_name

        # Try loading pre-computed matrix first
        if os.path.exists("embeddings_matrix.npy") and os.path.exists("embeddings_urls.json"):
            self._matrix = np.load("embeddings_matrix.npy")
            with open("embeddings_urls.json") as f:
                self._urls = json.load(f)
            print(f"[Embedder] Loaded pre-computed matrix {self._matrix.shape} — skipping model load for assessments")
        else:
            # Fallback: load full model (local dev without .npy files)
            print(f"[Embedder] No .npy files found — loading full model {model_name}")
            self._load_model()

    def _load_model(self):
        """Lazy model loader — only called when actually needed."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            print(f"[Embedder] Loading {self._model_name}...")
            self.model = SentenceTransformer(self._model_name)
            print("[Embedder] Model ready")

    def _text(self, a: dict) -> str:
        name  = a.get("name", "")
        types = " ".join(a.get("test_types", []))
        desc  = a.get("description", "")
        return f"{name} {name} {types} {desc}"

    def precompute(self, assessments: list[dict]):
        """
        Skip if pre-computed matrix already loaded from .npy.
        Only runs the full encode pipeline in local dev (no .npy files).
        """
        if self._matrix is not None:
            print(f"[Embedder] Using pre-computed matrix — skipping precompute")
            return

        self._load_model()
        print(f"[Embedder] Pre-computing {len(assessments)} embeddings...")
        texts = [self._text(a) for a in assessments]
        vecs  = self.model.encode(
            texts, batch_size=64, show_progress_bar=True,
            convert_to_numpy=True, normalize_embeddings=True
        )
        for a, v in zip(assessments, vecs):
            self._cache[a["url"]] = v

        self._urls   = [a["url"] for a in assessments]
        self._matrix = np.vstack([self._cache[u] for u in self._urls])
        print(f"[Embedder] Matrix shape: {self._matrix.shape} — ready")

    def score(self, query: str, assessments: list[dict]) -> list[dict]:
        """
        Embed query → single matrix multiply → sorted results.
        Model only needed to encode the query (~2ms with MiniLM).
        """
        # Always need model for query encoding
        self._load_model()
        q_vec = self.model.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        )[0]

        if self._matrix is not None:
            # Fast path: matrix loaded from .npy — one dot product for all 389
            sims    = self._matrix @ q_vec
            url_map = {a["url"]: a for a in assessments}
            results = [
                {"assessment": url_map[url], "embed_score": float(sims[i])}
                for i, url in enumerate(self._urls)
                if url in url_map
            ]
        else:
            # Fallback loop (should never reach here if precompute ran)
            q_vec_2d = q_vec.reshape(1, -1)
            results  = []
            for a in assessments:
                v = self._cache.get(a["url"])
                if v is None:
                    v = self.model.encode(
                        [self._text(a)], normalize_embeddings=True,
                        convert_to_numpy=True
                    )[0]
                from sklearn.metrics.pairwise import cosine_similarity
                score = float(cosine_similarity(q_vec_2d, v.reshape(1, -1))[0][0])
                results.append({"assessment": a, "embed_score": score})

        results.sort(key=lambda x: x["embed_score"], reverse=True)
        return results
