"""
Groq AI Layer for Operational Excellence
==========================================
Turns the Operational Excellence engine's static templates (5 Whys,
Fishbone bucketing, DMAIC Improve/Control, Recommendations) into
LLM-generated output via Groq's free tier, while keeping the Tier 1/2/3
data-honesty system intact and degrading gracefully to the old static
templates if the API is unavailable, rate-limited, or returns something
unusable.

MODEL NOTE (as of mid-2026)
----------------------------
llama3-8b-8192 / llama3-70b-8192 have been fully decommissioned by Groq,
and llama-3.1-8b-instant / llama-3.3-70b-versatile are in the process of
being deprecated. Current recommended free-tier chat models are the
OpenAI open-weight models Groq now hosts:

    openai/gpt-oss-20b   - default here. Fast, cheap, generous free-tier
                            token limits, JSON mode support. Plenty for
                            short structured RCA/DMAIC text.
    openai/gpt-oss-120b  - higher quality if you have headroom; set
                            GROQ_MODEL=openai/gpt-oss-120b to switch.

Check https://console.groq.com/docs/models for the current list if
either of these also gets retired later — this module only needs a
model name change (GROQ_MODEL env var / MODEL constant below).

TOKEN / RATE-LIMIT STRATEGY
----------------------------
Rather than four separate calls (5 Whys, Fishbone, DMAIC, Recommendations)
this module makes ONE combined call per analysis run and caches the
result against a compact signature of the KPIs/RCA (not the raw
dataframes). Streamlit reruns the whole script on every widget
interaction, so without this caching a single page visit could burn
10-20+ calls; with it, a given dataset/analysis only costs one call
until something material about the numbers changes.
"""

import hashlib
import json
import os

import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECS = 20
MAX_TOKENS = 900
TEMPERATURE = 0.35

FISHBONE_BUCKETS = ["People", "Process", "Machine", "Material", "Environment", "Management"]

TIER_LABEL = {0: "no signal", 1: "real / directly observed", 2: "partially inferred", 3: "estimated / illustrative"}

TIER_INSTRUCTION = {
    1: "This is real, directly observed data. Write with normal confidence.",
    2: "This is partially inferred from contextual signals (weather/traffic/warehouse columns), "
       "not an explicit delay-reason field. Hedge slightly — 'appears to', 'is likely driven by' — "
       "rather than stating it as certain fact.",
    3: "This is an ESTIMATED, illustrative split with no real delay-reason signal in the dataset. "
       "You MUST make this explicit: mention 'estimated' or 'illustrative' in root_cause and keep "
       "recommendations generic/directional rather than implying they're derived from this specific data.",
}

_SYSTEM_PROMPT = (
    "You are a Lean Six Sigma / supply-chain operations analyst inside a logistics analytics tool "
    "called RouteIQ. You are given a compact JSON summary of a delay root-cause analysis. "
    "Respond with ONLY a single valid JSON object matching the schema in the user message — no "
    "markdown, no code fences, no commentary before or after. Keep every text field to 1-2 concise "
    "sentences. Never invent specific numbers that aren't derivable from the input; when data is "
    "estimated, say so instead of stating it as fact."
)

# In-process cache used when Streamlit's own cache_data isn't available
# (e.g. under pytest / outside a Streamlit runtime).
_LOCAL_CACHE = {}

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except Exception:  # pragma: no cover - keeps this importable in plain pytest
    _HAS_STREAMLIT = False

# Tracks the outcome of the most recent call so the UI can show a small
# "AI-enhanced" / "static fallback" indicator without changing the shape
# of the dicts every other function already returns.
_LAST_STATUS = {"used_ai": False, "model": None, "reason": None}


def get_ai_status() -> dict:
    """Returns info about the most recent Groq call attempt, for a UI badge."""
    return dict(_LAST_STATUS)


def _get_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    if _HAS_STREAMLIT:
        try:
            return st.secrets.get("GROQ_API_KEY")
        except Exception:
            return None
    return None


def _get_model():
    return os.environ.get("GROQ_MODEL", DEFAULT_MODEL)


