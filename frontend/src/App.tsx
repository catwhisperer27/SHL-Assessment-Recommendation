import { useState, useRef } from "react"
import { TokenMatrix } from "./components/TokenMatrix"
import { ResultCard } from "./components/ResultCard"
import { getRecommendations } from "./api/recommend"
import type { Phase, RecommendResponse } from "./types"

const API_BASE = import.meta.env.VITE_API_URL || "https://shl-assessment-recommendation-1-by9w.onrender.com"

const EXAMPLES = [
  { label: "Software Engineer", jd: "We are looking for a Software Engineer with strong problem-solving skills, proficiency in algorithms and data structures, and ability to write clean scalable code. Must demonstrate logical thinking, collaborate in teams, and have passion for building software products." },
  { label: "Data Analyst", jd: "Seeking a Data Analyst to interpret complex datasets, build dashboards, and communicate insights to stakeholders. Strong numerical reasoning, SQL skills, and attention to detail required. Must present findings clearly to non-technical audiences." },
  { label: "HR Partner", jd: "We need an HR Business Partner to support talent acquisition, drive employee engagement, and partner with leaders on workforce planning. Strong interpersonal skills, coaching ability, and organisational awareness required." },
  { label: "Investment Banker", jd: "We are looking for an Investment Banker with strong analytical and financial modeling skills, deep understanding of corporate finance, and the ability to execute complex transactions. Must demonstrate strategic thinking, attention to detail, and strong communication skills." },
  { label: "Chief Operating Officer", jd: "We are looking for a Chief Operating Officer (COO) with strong leadership and operational excellence skills, capable of driving execution across teams and scaling business processes efficiently. Must demonstrate strategic thinking, data-driven decision making, and the ability to align operations with company vision." },
]

const STATUS: Record<Phase, string> = {
  idle: "",
  expanding: "Expanding query...",
  embedding: "Retrieving candidates...",
  reranking: "LLM reranking...",
  done: "",
}

const PIPELINE_STEPS = ["expand", "retrieve", "rerank", "serve"]
const PIPELINE_PHASES = ["expanding", "embedding", "reranking", "done"]

