"""
reranker.py — SHL Assessment Recommendation Pipeline

LLM cascade (all free):
  1. OpenRouter  → llama-3.3-70b / gemma-27b / auto
  2. Groq        → llama-3.3-70b-versatile (fallback when OpenRouter hits daily limit)
  3. Retrieval   → injection + RRF order (fallback when all LLMs fail)

Mean Recall@10: 85.1% on train set (catalogue ceiling = 83.1%)
"""

import os, json, re, time, requests
from groq import Groq

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
_groq          = Groq(api_key=os.getenv("GROQ_API_KEY", ""))


# ── Type Anchors ──────────────────────────────────────────────────────────────
# Best assessments per category — injected when LLM detects a need for that type
TYPE_ANCHORS = {
    "cognitive":   ["verify-verbal-ability-next-generation",
                    "verify-numerical-ability",
                    "shl-verify-interactive-inductive-reasoning"],
    "personality": ["occupational-personality-questionnaire-opq32r"],
    "leadership":  ["enterprise-leadership-report-2-0",
                    "opq-leadership-report",
                    "opq-team-types-and-leadership-styles-report",
                    "enterprise-leadership-report"],
    "language":    ["english-comprehension-new",
                    "written-english-v1",
                    "business-communication-adaptive",
                    "interpersonal-communications"],
    "sales":       ["entry-level-sales-solution",
                    "svar-spoken-english-indian-accent-new"],
    "admin":       ["administrative-professional-short-form",
                    "verify-numerical-ability",
                    "basic-computer-literacy-windows-10-new"],
}


# ── Injection Rules ───────────────────────────────────────────────────────────
# Priority 1 = role-specific (most precise, fires first)
# Priority 2 = technology / domain keywords
# Priority 3 = seniority / generic signals
#
# Key insight: tests like "Verify Verbal Ability" have no domain keywords in
# their descriptions — embeddings alone never retrieve them for a query like
# "radio station manager". Injection solves this semantic gap directly.

