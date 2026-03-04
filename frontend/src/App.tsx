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
  { label: "Investment Banker", jd: "We are looking for an Investment Banker with strong analytical and financial modeling skills, deep understanding of corporate finance, and the ability to execute complex transactions. Must demonstrate strategic thinking, attention to detail, and strong communication skills. Should be comfortable working in high-pressure environments, collaborating with cross-functional teams, and advising clients on capital raising, M&A, and financial strategy." },
  { label: "Chief Operating Officer", jd: "We are looking for a Chief Operating Officer (COO) with strong leadership and operational excellence skills, capable of driving execution across teams and scaling business processes efficiently. Must demonstrate strategic thinking, data-driven decision making, and the ability to align operations with company vision. Should be comfortable managing cross-functional teams, optimizing performance metrics, and building systems that enable sustainable growth in a fast-paced environment." },
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
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;0,9..40,900;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,210,180,0.12); border-radius: 4px; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:0.5; } 50% { opacity:1; } }
        textarea { outline: none; resize: none; }
        textarea::placeholder { color: rgba(180,220,210,0.18); }
        input { outline: none; }
        input::placeholder { color: rgba(180,220,210,0.18); }
        select { outline: none; }
        a { text-decoration: none; }
        .result-scroll::-webkit-scrollbar { width: 3px; }
        .result-scroll::-webkit-scrollbar-thumb { background: rgba(0,210,180,0.1); border-radius: 4px; }
        .pill-btn:hover { background: rgba(0,210,180,0.12) !important; color: #00d2b4 !important; border-color: rgba(0,210,180,0.35) !important; }
        .run-btn:hover:not(:disabled) { background: #00d2b4 !important; }
      `}</style>