export default function App() {
  const [jd, setJd] = useState("")
  const [phase, setPhase] = useState<Phase>("idle")
  const [response, setResponse] = useState<RecommendResponse | null>(null)
  const [error, setError] = useState("")
  const [filters, setFilters] = useState({ maxDuration: "", jobLevel: "", remoteOnly: false })
  const rightPanelRef = useRef<HTMLDivElement>(null)

  const isRunning = phase === "expanding" || phase === "embedding" || phase === "reranking"
  const showNote = !response

  const run = async () => {
    if (!jd.trim() || isRunning) return
    setError("")
    setResponse(null)
    setPhase("expanding")
    await new Promise(r => setTimeout(r, 500))
    setPhase("embedding")
    await new Promise(r => setTimeout(r, 700))
    setPhase("reranking")
    try {
      const res = await getRecommendations({ query: jd })
      setResponse(res)
      setPhase("done")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
      setPhase("idle")
    }
  }

  const filteredResults = response?.recommended_assessments.filter(a => {
    if (filters.maxDuration && a.duration && a.duration > parseInt(filters.maxDuration)) return false
    if (filters.jobLevel && !a.test_type?.includes(filters.jobLevel)) return false
    if (filters.remoteOnly && a.remote_support !== "Yes") return false
    return true
  }) ?? []

  const css = [
    "@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;0,9..40,900;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap');",
    "* { box-sizing: border-box; margin: 0; padding: 0; }",
    "::-webkit-scrollbar { width: 3px; }",
    "::-webkit-scrollbar-track { background: transparent; }",
    "::-webkit-scrollbar-thumb { background: rgba(0,210,180,0.12); border-radius: 4px; }",
    "@keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }",
    "@keyframes fadeOut { from { opacity:1; transform:translateY(0); } to { opacity:0; transform:translateY(-6px); } }",
    "@keyframes spin { to { transform: rotate(360deg); } }",
    "@keyframes pulse { 0%,100% { opacity:0.5; } 50% { opacity:1; } }",
    "@keyframes geminiSwirl { 0%{filter:hue-rotate(0deg) brightness(1.1);opacity:0.9} 25%{filter:hue-rotate(90deg) brightness(1.3);opacity:1} 50%{filter:hue-rotate(200deg) brightness(1.2);opacity:0.85} 75%{filter:hue-rotate(290deg) brightness(1.4);opacity:1} 100%{filter:hue-rotate(360deg) brightness(1.1);opacity:0.9} }",
    "@keyframes geminiBorder { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }",
    ".note-border-wrap { position:relative; border-radius:11px; padding:1.5px; }",
    ".note-border-wrap::before { content:''; position:absolute; inset:0; border-radius:11px; background: linear-gradient(135deg, #4285F4, #EA4335, #FBBC05, #34A853, #4285F4, #EA4335); background-size:300% 300%; z-index:0; }",
    isRunning
      ? ".note-border-wrap::before { animation: geminiBorder 2.5s ease infinite; opacity:1; }"
      : ".note-border-wrap::before { animation: none; opacity:0.25; filter: saturate(0.5); }",
    ".note-inner { position:relative; z-index:1; border-radius:10px; background:#0c0f0e; }",
    "textarea { outline: none; resize: none; }",
    "textarea::placeholder { color: rgba(180,220,210,0.18); }",
    "input { outline: none; }",
    "input::placeholder { color: rgba(180,220,210,0.18); }",
    "select { outline: none; }",
    "a { text-decoration: none; }",
    ".result-scroll::-webkit-scrollbar { width: 3px; }",
    ".result-scroll::-webkit-scrollbar-thumb { background: rgba(0,210,180,0.1); border-radius: 4px; }",
    ".pill-btn:hover { background: rgba(0,210,180,0.12) !important; color: #00d2b4 !important; border-color: rgba(0,210,180,0.35) !important; }",
    ".run-btn:hover:not(:disabled) { background: #00d2b4 !important; }",
    ".note-corner { position: absolute; width: 10px; height: 10px; }",
    ".note-corner::before, .note-corner::after { content: ''; position: absolute; background: linear-gradient(135deg, #4285F4, #EA4335, #FBBC05, #34A853); border-radius: 1px; }",
    ".note-corner--tl { top: -1px; left: -1px; }",
    ".note-corner--tl::before { width: 2px; height: 10px; top: 0; left: 0; }",
    ".note-corner--tl::after  { width: 10px; height: 2px; top: 0; left: 0; }",
    ".note-corner--tr { top: -1px; right: -1px; }",
    ".note-corner--tr::before { width: 2px; height: 10px; top: 0; right: 0; }",
    ".note-corner--tr::after  { width: 10px; height: 2px; top: 0; right: 0; }",
    ".note-corner--bl { bottom: -1px; left: -1px; }",
    ".note-corner--bl::before { width: 2px; height: 10px; bottom: 0; left: 0; }",
    ".note-corner--bl::after  { width: 10px; height: 2px; bottom: 0; left: 0; }",
    ".note-corner--br { bottom: -1px; right: -1px; }",
    ".note-corner--br::before { width: 2px; height: 10px; bottom: 0; right: 0; }",
    ".note-corner--br::after  { width: 10px; height: 2px; bottom: 0; right: 0; }",
    isRunning
      ? ".note-corner { animation: geminiSwirl 2s ease-in-out infinite; } .note-corner--tr { animation-delay: 0.5s; } .note-corner--bl { animation-delay: 1s; } .note-corner--br { animation-delay: 1.5s; }"
      : ".note-corner { animation: none; opacity: 0.3; filter: saturate(0.4); }",
  ].join("\n")

  return (
    <div style={{
      background: "#0c0f0e",
      color: "#e8f0ee",
      fontFamily: "'DM Sans', sans-serif",
      height: "100vh",
      width: "100vw",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
    }}>
      <style>{css}</style>

      <nav style={{
        height: 56,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 48px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        background: "rgba(12,15,14,0.9)",
        backdropFilter: "blur(24px)",
        zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#00d2b4", boxShadow: "0 0 8px rgba(0,210,180,0.6)" }} />
          <span style={{ fontWeight: 800, fontSize: 14, letterSpacing: "-0.02em" }}>SHL FLOW</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {PIPELINE_STEPS.map((s, i) => {
            const active = PIPELINE_PHASES.indexOf(phase) >= i
            return (
              <div key={s} style={{ display: "flex", alignItems: "center" }}>
                {i > 0 && (
                  <div style={{ width: 20, height: 1, background: active ? "rgba(0,210,180,0.35)" : "rgba(255,255,255,0.07)", margin: "0 4px", transition: "background 0.5s" }} />
                )}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                  <div style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: active ? "#00d2b4" : "rgba(255,255,255,0.1)",
                    boxShadow: active ? "0 0 6px rgba(0,210,180,0.7)" : "none",
                    transition: "all 0.4s",
                    animation: PIPELINE_PHASES[i] === phase ? "pulse 1s ease infinite" : "none",
                  }} />
                  <span style={{ fontSize: 8, color: active ? "rgba(0,210,180,0.6)" : "rgba(255,255,255,0.15)", letterSpacing: "0.08em", transition: "color 0.4s" }}>{s}</span>
                </div>
              </div>
            )
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {STATUS[phase] && (
            <span style={{ fontSize: 10, color: "rgba(0,210,180,0.7)", fontFamily: "'JetBrains Mono', monospace", animation: "pulse 1.5s ease infinite" }}>
              {STATUS[phase]}
            </span>
          )}
          <span style={{ fontSize: 10, color: "rgba(0,210,180,0.35)", fontFamily: "'JetBrains Mono', monospace" }}>389 assessments</span>
          <a
            href={API_BASE + "/docs"}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 10, color: "rgba(180,220,210,0.3)", letterSpacing: "0.08em", fontWeight: 600, transition: "color 0.2s" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#00d2b4")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(180,220,210,0.3)")}>
            API DOCS
          </a>
        </div>
      </nav>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", overflow: "hidden", position: "relative" }}>
        <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
          <TokenMatrix active={isRunning || phase === "done"} />
        </div>
        <div style={{ position: "absolute", top: 0, left: 0, bottom: 0, width: "48%", background: "linear-gradient(to right, rgba(12,15,14,0.97) 55%, transparent 100%)", zIndex: 1, pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 2, padding: "0 52px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ marginBottom: 20 }}>
            <span style={{ fontSize: 10, color: "#00d2b4", letterSpacing: "0.16em", fontWeight: 600, background: "rgba(0,210,180,0.06)", border: "1px solid rgba(0,210,180,0.14)", padding: "4px 14px", borderRadius: 20 }}>
              ASSESSMENT RECOMMENDATION ENGINE
            </span>
          </div>
          <h1 style={{ fontSize: 82, fontWeight: 900, lineHeight: 1.04, letterSpacing: "-0.04em", color: "#e8f0ee", marginBottom: 18, animation: "fadeUp 0.5s ease both" }}>
            The right<br />
            assessment<br />
            for every{" "}
            <span style={{ background: "rgba(0,210,180,0.12)", border: "1px solid rgba(0,210,180,0.35)", color: "#00d2b4", padding: "2px 14px", borderRadius: 8, display: "inline-block" }}>
              role
            </span>
          </h1>
          <p style={{ fontSize: 18, color: "rgba(180,220,210,0.38)", lineHeight: 1.8, maxWidth: 360, fontWeight: 400, animation: "fadeUp 0.5s ease 0.1s both" }}>
            Paste a job description or URL. The hybrid retrieval pipeline finds the most relevant SHL assessments using semantic search and LLM reranking.
          </p>
        </div>

        <div ref={rightPanelRef} style={{ position: "relative", zIndex: 2, padding: "0 48px 0 24px", display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {EXAMPLES.map(ex => (
              <button key={ex.label} className="pill-btn" onClick={() => setJd(ex.jd)} style={{
                background: "rgba(0,210,180,0.05)", border: "1px solid rgba(0,210,180,0.13)",
                color: "rgba(0,210,180,0.5)", padding: "4px 12px", fontSize: 10,
                fontFamily: "'DM Sans', sans-serif", fontWeight: 600, borderRadius: 50,
                cursor: "pointer", letterSpacing: "0.04em", backdropFilter: "blur(8px)", transition: "all 0.15s",
              }}>{ex.label}</button>
            ))}
          </div>

          <div style={{
            background: "rgba(12,15,14,0.35)",
            border: "1px solid rgba(0,210,180,0.08)",
            borderRadius: 16,
            overflow: "hidden",
            backdropFilter: "blur(6px)",
            boxShadow: "0 8px 40px rgba(0,0,0,0.3), 0 0 0 1px rgba(0,210,180,0.06)",
          }}>
            <textarea
              rows={5}
              value={jd}
              onChange={e => setJd(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && e.metaKey) run() }}
              placeholder="Paste a job description, role title, or URL..."
              style={{
                width: "100%", background: "transparent", border: "none",
                color: "#e8f0ee", fontSize: 13, padding: "18px 20px",
                fontFamily: "'DM Sans', sans-serif", lineHeight: 1.75, fontWeight: 400,
              }}
            />
            <div style={{
              display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
              padding: "8px 12px", borderTop: "1px solid rgba(255,255,255,0.05)",
              background: "rgba(0,0,0,0.1)",
            }}>
              <input
                placeholder="Max duration (min)"
                value={filters.maxDuration}
                onChange={e => setFilters(f => ({ ...f, maxDuration: e.target.value }))}
                style={{ background: "transparent", border: "1px solid rgba(255,255,255,0.08)", color: "#e8f0ee", padding: "4px 10px", borderRadius: 8, fontSize: 10, fontFamily: "inherit", width: 120 }}
              />
              <select
                value={filters.jobLevel}
                onChange={e => setFilters(f => ({ ...f, jobLevel: e.target.value }))}
                style={{ background: "#0c0f0e", border: "1px solid rgba(255,255,255,0.08)", color: filters.jobLevel ? "#e8f0ee" : "rgba(180,220,210,0.2)", padding: "4px 10px", borderRadius: 8, fontSize: 10, fontFamily: "inherit" }}
              >
                <option value="">All levels</option>
                {["Graduate", "Entry-Level", "Mid-Professional", "Manager", "Director", "Executive"].map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
              <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "rgba(180,220,210,0.3)", cursor: "pointer" }}>
                <input type="checkbox" checked={filters.remoteOnly} onChange={e => setFilters(f => ({ ...f, remoteOnly: e.target.checked }))} />
                Remote only
              </label>
              <button onClick={run} disabled={isRunning || !jd.trim()} className="run-btn" style={{
                marginLeft: "auto",
                width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
                background: jd.trim() && !isRunning ? "#e8f0ee" : "rgba(255,255,255,0.07)",
                border: "none",
                color: jd.trim() && !isRunning ? "#0c0f0e" : "rgba(255,255,255,0.2)",
                cursor: isRunning || !jd.trim() ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.2s", fontSize: 15, fontWeight: 700,
              }}>
                {isRunning
                  ? <div style={{ width: 13, height: 13, border: "2px solid rgba(255,255,255,0.1)", borderTopColor: "#e8f0ee", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                  : "↑"}
              </button>
            </div>
          </div>

          {/* Render cold-start note — hidden once results load */}
          {showNote && (
            <div className="note-border-wrap" style={{ animation: "fadeUp 0.4s ease both" }}>
              <div className="note-inner" style={{ padding: "10px 16px" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span style={{ fontSize: 13, lineHeight: 1, marginTop: 1 }}>⚡</span>
                  <div>
                    <p style={{ fontSize: 11, color: "rgba(200,220,215,0.8)", lineHeight: 1.6, fontWeight: 500 }}>
                      The backend is hosted on Render. For the first visit after some time, the service may take up to <span style={{ color: "#fff", fontWeight: 700 }}>1 minute</span> to start. Please be patient while it boots.
                    </p>
                    <p style={{ fontSize: 10, color: "rgba(180,220,210,0.3)", marginTop: 4, lineHeight: 1.5 }}>
                      If it takes more than 1 min with no response, reload the page and try again.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div style={{ fontSize: 11, color: "#f87171", background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.15)", padding: "8px 14px", borderRadius: 8, animation: "fadeUp 0.3s ease both" }}>
              {error}
            </div>
          )}

          {response && (
            <div style={{ animation: "fadeUp 0.4s ease both" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, paddingLeft: 2 }}>
                <div>
                  <span style={{ fontSize: 10, color: "#00d2b4", letterSpacing: "0.12em", fontWeight: 600 }}>RESULTS</span>
                  <span style={{ fontSize: 10, color: "rgba(180,220,210,0.3)", marginLeft: 10 }}>{filteredResults.length} assessments</span>
                </div>
                <span style={{ fontSize: 10, color: "rgba(0,210,180,0.4)", fontFamily: "'JetBrains Mono', monospace" }}>LLM Reranked</span>
              </div>
              <div className="result-scroll" style={{ overflowY: "auto", maxHeight: "calc(100vh - 420px)", paddingRight: 4 }}>
                {filteredResults.map((a, i) => (
                  <ResultCard key={a.url} assessment={a} rank={i + 1} delay={i * 0.05} />
                ))}
                {filteredResults.length === 0 && (
                  <div style={{ fontSize: 12, color: "rgba(180,220,210,0.3)", padding: "20px 0", textAlign: "center" }}>
                    No results match your filters.
                  </div>
                )}
              </div>
            </div>
          )}

          {isRunning && !response && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[1, 2, 3].map(i => (
                <div key={i} style={{ height: 64, borderRadius: 10, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", animation: "pulse 1.5s ease infinite" }} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{
        height: 36, flexShrink: 0,
        borderTop: "1px solid rgba(255,255,255,0.04)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 48px",
        background: "rgba(0,0,0,0.3)",
      }}>
        <span style={{ fontWeight: 700, fontSize: 11, letterSpacing: "-0.01em", color: "rgba(180,220,210,0.3)" }}>Rishi</span>
        <span style={{ fontSize: 10, color: "rgba(180,220,210,0.15)" }}></span>
      </div>
    </div>
  )
}