# ─────────────────────────────────────────────
# SIGNATURE — small, hashable, JSON-serializable summary of the run
# ─────────────────────────────────────────────
def build_signature(kpis: dict, rca: dict, cols: dict, top_n_causes: int = 6) -> dict:
    pareto_df = rca.get("pareto_df")
    causes = []
    if pareto_df is not None and len(pareto_df):
        for _, row in pareto_df.head(top_n_causes).iterrows():
            causes.append({
                "cause": str(row["Cause"]),
                "count": int(row["Count"]),
                "pct": float(row["Pct"]),
            })

    return {
        "tier": rca.get("tier"),
        "method": rca.get("method"),
        "top_cause": rca.get("top_cause"),
        "causes": causes,
        "otd_pct": kpis.get("otd_pct"),
        "n_delayed": kpis.get("n_delayed"),
        "n_shipments": kpis.get("n_shipments"),
        "tat_hours": kpis.get("tat_hours") if kpis.get("tat_available") else None,
        "cost_per_shipment": kpis.get("cost_per_shipment") if kpis.get("cost_available") else None,
        "util_pct": kpis.get("util_pct") if kpis.get("util_available") else None,
        "esg_score": kpis.get("esg_score") if kpis.get("carbon_available") else None,
        "delay_cost": kpis.get("delay_cost") if kpis.get("delay_cost_available") else None,
    }


def _signature_key(signature: dict) -> str:
    return json.dumps(signature, sort_keys=True, default=str)


# ─────────────────────────────────────────────
# PROMPT BUILDING
# ─────────────────────────────────────────────
def _build_user_prompt(signature: dict) -> str:
    tier = signature.get("tier") or 0
    tier_note = TIER_INSTRUCTION.get(tier, "Treat this as low-confidence data; hedge accordingly.")

    kpi_bits = [f"OTD {signature.get('otd_pct')}%",
                f"{signature.get('n_delayed')}/{signature.get('n_shipments')} shipments delayed"]
    if signature.get("tat_hours") is not None:
        kpi_bits.append(f"avg TAT {signature['tat_hours']}h")
    if signature.get("cost_per_shipment") is not None:
        kpi_bits.append(f"cost/shipment {signature['cost_per_shipment']}")
    if signature.get("util_pct") is not None:
        kpi_bits.append(f"fleet utilization {signature['util_pct']}%")
    if signature.get("esg_score") is not None:
        kpi_bits.append(f"ESG score {signature['esg_score']}/100")
    if signature.get("delay_cost") is not None:
        kpi_bits.append(f"estimated delay cost {signature['delay_cost']}")

    causes = signature.get("causes") or []
    cause_names = [c["cause"] for c in causes]

    schema = {
        "root_cause": "one-sentence systemic root cause statement for the top cause",
        "whys": ["why 1", "why 2", "why 3", "why 4", "why 5"],
        "fishbone": {c: "People|Process|Machine|Material|Environment|Management" for c in cause_names} or
                    {"<cause name>": "People|Process|Machine|Material|Environment|Management"},
        "improve": "1-2 sentence tailored DMAIC Improve action",
        "control": "1-2 sentence tailored DMAIC Control monitoring plan",
        "recommendations": [
            {"cause": c, "text": "tailored recommendation", "reduction_pct": 0.1} for c in cause_names
        ] or [{"cause": "<cause name>", "text": "tailored recommendation", "reduction_pct": 0.1}],
    }

    return (
        f"Data signal tier: {tier} ({TIER_LABEL.get(tier, 'unknown')}). "
        f"Attribution method: {signature.get('method')}\n"
        f"KPI snapshot: {', '.join(kpi_bits)}.\n"
        f"Pareto delay causes (top to bottom): {json.dumps(causes)}\n"
        f"Top cause under investigation: {signature.get('top_cause')}\n\n"
        f"{tier_note}\n\n"
        "Return ONLY a JSON object with exactly this shape (values are examples of the expected "
        f"type/format, not literal text to reuse): {json.dumps(schema)}\n"
        "The 'whys' list must progressively dig deeper (Why 1 = surface symptom, Why 5 = systemic "
        "root cause) and reference the KPI numbers where it strengthens the point. "
        "'fishbone' must include every cause name listed above, each mapped to exactly one of the "
        "six categories. 'recommendations' must include one entry per cause listed above, with "
        "reduction_pct as a realistic conservative decimal fraction between 0.02 and 0.30 "
        "representing the share of that cause's delays the fix could plausibly remove."
    )


