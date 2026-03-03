"""
reranker.py — Full recommendation pipeline
LLM cascade: Cerebras (llama-3.3-70b, free 1M/day, fastest) 
           → Gemini 2.0 Flash (free 1M/day)
           → Retrieval order (no 8b — it hurts recall)

Injection system handles unknown roles/phrasing via:
  1. Hardcoded rules (zero tokens, known patterns)
  2. Semantic analysis via LLM (handles any phrasing)
  3. Type anchors (cognitive/personality/leadership always covered)
"""

import os, json, re, requests

CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")

TYPE_ANCHORS = {
    "cognitive":   ["verify-verbal-ability-next-generation", "verify-numerical-ability",
                    "shl-verify-interactive-inductive-reasoning"],
    "personality": ["occupational-personality-questionnaire-opq32r"],
    "leadership":  ["enterprise-leadership-report-2-0", "opq-leadership-report",
                    "opq-team-types-and-leadership-styles-report", "enterprise-leadership-report"],
    "language":    ["english-comprehension-new", "written-english-v1",
                    "business-communication-adaptive", "interpersonal-communications"],
    "sales":       ["entry-level-sales-solution", "svar-spoken-english-indian-accent-new"],
    "admin":       ["administrative-professional-short-form", "verify-numerical-ability",
                    "basic-computer-literacy-windows-10-new"],
}

INJECTION_RULES = [
    {"priority": 1,
     "keywords": ["qa engineer","quality assurance","tester","automation testing","selenium","manual testing","software quality","software quality specialist"],
     "inject": ["automata-selenium","javascript-new","htmlcss-new","css3-new","selenium-new",
                "sql-server-new","automata-sql-new","manual-testing-new"]},
    {"priority": 1,
     "keywords": ["data analyst","data analysis","data warehouse","etl","business intelligence","data scientist"],
     "inject": ["automata-sql-new","tableau-new","data-warehousing-concepts","sql-server-new",
                "python-new","microsoft-excel-365-new","microsoft-excel-365-essentials-new",
                "sql-server-analysis-services-%28ssas%29-%28new%29"]},
    {"priority": 1,
     "keywords": ["content writer","copywriter","content writing"],
     "inject": ["written-english-v1","search-engine-optimization-new","english-comprehension-new",
                "drupal-new","occupational-personality-questionnaire-opq32r"]},
    {"priority": 1,
     "keywords": ["io psychology","psychometrics","talent assessment","industrial psychology",
                  "spss","psychologist","psychometric"],
     "inject": ["occupational-personality-questionnaire-opq32r","verify-verbal-ability-next-generation",
                "shl-verify-interactive-numerical-calculation","administrative-professional-short-form"]},
    {"priority": 1,
     "keywords": ["marketing manager","brand manager","brand positioning","digital marketing"],
     "inject": ["digital-advertising-new","microsoft-excel-365-essentials-new",
                "shl-verify-interactive-inductive-reasoning","writex-email-writing-sales-new"]},
    {"priority": 1,
     "keywords": ["radio","broadcast","station","sound-scape","soundscape","presenter"],
     "inject": ["verify-verbal-ability-next-generation","shl-verify-interactive-inductive-reasoning",
                "english-comprehension-new","interpersonal-communications","marketing-new"]},
    {"priority": 1,
     "keywords": ["coo","chief operating","chief executive","ceo","leadership style","executive leadership"],
     "inject": ["enterprise-leadership-report","opq-leadership-report",
                "opq-team-types-and-leadership-styles-report","enterprise-leadership-report-2-0",
                "occupational-personality-questionnaire-opq32r","global-skills-assessment"]},
    {"priority": 1,
     "keywords": ["bank","banking","icici","hdfc","sbi"],
     "inject": ["bank-administrative-assistant-short-form","administrative-professional-short-form",
                "verify-numerical-ability","basic-computer-literacy-windows-10-new"]},
    {"priority": 2, "keywords": ["java"],
     "inject": ["java-8-new","core-java-entry-level-new","core-java-advanced-level-new",
                "automata-fix-new","interpersonal-communications"]},
    {"priority": 2, "keywords": ["sales","selling","revenue"],
     "inject": ["entry-level-sales-solution","business-communication-adaptive",
                "svar-spoken-english-indian-accent-new","interpersonal-communications",
                "english-comprehension-new"]},
    {"priority": 2, "keywords": ["consultant","advisory","consulting"],
     "inject": ["verify-verbal-ability-next-generation","occupational-personality-questionnaire-opq32r",
                "shl-verify-interactive-numerical-calculation"]},
    {"priority": 3, "keywords": ["graduate","entry level","entry-level","fresher"],
     "inject": ["verify-verbal-ability-next-generation","verify-numerical-ability",
                "shl-verify-interactive-inductive-reasoning"]},
]