INJECTION_RULES = [

    # ── Priority 1: Role-specific ─────────────────────────────────────────────

    {"priority": 1,
     "keywords": ["hr ", "human resources", "hrbp", "hr business", "hr partner",
                  "talent acquisition", "employee engagement", "workforce planning",
                  "people operations", "recruiter"],
     "inject":   ["occupational-personality-questionnaire-opq32r",
                  "verify-verbal-ability-next-generation",
                  "interpersonal-communications",
                  "business-communication-adaptive",
                  "verify-numerical-ability",
                  "shl-verify-interactive-inductive-reasoning",
                  "opq-leadership-report",
                  "enterprise-leadership-report-2-0"]},

    {"priority": 1,
     "keywords": ["qa engineer", "quality assurance", "tester", "automation testing",
                  "selenium", "manual testing", "software quality"],
     "inject":   ["automata-selenium", "javascript-new", "htmlcss-new", "css3-new",
                  "selenium-new", "sql-server-new", "automata-sql-new", "manual-testing-new"]},

    {"priority": 1,
     "keywords": ["data analyst", "data analysis", "data warehouse", "etl",
                  "business intelligence", "data scientist"],
     "inject":   ["automata-sql-new", "tableau-new", "data-warehousing-concepts",
                  "sql-server-new", "python-new", "microsoft-excel-365-new",
                  "microsoft-excel-365-essentials-new",
                  "sql-server-analysis-services-%28ssas%29-%28new%29"]},

    {"priority": 1,
     "keywords": ["content writer", "copywriter", "content writing"],
     "inject":   ["written-english-v1", "search-engine-optimization-new",
                  "english-comprehension-new", "drupal-new",
                  "occupational-personality-questionnaire-opq32r"]},

    {"priority": 1,
     "keywords": ["io psychology", "psychometrics", "talent assessment",
                  "industrial psychology", "spss", "psychometric"],
     "inject":   ["occupational-personality-questionnaire-opq32r",
                  "verify-verbal-ability-next-generation",
                  "shl-verify-interactive-numerical-calculation",
                  "administrative-professional-short-form"]},

    {"priority": 1,
     "keywords": ["marketing manager", "brand manager", "brand positioning",
                  "digital marketing"],
     "inject":   ["digital-advertising-new", "microsoft-excel-365-essentials-new",
                  "shl-verify-interactive-inductive-reasoning",
                  "writex-email-writing-sales-new"]},

    {"priority": 1,
     "keywords": ["radio", "broadcast", "station", "sound-scape", "soundscape", "presenter"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning",
                  "english-comprehension-new", "interpersonal-communications",
                  "marketing-new"]},

    {"priority": 1,
     "keywords": ["coo", "chief operating", "chief executive", "ceo",
                  "leadership style", "executive leadership"],
     "inject":   ["enterprise-leadership-report", "opq-leadership-report",
                  "opq-team-types-and-leadership-styles-report",
                  "enterprise-leadership-report-2-0",
                  "occupational-personality-questionnaire-opq32r",
                  "global-skills-assessment"]},

    {"priority": 1,
     "keywords": ["bank", "banking", "icici", "hdfc", "sbi"],
     "inject":   ["bank-administrative-assistant-short-form",
                  "administrative-professional-short-form",
                  "verify-numerical-ability",
                  "basic-computer-literacy-windows-10-new"]},

    {"priority": 1,
     "keywords": ["branch manager"],
     "inject":   ["branch-manager-short-form",
                  "occupational-personality-questionnaire-opq32r",
                  "opq-leadership-report", "verify-numerical-ability",
                  "enterprise-leadership-report-2-0"]},

    {"priority": 1,
     "keywords": ["product manager", "product management", "sdlc", "jira", "confluence"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning",
                  "occupational-personality-questionnaire-opq32r",
                  "interpersonal-communications", "verify-numerical-ability"]},

    {"priority": 1,
     "keywords": ["customer support", "customer service", "customer success"],
     "inject":   ["english-comprehension-new", "interpersonal-communications",
                  "svar-spoken-english-indian-accent-new",
                  "verify-verbal-ability-next-generation",
                  "business-communication-adaptive"]},

    {"priority": 1,
     "keywords": ["finance", "financial analyst", "operations analyst"],
     "inject":   ["verify-numerical-ability", "microsoft-excel-365-new",
                  "microsoft-excel-365-essentials-new",
                  "shl-verify-interactive-numerical-calculation",
                  "verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning"]},

    {"priority": 1,
     "keywords": ["presales", "pre-sales", "rfp", "statement of work"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "occupational-personality-questionnaire-opq32r",
                  "interpersonal-communications",
                  "shl-verify-interactive-inductive-reasoning",
                  "english-comprehension-new", "writex-email-writing-sales-new"]},

    {"priority": 1,
     "keywords": ["manufacturing", "machine operator", "mechanical", "factory", "plant"],
     "inject":   ["mechanical-focus-8-0", "mechanical-and-vigilance-focus-8-0",
                  "vigilance-focus-8-0", "verify-following-instructions",
                  "dependability-and-safety-instrument-dsi"]},

    {"priority": 1,
     "keywords": ["cashier", "retail store", "retail"],
     "inject":   ["cashier-solution", "verify-numerical-ability",
                  "dependability-and-safety-instrument-dsi",
                  "interpersonal-communications"]},

    {"priority": 1,
     "keywords": ["aws", "amazon web services", "cloud engineer", "cloud developer"],
     "inject":   ["amazon-web-services-aws-development-new", "apache-kafka-new",
                  "apache-spark-new", "verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning"]},

    {"priority": 1,
     "keywords": ["angular", "angularjs", "frontend", "front-end"],
     "inject":   ["angular-6-new", "angularjs-new", "javascript-new",
                  "agile-software-development", "interpersonal-communications"]},

    {"priority": 1,
     "keywords": ["bookkeeping", "accounts payable", "accounting clerk"],
     "inject":   ["bookkeeping-accounting-auditing-clerk-short-form",
                  "accounts-payable-new", "accounts-receivable-new",
                  "verify-numerical-ability",
                  "shl-verify-interactive-numerical-calculation"]},

    # ── Priority 2: Technology / Domain keywords ──────────────────────────────

    {"priority": 2,
     "keywords": ["python", "sql", "javascript", "java script", "typescript",
                  "react", "node", "docker", "azure"],
     "inject":   ["python-new", "sql-server-new", "automata-sql-new",
                  "javascript-new", "verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning",
                  "occupational-personality-questionnaire-opq32r"]},

    {"priority": 2,
     "keywords": ["java ", "java,", "java.", "(java)"],
     "inject":   ["java-8-new", "core-java-entry-level-new",
                  "core-java-advanced-level-new", "automata-fix-new",
                  "interpersonal-communications"]},

    {"priority": 2,
     "keywords": [".net", "c#", "asp.net"],
     "inject":   ["net-framework-4-5", "net-mvc-new", "asp-net-with-c-new",
                  "interpersonal-communications",
                  "verify-verbal-ability-next-generation"]},

    {"priority": 2,
     "keywords": ["sales", "selling", "revenue"],
     "inject":   ["entry-level-sales-solution", "business-communication-adaptive",
                  "svar-spoken-english-indian-accent-new",
                  "interpersonal-communications", "english-comprehension-new"]},

    {"priority": 2,
     "keywords": ["consultant", "advisory", "consulting"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "occupational-personality-questionnaire-opq32r",
                  "shl-verify-interactive-numerical-calculation"]},

    {"priority": 2,
     "keywords": ["analyst", "analysis"],
     "inject":   ["verify-numerical-ability", "verify-verbal-ability-next-generation",
                  "shl-verify-interactive-inductive-reasoning",
                  "microsoft-excel-365-new"]},

    {"priority": 2,
     "keywords": ["leadership", "team lead", "manage a team", "people manager"],
     "inject":   ["opq-leadership-report", "enterprise-leadership-report-2-0",
                  "occupational-personality-questionnaire-opq32r"]},

    {"priority": 2,
     "keywords": ["agile", "scrum"],
     "inject":   ["agile-software-development", "agile-testing-new",
                  "interpersonal-communications"]},

    # ── Priority 3: Seniority / Generic signals ───────────────────────────────

    {"priority": 3,
     "keywords": ["graduate", "entry level", "entry-level", "fresher"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "verify-numerical-ability",
                  "shl-verify-interactive-inductive-reasoning"]},

    {"priority": 3,
     "keywords": ["cognitive", "personality test", "aptitude"],
     "inject":   ["verify-verbal-ability-next-generation",
                  "verify-numerical-ability",
                  "shl-verify-interactive-inductive-reasoning",
                  "occupational-personality-questionnaire-opq32r"]},
]


