import type { RecommendRequest, RecommendResponse } from "../types"

const API_BASE = import.meta.env.VITE_API_URL || "https://shl-assessment-recommendation-1-by9w.onrender.com"

export async function getRecommendations(req: RecommendRequest): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/healthy`)
    return res.ok
  } catch {
    return false
  }
}