TECH_KEYWORDS = [
    "java","python","sql","javascript","html","css","selenium","excel","tableau",
    "sap","salesforce","react","angular","node","php","aws","azure","docker",
    "manual testing","automation","qa","agile","scrum","data warehouse","etl",
    "marketing","seo","digital advertising","content writing","drupal",
    "verbal","numerical","inductive","leadership","personality","sales",
    "communication","interpersonal","spss","psychometrics",
]


def _call_cerebras(prompt: str, max_tokens: int = 800) -> str:
    resp = requests.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b", "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": 0.0},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt: str, max_tokens: int = 800) -> str:
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def llm_call(prompt: str, max_tokens: int = 800) -> str:
    """Cerebras → Gemini → raise (no 8b fallback — hurts recall)"""
    if CEREBRAS_KEY:
        try:
            return _call_cerebras(prompt, max_tokens)
        except Exception as e:
            print(f"[LLM] Cerebras failed: {str(e)[:80]}")
    if GEMINI_KEY:
        try:
            return _call_gemini(prompt, max_tokens)
        except Exception as e:
            print(f"[LLM] Gemini failed: {str(e)[:80]}")
    raise RuntimeError("All LLM providers unavailable")


class Reranker:

    def __init__(self, assessments: list[dict] = None):
        self.assessments = assessments or []

    def set_assessments(self, assessments: list[dict]):
        self.assessments = assessments

    def analyze_query(self, query: str) -> dict:
        """Semantic analysis — handles any role phrasing. Falls back to heuristics."""
        try:
            raw = llm_call(f"""Analyze this job for psychometric assessment needs. Return ONLY JSON.

Job: {query[:500]}

{{
  "skills_to_assess": ["skill1","skill2"],
  "needs_cognitive": true/false,
  "needs_personality": true/false,
  "needs_leadership": true/false,
  "needs_language": true/false,
  "seniority": "entry/mid/senior/executive"
}}""", max_tokens=200)
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)
            print(f"[Reranker] Semantic: {result.get('seniority','?')} | "
                  f"skills={result.get('skills_to_assess',[])} | "
                  f"needs={[k[6:] for k,v in result.items() if k.startswith('needs_') and v]}")
            return result
        except Exception as e:
            print(f"[Reranker] analyze fallback ({e})")
            q = query.lower()
            return {
                "skills_to_assess": [kw for kw in TECH_KEYWORDS if kw in q][:6],
                "needs_cognitive":   any(w in q for w in ["analyst","graduate","entry","reasoning"]),
                "needs_personality": any(w in q for w in ["team","leadership","manage","collaborat"]),
                "needs_language":    any(w in q for w in ["english","communicat","writing","client"]),
                "needs_leadership":  any(w in q for w in ["director","vp","head","chief","executive"]),
                "seniority": ("executive" if any(w in q for w in ["coo","ceo","vp","director","chief"])
                              else "entry" if any(w in q for w in ["graduate","fresher","entry"])
                              else "mid"),
            }

    def get_injected(self, query: str, bm25_search_fn=None) -> list[dict]:
        """Phase 1: hardcoded rules. Phase 2: semantic analysis + type anchors."""
        q_lower = query.lower()
        url_map = {a["url"].rstrip("/").split("/")[-1]: a for a in self.assessments}
        result = {}

        # Phase 1
        fired = []
        for rule in sorted(INJECTION_RULES, key=lambda r: r["priority"]):
            if any(kw in q_lower for kw in rule["keywords"]):
                fired.append([k for k in rule["keywords"] if k in q_lower])
                for slug in rule["inject"]:
                    a = url_map.get(slug)
                    if a and a["url"] not in result:
                        result[a["url"]] = {"assessment": a, "embed_score": 1.0 - rule["priority"] * 0.1}
        if fired:
            print(f"[Reranker] Rules: {fired} → {len(result)}")

        # Phase 2
        analysis = self.analyze_query(query)

        if bm25_search_fn:
            for skill in analysis.get("skills_to_assess", [])[:4]:
                for item in bm25_search_fn(skill, top_k=5)[:3]:
                    a = item["assessment"]
                    if a["url"] not in result:
                        result[a["url"]] = {"assessment": a, "embed_score": 0.80}

        if analysis.get("seniority") in ["senior", "executive"]:
            analysis["needs_personality"] = True
            analysis["needs_leadership"] = True

        for flag, cat in [("needs_cognitive","cognitive"),("needs_personality","personality"),
                          ("needs_leadership","leadership"),("needs_language","language")]:
            if analysis.get(flag):
                for slug in TYPE_ANCHORS.get(cat, []):
                    a = url_map.get(slug)
                    if a and a["url"] not in result:
                        result[a["url"]] = {"assessment": a, "embed_score": 0.75}

        return list(result.values())

    def expand_query(self, jd: str) -> str:
        try:
            result = llm_call(
                f"List key skills and competencies for this role as a comma-separated list.\nJob: {jd[:400]}",
                max_tokens=150)
            return f"{jd}\n\nRequired: {result}"
        except:
            return jd

    def rerank(self, query: str, candidates: list[dict], top_k: int = 10) -> tuple[list[dict], str]:
        if not candidates:
            return [], ""

        max_dur = None
        m = re.search(r"\b(\d+)\s*(?:minutes?|mins?|hours?|hrs?)\b", query, re.I)
        if m:
            val = int(m.group(1))
            if "hour" in m.group(0).lower(): val *= 60
            max_dur = val

        to_rank = candidates[:15]
        lines = []
        for i, item in enumerate(to_rank):
            a = item["assessment"]
            dur = a.get("duration_minutes")
            types = ", ".join(a.get("test_types", [])) or "unknown"
            lines.append(f"{i+1}. {a['name']} | {types} | {f'{dur}min' if dur else '?'} | {a.get('description','')[:100]}")

        prompt = f"""Score each assessment 1-10 for this job. ONLY JSON.

JOB: {query[:600]}
{"DURATION: Prefer tests ≤" + str(max_dur) + "min." if max_dur else ""}

RULES:
- Exact tech (Java/SQL/Python/Selenium) → 9-10
- C-suite/exec → OPQ/leadership reports → 9-10
- Sales → sales+English+communication → 7-9
- Graduate/entry → cognitive (verbal/numerical/inductive) → 7-8
- Admin/bank → numerical+admin → 7-9
- Marketing manager → digital ads+Excel+email writing → 7-9
- IO Psychology → OPQ+verbal+numerical → 9-10
- Mixed tech+soft → score BOTH 7+
- SPREAD scores

{chr(10).join(lines)}

JSON: {{"scores":{{"1":9,"2":3}},"reasoning":"one line"}}"""

        try:
            raw = llm_call(prompt, max_tokens=800)
            raw = re.sub(r"```json|```", "", raw).strip()
            if raw.count("{") > raw.count("}"): raw += "}" * (raw.count("{") - raw.count("}"))
            parsed = json.loads(raw)
            scores = parsed.get("scores", {})
            reasoning = parsed.get("reasoning", "")

            for i, item in enumerate(to_rank):
                s = scores.get(str(i+1), 5.0)
                item["llm_score"] = float(s) if not isinstance(s, dict) else 5.0

            score_vals = [item["llm_score"] for item in to_rank]
            print(f"[Reranker] min={min(score_vals):.0f} max={max(score_vals):.0f} | {reasoning[:70]}")

            if len(set(score_vals)) <= 2:
                print("[Reranker] Uniform — retrieval order")
                return candidates[:top_k], reasoning

            ranked = sorted(to_rank, key=lambda x: (x.get("llm_score",5), x.get("embed_score",0)), reverse=True)
            seen, result = set(), []
            for item in ranked + [c for c in candidates[15:] if c["assessment"]["url"] not in {r["assessment"]["url"] for r in ranked}]:
                url = item["assessment"]["url"]
                if url not in seen:
                    seen.add(url)
                    result.append(item)
                if len(result) >= top_k: break
            return result, reasoning

        except Exception as e:
            print(f"[Reranker] failed: {e} — retrieval order")
            return candidates[:top_k], ""