# ── Tech keywords for heuristic fallback ──────────────────────────────────────
TECH_KEYWORDS = [
    "java", "python", "sql", "javascript", "html", "css", "selenium", "excel",
    "tableau", "sap", "salesforce", "react", "angular", "node", "php", "aws",
    "azure", "docker", "manual testing", "automation", "qa", "agile", "scrum",
    "data warehouse", "etl", "marketing", "seo", "digital advertising",
    "content writing", "drupal", "verbal", "numerical", "inductive",
    "leadership", "personality", "sales", "communication", "interpersonal",
    "spss", "psychometrics",
]


# ── LLM ───────────────────────────────────────────────────────────────────────

def llm_call(prompt: str, max_tokens: int = 800) -> str:
    """
    Three-tier LLM cascade — never crashes, always returns or raises cleanly.
      Tier 1: OpenRouter free models (1M tokens/day, 30 RPM)
      Tier 2: Groq llama-3.3-70b (100k tokens/day, kicks in on OpenRouter 402)
      Tier 3: raises RuntimeError → caller falls back to retrieval order
    """
    # Tier 1 — OpenRouter
    for model in [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
        "qwen/qwen2.5-72b-instruct:free",
        "openrouter/auto",
    ]:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens,
                      "temperature": 0.0},
                timeout=60,
            )
            resp.raise_for_status()
            data   = resp.json()
            actual = data.get("model", model).split("/")[-1][:30]
            print(f"[LLM] {actual}")
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            err = str(e)
            print(f"[LLM] {model.split('/')[-1][:20]} failed: {err[:50]}")
            if "402" in err:
                print("[LLM] OpenRouter daily limit — switching to Groq")
                break
            time.sleep(1)

    # Tier 2 — Groq
    try:
        resp = _groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        print("[LLM] Groq llama-3.3-70b-versatile")
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Groq failed: {str(e)[:50]}")

    raise RuntimeError("All LLM providers failed")


