import { useEffect, useRef } from "react"

const TOKENS = [
  "python","sql","excel","leadership","communication","sales","java","react",
  "data analysis","project mgmt","teamwork","negotiation","kubernetes","machine learning",
  "finance","accounting","customer service","agile","scrum","typescript","nodejs",
  "marketing","recruitment","coaching","powerbi","tableau","aws","azure","devops",
  "c++","golang","rust","swift","kotlin","django","fastapi","tensorflow","pytorch",
  "hypothesis testing","regression","forecasting","risk mgmt","compliance","audit",
  "ux design","figma","product mgmt","roadmap","okrs","kpis","stakeholder mgmt",
  "cold calling","crm","salesforce","hubspot","seo","copywriting","branding",
  "nursing","clinical","diagnosis","patient care","pharmacology",
  "civil eng","structural","autocad","manufacturing","lean","six sigma",
  "teaching","curriculum","mentoring","facilitation","training",
  "quant finance","derivatives","portfolio","valuation","m&a",
  "cybersecurity","networking","linux","docker","microservices","rest api",
  "r language","matlab","spss","nlp","computer vision","reinforcement learning",
  "supply chain","logistics","procurement","inventory","erp","sap",
  "verbal reasoning","numerical","inductive","deductive","personality","motivation",
]

interface Props {
  active: boolean
}

export function TokenMatrix({ active }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")!
    const W = canvas.offsetWidth
    const H = canvas.offsetHeight
    canvas.width = W
    canvas.height = H

    const CELL_W = 118
    const CELL_H = 28
    const COLS = Math.floor(W / CELL_W)
    const ROWS = Math.floor(H / CELL_H)

    type Cell = { word: string; op: number; highlight: boolean; timer: number }
    const cells: Cell[][] = Array.from({ length: ROWS }, () =>
      Array.from({ length: COLS }, () => ({
        word: TOKENS[Math.floor(Math.random() * TOKENS.length)],
        op: Math.random() * 0.12 + 0.03,
        highlight: false,
        timer: 0,
      }))
    )

    let frame = 0
    const draw = () => {
      ctx.clearRect(0, 0, W, H)
      ctx.font = "11px 'JetBrains Mono', monospace"

      if (active && Math.random() < 0.05) {
        const r = Math.floor(Math.random() * ROWS)
        const c = Math.floor(Math.random() * COLS)
        cells[r][c].highlight = true
        cells[r][c].timer = 28
      }

      if (frame % 20 === 0) {
        const r = Math.floor(Math.random() * ROWS)
        const c = Math.floor(Math.random() * COLS)
        if (!cells[r][c].highlight) {
          cells[r][c].word = TOKENS[Math.floor(Math.random() * TOKENS.length)]
        }
      }

      cells.forEach((row, r) => {
        row.forEach((cell, c) => {
          const x = c * CELL_W + 8
          const y = r * CELL_H + 18
          if (cell.highlight) {
            const t = cell.timer / 28
            ctx.fillStyle = `rgba(0,210,180,${0.14 * t})`
            ctx.fillRect(x - 4, y - 14, CELL_W - 4, 20)
            ctx.fillStyle = `rgba(0,210,180,${0.9 * t})`
            ctx.fillText(cell.word, x, y)
            cell.timer--
            if (cell.timer <= 0) cell.highlight = false
          } else {
            ctx.fillStyle = `rgba(0,210,180,${cell.op})`
            ctx.fillText(cell.word, x, y)
          }
        })
      })

      frame++
      rafRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(rafRef.current)
  }, [active])

  return (
    <canvas ref={canvasRef} style={{ width: "100%", height: "100%", display: "block" }} />
  )
}