# ─────────────────────────────────────────────
# RAW GROQ CALL
# ─────────────────────────────────────────────
def _call_groq(signature: dict):
    api_key = _get_api_key()
    if not api_key:
        _LAST_STATUS.update(used_ai=False, model=None, reason="no GROQ_API_KEY configured")
        return None

    model = _get_model()
    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(signature)},
                ],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "response_format": {"type": "json_object"},
            },
            timeout=REQUEST_TIMEOUT_SECS,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except requests.exceptions.RequestException as e:
        _LAST_STATUS.update(used_ai=False, model=model, reason=f"network/API error: {e}")
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        _LAST_STATUS.update(used_ai=False, model=model, reason=f"unparseable response: {e}")
        return None

    validated = _validate(parsed, signature)
    if validated is None:
        _LAST_STATUS.update(used_ai=False, model=model, reason="response failed schema validation")
        return None

    _LAST_STATUS.update(used_ai=True, model=model, reason=None)
    return validated


def _validate(parsed: dict, signature: dict):
    """Defensive checks so a malformed/partial LLM response never reaches the UI raw."""
    if not isinstance(parsed, dict):
        return None

    causes = [c["cause"] for c in (signature.get("causes") or [])]

    whys = parsed.get("whys")
    if not isinstance(whys, list) or len(whys) < 3:
        return None
    whys = [str(w).strip() for w in whys if str(w).strip()][:5]

    root_cause = str(parsed.get("root_cause") or "").strip()
    if not root_cause:
        return None

    fishbone_raw = parsed.get("fishbone") or {}
    fishbone = {}
    if isinstance(fishbone_raw, dict):
        for cause, bucket in fishbone_raw.items():
            bucket = str(bucket).strip().title()
            if bucket in FISHBONE_BUCKETS:
                fishbone[str(cause)] = bucket

    improve = str(parsed.get("improve") or "").strip()
    control = str(parsed.get("control") or "").strip()

    recs_raw = parsed.get("recommendations")
    recs = []
    if isinstance(recs_raw, list):
        for r in recs_raw:
            if not isinstance(r, dict):
                continue
            cause = str(r.get("cause") or "").strip()
            text = str(r.get("text") or "").strip()
            try:
                reduction = float(r.get("reduction_pct"))
            except (TypeError, ValueError):
                continue
            if not cause or not text:
                continue
            reduction = max(0.02, min(reduction, 0.30))
            recs.append({"cause": cause, "text": text, "reduction_pct": round(reduction, 3)})

    # Require at least the essentials to call this a usable AI response.
    if not whys or not root_cause or not improve or not control:
        return None

    return {
        "root_cause": root_cause,
        "whys": whys,
        "fishbone": fishbone,        # cause -> bucket, may be partial; caller fills gaps
        "improve": improve,
        "control": control,
        "recommendations": recs,     # may be shorter than `causes`; caller fills gaps
    }


# ─────────────────────────────────────────────
# CACHED ENTRY POINT
# ─────────────────────────────────────────────
if _HAS_STREAMLIT:
    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached_call(signature_json: str):
        return _call_groq(json.loads(signature_json))
else:
    def _cached_call(signature_json: str):
        key = hashlib.sha256(signature_json.encode()).hexdigest()
        if key not in _LOCAL_CACHE:
            _LOCAL_CACHE[key] = _call_groq(json.loads(signature_json))
        return _LOCAL_CACHE[key]


def get_ai_analysis(kpis: dict, rca: dict, cols: dict):
    """Public entry point. Returns a validated AI dict, or None (caller falls back to static).

    Cheap to call repeatedly within a Streamlit rerun — real network calls only
    happen once per distinct (tier, causes, KPI snapshot) signature.
    """
    if not rca.get("top_cause") or (rca.get("tier") or 0) == 0:
        _LAST_STATUS.update(used_ai=False, model=None, reason="no delay/cause data to analyze")
        return None

    signature = build_signature(kpis, rca, cols)
    signature_json = _signature_key(signature)
    try:
        return _cached_call(signature_json)
    except Exception:
        # Cache machinery itself failing (e.g. odd Streamlit state) shouldn't
        # take down the page — fall through to an uncached direct call.
        return _call_groq(signature)