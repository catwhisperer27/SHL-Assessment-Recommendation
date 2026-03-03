import type { Phase } from "../types"

interface Props {
  phase: Phase
}

const STEPS = [
  { label: "Job Description", sub: "raw text input", icon: "📄" },
  { label: "Query Expansion", sub: "Groq enriches JD", icon: "🔍" },
  { label: "Sentence Embeddings", sub: "all-MiniLM-L6-v2", icon: "⚡" },
  { label: "Cosine Similarity", sub: "vs 518 assessments", icon: "📐" },
  { label: "Top-K Retrieval", sub: "top 20 candidates", icon: "🎯" },
  { label: "LLM Reranking", sub: "Groq Llama 3.3 70B", icon: "🧠" },
  { label: "API Response", sub: "FastAPI /recommend", icon: "🚀" },
]

const PHASE_IDX: Record<Phase, number> = {
  idle: -1,
  expanding: 1,
  embedding: 2,
  reranking: 5,
  done: 6,
}

export function ArchDiagram({ phase }: Props) {
  const activeIdx = PHASE_IDX[phase]

  return (
    <section style={{ padding: "80px 64px", background: "#060b0a", borderTop: "1px solid rgba(0,210,190,0.08)" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>

        <div style={{ marginBottom: 10 }}>
          <span style={{ fontSize: 11, color: "#00d2be", letterSpacing: "0.15em", fontWeight: 600 }}>SYSTEM ARCHITECTURE</span>
        </div>
        <h2 style={{ fontFamily: "'Syne', sans-serif", fontSize: 32, fontWeight: 800, letterSpacing: "-0.03em", marginBottom: 8 }}>
          From sequential to parallel
        </h2>
        <p style={{ fontSize: 14, color: "#4a7a74", lineHeight: 1.75, maxWidth: 500, marginBottom: 52 }}>
          Traditional keyword search matches one term at a time. This pipeline embeds the entire JD semantically, retrieves candidates in parallel, then reranks with LLM reasoning.
        </p>

        {/* Pipeline flow */}
        <div style={{ display: "flex", alignItems: "center", overflowX: "auto", paddingBottom: 16, gap: 0 }}>
          {STEPS.map((s, i) => (
            <div key={s.label} style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
              <div style={{
                background: i <= activeIdx ? "rgba(0,210,190,0.1)" : "rgba(255,255,255,0.02)",
                border: `1px solid ${i === activeIdx ? "rgba(0,210,190,0.5)" : i < activeIdx ? "rgba(0,210,190,0.25)" : "rgba(255,255,255,0.07)"}`,
                borderRadius: 12, padding: "14px 16px", minWidth: 120, textAlign: "center",
                transition: "all 0.5s ease",
                boxShadow: i === activeIdx ? "0 0 20px rgba(0,210,190,0.15)" : "none",
              }}>
                <div style={{ fontSize: 20, marginBottom: 6 }}>{s.icon}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: i <= activeIdx ? "#00d2be" : "#2a4a44", marginBottom: 3, transition: "color 0.5s" }}>
                  {s.label}
                </div>
                <div style={{ fontSize: 10, color: "#1a3a34" }}>{s.sub}</div>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{ display: "flex", alignItems: "center", padding: "0 6px", flexShrink: 0 }}>
                  <div style={{ width: 20, height: 1, background: i < activeIdx ? "rgba(0,210,190,0.4)" : "rgba(255,255,255,0.07)", transition: "background 0.5s" }} />
                  <div style={{ width: 0, height: 0, borderTop: "4px solid transparent", borderBottom: "4px solid transparent", borderLeft: `5px solid ${i < activeIdx ? "rgba(0,210,190,0.4)" : "rgba(255,255,255,0.07)"}`, transition: "border-color 0.5s" }} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Parallel vs Sequential */}
        <div style={{ marginTop: 60, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28 }}>
          <div>
            <div style={{ fontSize: 10, color: "#4a7a74", marginBottom: 6, letterSpacing: "0.1em", fontWeight: 600 }}>PARALLEL RETRIEVAL · OUR SYSTEM</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {["embed", "cosine", "retrieve", "rerank", "serve", "respond"].map((t, i) => (
                <div key={t} style={{
                  background: "rgba(0,210,190,0.12)", border: "1px solid rgba(0,210,190,0.35)",
                  color: "#00d2be", padding: "7px 13px", borderRadius: 6,
                  fontSize: 11, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600,
                  animation: `fadeUp 0.3s ease ${i * 0.06}s both`,
                }}>
                  {t}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#1a3a34", marginBottom: 6, letterSpacing: "0.1em", fontWeight: 600 }}>SEQUENTIAL SEARCH · KEYWORD MATCHING</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {["keyword", "match", "keyword", "match", "keyword", "match"].map((t, i) => (
                <div key={i} style={{
                  background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)",
                  color: "#1a3a34", padding: "7px 13px", borderRadius: 6,
                  fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tech stack */}
        <div style={{ marginTop: 52, display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
          {[
            { label: "Embeddings", value: "all-MiniLM-L6-v2", sub: "sentence-transformers" },
            { label: "LLM Reranking", value: "Llama 3.3 70B", sub: "Groq — free API" },
            { label: "Backend", value: "FastAPI", sub: "Python async" },
            { label: "Catalogue", value: "518 assessments", sub: "scraped from SHL" },
          ].map(s => (
            <div key={s.label} style={{
              background: "rgba(0,210,190,0.03)", border: "1px solid rgba(0,210,190,0.1)",
              borderRadius: 12, padding: "18px 16px",
            }}>
              <div style={{ fontSize: 10, color: "#4a7a74", letterSpacing: "0.1em", marginBottom: 7, fontWeight: 600 }}>{s.label.toUpperCase()}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#00d2be", marginBottom: 3 }}>{s.value}</div>
              <div style={{ fontSize: 11, color: "#1a3a34" }}>{s.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
