import type { Assessment } from "../types"

interface Props {
  assessment: Assessment
  rank: number
  delay?: number
}

export function ResultCard({ assessment: a, rank, delay = 0 }: Props) {
  const isRemote   = a.remote_support === "Yes"
  const isAdaptive = a.adaptive_support === "Yes"

  return (
    <div style={{
      background: "rgba(255,255,255,0.02)",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 14,
      padding: "20px 24px",
      marginBottom: 12,
      animation: `fadeUp 0.4s ease ${delay}s both`,
      transition: "border-color 0.2s",
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = "rgba(0,210,180,0.2)")}
      onMouseLeave={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)")}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 12 }}>
        {/* Rank badge */}
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, fontWeight: 700, color: "#00d2b4",
          minWidth: 28, paddingTop: 2,
        }}>
          #{rank}
        </div>

        <div style={{ flex: 1 }}>
          {/* Name + link */}
          <a href={a.url} target="_blank" rel="noreferrer" style={{
            fontSize: 15, fontWeight: 600, color: "#e8f0ee",
            textDecoration: "none", lineHeight: 1.4,
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "#00d2b4")}
            onMouseLeave={e => (e.currentTarget.style.color = "#e8f0ee")}
          >
            {a.name} ↗
          </a>

          {/* Tags row */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {/* Test types */}
            {a.test_type.map(t => (
              <span key={t} style={{
                fontSize: 10, fontWeight: 600, letterSpacing: "0.06em",
                color: "#00d2b4", background: "rgba(0,210,180,0.08)",
                border: "1px solid rgba(0,210,180,0.2)",
                padding: "3px 8px", borderRadius: 4,
              }}>{t.toUpperCase()}</span>
            ))}

            {/* Duration */}
            {a.duration && (
              <span style={{
                fontSize: 10, color: "rgba(180,220,210,0.5)",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                padding: "3px 8px", borderRadius: 4,
              }}>⏱ {a.duration} min</span>
            )}

            {/* Remote */}
            {isRemote && (
              <span style={{
                fontSize: 10, color: "rgba(180,220,210,0.5)",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                padding: "3px 8px", borderRadius: 4,
              }}>🌐 Remote</span>
            )}

            {/* Adaptive */}
            {isAdaptive && (
              <span style={{
                fontSize: 10, color: "rgba(180,220,210,0.5)",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                padding: "3px 8px", borderRadius: 4,
              }}>⚡ Adaptive</span>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      {a.description && (
        <p style={{
          fontSize: 13, color: "rgba(180,220,210,0.45)",
          lineHeight: 1.7, marginLeft: 44,
          display: "-webkit-box", WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical", overflow: "hidden",
        }}>
          {a.description}
        </p>
      )}

      {/* URL */}
      <div style={{ marginLeft: 44, marginTop: 8 }}>
        <a href={a.url} target="_blank" rel="noreferrer" style={{
          fontSize: 11, color: "rgba(0,210,180,0.4)",
          fontFamily: "'JetBrains Mono', monospace",
          textDecoration: "none",
        }}
          onMouseEnter={e => (e.currentTarget.style.color = "#00d2b4")}
          onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,210,180,0.4)")}
        >
          {a.url.replace("https://www.shl.com", "")}
        </a>
      </div>
    </div>
  )
}