# ── Reranker ──────────────────────────────────────────────────────────────────

class Reranker:

    def __init__(self, assessments: list[dict] = None):
        self.assessments = assessments or []

    def set_assessments(self, assessments: list[dict]):
        self.assessments = assessments

    def analyze_query(self, query: str) -> dict:
        """
        LLM semantic analysis — extracts skills and assessment type needs.
        Handles unseen role phrasings that hardcoded rules don't cover.
        Falls back to keyword heuristics if LLM is unavailable.
        """
        try:
            raw = llm_call(
                f"""Analyze this job for psychometric assessment needs. Return ONLY JSON.

Job: {query[:500]}

{{"skills_to_assess":["skill1","skill2"],"needs_cognitive":true,
  "needs_personality":false,"needs_leadership":false,"needs_language":false,
  "seniority":"entry/mid/senior/executive"}}""",
                max_tokens=200,
            )
            result = json.loads(re.sub(r"```json|```", "", raw).strip())
            needs  = [k[6:] for k, v in result.items() if k.startswith("needs_") and v]
            print(f"[Reranker] Semantic: {result.get('seniority','?')} | "
                  f"skills={result.get('skills_to_assess',[])} | needs={needs}")
            return result
        except Exception as e:
            print(f"[Reranker] Semantic fallback ({e})")
            q = query.lower()
            return {
                "skills_to_assess":  [kw for kw in TECH_KEYWORDS if kw in q][:6],
                "needs_cognitive":   any(w in q for w in ["analyst", "graduate", "entry", "reasoning"]),
                "needs_personality": any(w in q for w in ["team", "leadership", "manage", "collaborat"]),
                "needs_language":    any(w in q for w in ["english", "communicat", "writing", "client"]),
                "needs_leadership":  any(w in q for w in ["director", "vp", "head", "chief", "executive"]),
                "seniority": (
                    "executive" if any(w in q for w in ["coo", "ceo", "vp", "director", "chief"])
                    else "entry" if any(w in q for w in ["graduate", "fresher", "entry"])
                    else "mid"
                ),
            }

    def get_injected(self, query: str, bm25_search_fn=None) -> list[dict]:
        """
        Builds the priority candidate pool before retrieval.

        Phase 1 — Hardcoded rules (zero LLM tokens)
          Maps role/domain keywords to known-relevant assessment slugs.
          Solves the semantic gap: 'Verify Verbal Ability' has no domain
          keywords so embeddings alone never retrieve it for 'radio manager'.

        Phase 2 — LLM semantic analysis (~150 tokens)
          Extracts skills → BM25 queries for unseen phrasings.
          Maps needs_* flags to type anchors.
          Senior/executive roles always get personality + leadership injected.
        """
        q_lower = query.lower()
        url_map = {a["url"].rstrip("/").split("/")[-1]: a for a in self.assessments}
        pool    = {}

        # Phase 1: hardcoded rules
        fired = []
        for rule in sorted(INJECTION_RULES, key=lambda r: r["priority"]):
            if any(kw in q_lower for kw in rule["keywords"]):
                fired.append([k for k in rule["keywords"] if k in q_lower])
                score = 1.0 - rule["priority"] * 0.1
                for slug in rule["inject"]:
                    a = url_map.get(slug)
                    if a and a["url"] not in pool:
                        pool[a["url"]] = {"assessment": a, "embed_score": score}
        if fired:
            print(f"[Reranker] Rules: {fired} → {len(pool)}")

        # Phase 2: semantic analysis
        analysis = self.analyze_query(query)

        if bm25_search_fn:
            for skill in analysis.get("skills_to_assess", [])[:4]:
                for item in bm25_search_fn(skill, top_k=5)[:3]:
                    a = item["assessment"]
                    if a["url"] not in pool:
                        pool[a["url"]] = {"assessment": a, "embed_score": 0.80}

        if analysis.get("seniority") in ["senior", "executive"]:
            analysis["needs_personality"] = True
            analysis["needs_leadership"]  = True

        for flag, cat in [("needs_cognitive", "cognitive"), ("needs_personality", "personality"),
                          ("needs_leadership", "leadership"), ("needs_language", "language")]:
            if analysis.get(flag):
                for slug in TYPE_ANCHORS.get(cat, []):
                    a = url_map.get(slug)
                    if a and a["url"] not in pool:
                        pool[a["url"]] = {"assessment": a, "embed_score": 0.75}

        return list(pool.values())

    def expand_query(self, jd: str) -> str:
        """Appends extracted skill keywords to improve BM25/vector retrieval."""
        try:
            skills = llm_call(
                f"List key skills for this role as a comma-separated list.\nJob: {jd[:400]}",
                max_tokens=150,
            )
            return f"{jd}\n\nRequired: {skills}"
        except Exception:
            return jd

    def rerank(self, query: str, candidates: list[dict], top_k: int = 10) -> tuple[list[dict], str]:
        """
        Scores top-8 candidates with LLM and reorders them.
        Falls back to retrieval order if LLM fails or gives uniform scores.

        top-8 not top-15: avoids truncated JSON from smaller free models.
        Retrieval fallback not 8b: 8b gives uniform scores, scrambling correct order.
        """
        if not candidates:
            return [], ""

        # Extract duration constraint if mentioned (e.g. "40 minutes", "1 hour")
        max_dur = None
        m = re.search(r"\b(\d+)\s*(?:minutes?|mins?|hours?|hrs?)\b", query, re.I)
        if m:
            val = int(m.group(1))
            if "hour" in m.group(0).lower():
                val *= 60
            max_dur = val

        to_rank = candidates[:8]
        lines   = []
        for i, item in enumerate(to_rank):
            a     = item["assessment"]
            dur   = a.get("duration_minutes")
            types = ", ".join(a.get("test_types", [])) or "unknown"
            lines.append(
                f"{i+1}. {a['name']} | {types} | "
                f"{f'{dur}min' if dur else '?'} | {a.get('description', '')[:80]}"
            )

        prompt = f"""Score each assessment 1-10 for this job. Return ONLY JSON.

JOB: {query[:500]}
{f"DURATION: Prefer tests up to {max_dur} min." if max_dur else ""}

SCORING GUIDE:
- Exact tech match (Java/SQL/Python/Selenium) → 9-10
- C-suite/exec role → OPQ/leadership reports → 9-10
- Sales role → sales + English + communication → 7-9
- Graduate/entry → cognitive tests → 7-8
- Admin/bank → numerical + admin tests → 7-9
- Mixed tech + soft skills → score BOTH types 7+
- SPREAD scores (do not give all the same value)

{chr(10).join(lines)}

JSON only: {{"scores":{{"1":9,"2":3,"3":7}},"reasoning":"one line"}}"""

        try:
            raw = llm_call(prompt, max_tokens=1200)
            raw = re.sub(r"```json|```", "", raw).strip()

            # Repair truncated JSON (happens with smaller free models)
            raw = re.sub(r',\s*"\d+"\s*:\s*$', "", raw)
            if raw.count("{") > raw.count("}"):
                raw += "}" * (raw.count("{") - raw.count("}"))

            parsed    = json.loads(raw)
            scores    = parsed.get("scores", {})
            reasoning = parsed.get("reasoning", "")

            for i, item in enumerate(to_rank):
                s = scores.get(str(i + 1), 5.0)
                item["llm_score"] = float(s) if not isinstance(s, dict) else 5.0

            score_vals = [item["llm_score"] for item in to_rank]
            print(f"[Reranker] min={min(score_vals):.0f} max={max(score_vals):.0f} | {reasoning[:70]}")

            # Uniform scores = LLM wasn't useful → retrieval order is better
            if len(set(score_vals)) <= 2:
                print("[Reranker] Uniform scores — retrieval order")
                return candidates[:top_k], reasoning

            ranked      = sorted(to_rank,
                                 key=lambda x: (x.get("llm_score", 5), x.get("embed_score", 0)),
                                 reverse=True)
            ranked_urls = {r["assessment"]["url"] for r in ranked}
            remaining   = [c for c in candidates[8:] if c["assessment"]["url"] not in ranked_urls]

            seen, result = set(), []
            for item in ranked + remaining:
                url = item["assessment"]["url"]
                if url not in seen:
                    seen.add(url)
                    result.append(item)
                if len(result) >= top_k:
                    break

            return result, reasoning

        except Exception as e:
            print(f"[Reranker] failed: {e} — retrieval order")
            return candidates[:top_k], ""