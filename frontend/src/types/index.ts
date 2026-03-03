export interface Assessment {
  url: string
  name: string
  adaptive_support: string
  description: string
  duration: number | null
  remote_support: string
  test_type: string[]
  embed_score?: number | null
  llm_score?: number | null
}

export interface RecommendRequest {
  query: string
  max_results?: number
}

export interface RecommendResponse {
  recommended_assessments: Assessment[]
}

export type Phase = "idle" | "expanding" | "embedding" | "reranking" | "done"
export type ViewTab = "final" | "embed"