# Surface Explain Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI explain button to the Surfaces tab that silently computes vol-smile, spike, and price-divergence metrics in the frontend, then sends them to a new `/ai/explain_surfaces` backend endpoint for a Gemini-generated narrative.

**Architecture:** Metrics are computed in a Vue composable (`useSurfaceMetrics.js`) the moment both surface components finish loading, using the raw data they already hold in memory. The composable exposes `{ metrics, ready }` reactively; `SurfaceExplainPanel.vue` consumes these and posts to the new endpoint on button click. The backend serialises the pre-computed metrics into a structured prompt and calls Gemini — no raw grid data crosses the wire.

**Tech Stack:** Python/FastAPI (backend), Pydantic v2, Gemini via existing `src/ai/client.py`, Vue 3 Composition API, Plotly (already in use), no new npm packages.

**Spec:** `docs/superpowers/specs/2026-05-28-surface-explain-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/api/schemas.py` | Modify | Add `volume`/`oi` to `MarketPricePoint`; add `BucketMetrics`, `SurfaceExplainRequest`, `SurfaceExplainResponse` |
| `src/api/routes/surface.py` | Modify | Populate `volume`/`oi` in `market_points` list |
| `src/ai/explain_surfaces.py` | Create | `build_surface_explain_message()` + `call_explain_surfaces()` |
| `src/ai/prompts/explain_surfaces_system.txt` | Create | Gemini system prompt for surface analysis |
| `src/ai/prompts.py` | Modify | Load `EXPLAIN_SURFACES_SYSTEM_PROMPT` |
| `src/api/routes/ai.py` | Modify | Add `POST /ai/explain_surfaces` endpoint |
| `tests/test_explain_surfaces.py` | Create | Unit tests for `build_surface_explain_message` + `call_explain_surfaces` |
| `tests/test_ai_routes.py` | Modify | Add route tests for `/ai/explain_surfaces` |
| `frontend/src/lib/api.js` | Modify | Add `explainSurfaces(payload)` |
| `frontend/src/lib/useSurfaceMetrics.js` | Create | Bucket grid + vol metrics + price metrics composable |
| `frontend/src/components/VolSurface.vue` | Modify | Emit `surfaceLoaded` after load |
| `frontend/src/components/PriceSurface.vue` | Modify | Emit `surfaceLoaded` after load |
| `frontend/src/App.vue` | Modify | Collect emits, instantiate composable, wire `SurfaceExplainPanel` |
| `frontend/src/components/SurfaceExplainPanel.vue` | Create | Level selector, explain button, markdown output |

---

## Task 1: Extend schemas

**Files:**
- Modify: `src/api/schemas.py`

- [ ] **Step 1: Extend `MarketPricePoint` and add three new schemas**

In `src/api/schemas.py`, replace the existing `MarketPricePoint` and add new classes after `PriceSurfaceResponse`:

```python
class MarketPricePoint(BaseModel):
    K: float
    T: float
    mid_price: float
    volume: int = 0
    open_interest: int = 0


class BucketMetrics(BaseModel):
    t_label: str
    m_label: str
    # vol surface
    spike_count: int
    # price surface
    mean_signed_div: float | None
    mean_abs_div: float | None
    pct_large_div: float | None
    count_large_div: int
    # liquidity
    volume: int
    open_interest: int


class SurfaceExplainRequest(BaseModel):
    user_level: UserLevel
    ticker: str
    option_type: OptionType
    smile_intensity: float
    put_skew: float
    deep_itm_bias: float | None
    divergence_threshold: float
    buckets: list[BucketMetrics]


class SurfaceExplainResponse(BaseModel):
    explanation: str
```

- [ ] **Step 2: Verify existing tests still pass (schema change is backwards-compatible)**

```
python -m pytest tests/ -v -x -q 2>&1 | tail -20
```

Expected: all existing tests pass (new fields have defaults so nothing breaks).

---

## Task 2: Add volume/OI to price surface route

**Files:**
- Modify: `src/api/routes/surface.py`

- [ ] **Step 1: Update `market_points` construction in `price_surface`**

In `src/api/routes/surface.py`, find the block that builds `market_points` (around line 257) and replace it:

```python
market_points = [
    MarketPricePoint(
        K=float(cr.strike),
        T=float(cr.T),
        mid_price=float(cr.mid_price),
        volume=int(cr.volume or 0),
        open_interest=int(cr.open_interest or 0),
    )
    for cr in chain_rows
    if float(cr.mid_price) > 0
]
```

- [ ] **Step 2: Run tests**

```
python -m pytest tests/ -v -x -q 2>&1 | tail -10
```

Expected: all pass.

---

## Task 3: System prompt

**Files:**
- Create: `src/ai/prompts/explain_surfaces_system.txt`
- Modify: `src/ai/prompts.py`

- [ ] **Step 1: Write the system prompt**

Create `src/ai/prompts/explain_surfaces_system.txt`:

```
You are an educational options market analyst. You will receive pre-computed metrics summarising the implied-volatility surface and the model-vs-market price surface for a single ticker and option type.

Adapt depth and language to the user level:
- Beginner: plain language, no formulas, focus on intuition and real-world meaning.
- Finance Student: standard financial terminology, key formulas where helpful, explain model assumptions.
- Professional: concise, assume deep domain knowledge, focus on nuance and structural interpretation.

Use plain text for all formulas (e.g. C = S*N(d1) - K*e^(-rT)*N(d2)), not LaTeX.
Do not make buy or sell recommendations of any kind.

The metrics you receive are:

VOL SURFACE SCALARS
- smile_intensity: (mean OTM IV / ATM IV) - 1. Positive = OTM options are priced at higher IV than ATM, indicating a volatility smile.
- put_skew: (mean put-side OTM IV / ATM IV) - 1, for moneyness 0.80–0.95. Positive = downside protection is expensive, reflecting market fear of drops.

PER-BUCKET TABLE (shared T × moneyness grid)
Each row covers one (maturity band, moneyness band) cell. Fields:
- spike_count: number of IV data points in this cell whose IV deviates more than 2 standard deviations from the cell mean. These are local outliers — not simply the smile — because z-scores are computed within each cell. Spikes often signal low-liquidity contracts or data noise.
- mean_signed_div: average (market_price - model_price) / model_price in this cell. Positive = market prices higher than the model; negative = model overprices.
- mean_abs_div: average absolute divergence — this is the primary measure of how well the model fits in this cell.
- pct_large_div / count_large_div: fraction and count of contracts whose absolute divergence exceeds the ticker-specific threshold (divergence_threshold). IMPORTANT: this threshold equals mean(|div|) + 2*std(|div|) across all contracts, so by construction only ~2–5% of points exceed it. Do NOT interpret near-zero pct_large_div as "the model fits well" — a cell with pct_large_div=0 but mean_abs_div=0.35 still shows substantial systematic mispricing. Use mean_abs_div as the primary fit signal; pct_large_div shows whether there are concentrated outlier clusters on top of the typical divergence.
- volume / open_interest: total contracts in this cell. Low values indicate illiquid strikes where divergences and spikes are less reliable.

PRICE SURFACE SCALAR
- deep_itm_bias: mean signed divergence for contracts with moneyness < 0.80 (deep ITM puts / deep OTM calls). A negative value means the model underprices these contracts. BSM systematically underprices deep-ITM options because it cannot account for early-exercise premium (American options) or the steep left tail priced into the market.
- divergence_threshold: the adaptive 2-sigma cutoff used for pct_large_div / count_large_div. Include this value in your narrative so the reader understands the scale of "large" divergence for this ticker.

STRUCTURE YOUR RESPONSE as:
1. Vol surface shape (smile, skew, what it implies)
2. IV spikes (which buckets, likely causes)
3. Model vs market (where the model fits and where it diverges most, referencing mean_abs_div and mean_signed_div)
4. Deep ITM bias if present
5. Liquidity observations (link low-volume buckets to less reliable metrics)
6. Cross-surface observations (e.g. a bucket with both high spike_count and high mean_abs_div suggests data noise is inflating apparent divergence)

Keep the response focused and concrete — reference specific bucket labels and numeric values where they add insight.
```

- [ ] **Step 2: Register the prompt in `src/ai/prompts.py`**

```python
"""Loads system prompt text files into module-level constants."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent / "prompts"

EXPLAIN_SYSTEM_PROMPT = (_DIR / "explain_system.txt").read_text(encoding="utf-8")
CHAT_SYSTEM_PROMPT = (_DIR / "chat_system.txt").read_text(encoding="utf-8")
EXPLAIN_SURFACES_SYSTEM_PROMPT = (_DIR / "explain_surfaces_system.txt").read_text(encoding="utf-8")
```

---

## Task 4: `src/ai/explain_surfaces.py`

**Files:**
- Create: `src/ai/explain_surfaces.py`

- [ ] **Step 1: Write the module**

```python
"""Builds the explain-surfaces prompt and calls Gemini."""
from __future__ import annotations

from src.ai.client import generate
from src.ai.prompts import EXPLAIN_SURFACES_SYSTEM_PROMPT

_LEVEL_LABELS = {
    "beginner": "Beginner",
    "finance_student": "Finance Student",
    "professional": "Professional",
}


def build_surface_explain_message(data: dict) -> str:
    level = _LEVEL_LABELS.get(data["user_level"], data["user_level"])
    ticker = data["ticker"]
    option_type = data["option_type"]

    lines = [
        f"User level: {level}",
        f"Ticker: {ticker}  |  Option type: {option_type}",
        "",
        "VOL SURFACE SCALARS",
        f"  smile_intensity : {data['smile_intensity']:.4f}",
        f"  put_skew        : {data['put_skew']:.4f}",
        "",
        "PRICE SURFACE SCALARS",
        f"  deep_itm_bias        : {data['deep_itm_bias']:.4f}" if data["deep_itm_bias"] is not None else "  deep_itm_bias        : n/a (no contracts with moneyness < 0.80)",
        f"  divergence_threshold : {data['divergence_threshold']:.4f}  (mean|div| + 2*std across all contracts)",
        "",
        "PER-BUCKET METRICS  (T × moneyness grid)",
        f"{'T':12s}  {'Moneyness':12s}  {'spikes':>6}  {'mean_sdiv':>10}  {'mean_adiv':>10}  {'pct_ldiv':>9}  {'n_ldiv':>6}  {'volume':>8}  {'OI':>8}",
        "-" * 110,
    ]

    for b in data["buckets"]:
        def fmt(v, fmt_str):
            return format(v, fmt_str) if v is not None else "    n/a"

        lines.append(
            f"{b['t_label']:12s}  {b['m_label']:12s}  "
            f"{b['spike_count']:>6d}  "
            f"{fmt(b['mean_signed_div'], '>+10.4f')}  "
            f"{fmt(b['mean_abs_div'],    '>10.4f')}  "
            f"{fmt(b['pct_large_div'],   '>9.1%')}  "
            f"{b['count_large_div']:>6d}  "
            f"{b['volume']:>8d}  "
            f"{b['open_interest']:>8d}"
        )

    lines.append("")
    lines.append("Please analyse these surfaces.")
    return "\n".join(lines)


def call_explain_surfaces(data: dict) -> str:
    message = build_surface_explain_message(data)
    return generate(
        EXPLAIN_SURFACES_SYSTEM_PROMPT,
        [{"role": "user", "parts": [{"text": message}]}],
    )
```

---

## Task 5: Tests for `explain_surfaces.py`

**Files:**
- Create: `tests/test_explain_surfaces.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for src/ai/explain_surfaces.py."""
from __future__ import annotations

from unittest.mock import patch


SAMPLE_BUCKET = {
    "t_label": "0.25–0.50",
    "m_label": "0.90–1.00",
    "spike_count": 2,
    "mean_signed_div": 0.05,
    "mean_abs_div": 0.08,
    "pct_large_div": 0.03,
    "count_large_div": 1,
    "volume": 1200,
    "open_interest": 5000,
}

SAMPLE_DATA = {
    "user_level": "finance_student",
    "ticker": "AAPL",
    "option_type": "call",
    "smile_intensity": 0.12,
    "put_skew": 0.08,
    "deep_itm_bias": -0.15,
    "divergence_threshold": 0.25,
    "buckets": [SAMPLE_BUCKET],
}


def test_message_contains_ticker_and_level():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "AAPL" in msg
    assert "Finance Student" in msg
    assert "call" in msg


def test_message_contains_vol_scalars():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "0.1200" in msg   # smile_intensity
    assert "0.0800" in msg   # put_skew


def test_message_contains_price_scalars():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "-0.1500" in msg  # deep_itm_bias
    assert "0.2500" in msg   # divergence_threshold


def test_message_contains_bucket_row():
    from src.ai.explain_surfaces import build_surface_explain_message
    msg = build_surface_explain_message(SAMPLE_DATA)
    assert "0.25–0.50" in msg
    assert "0.90–1.00" in msg
    assert "1200" in msg     # volume


def test_message_null_deep_itm_bias():
    from src.ai.explain_surfaces import build_surface_explain_message
    data = {**SAMPLE_DATA, "deep_itm_bias": None}
    msg = build_surface_explain_message(data)
    assert "n/a" in msg


def test_call_explain_surfaces_calls_generate():
    from src.ai.explain_surfaces import call_explain_surfaces
    from src.ai.prompts import EXPLAIN_SURFACES_SYSTEM_PROMPT

    with patch("src.ai.explain_surfaces.generate", return_value="Surface looks fine.") as mock_gen:
        result = call_explain_surfaces(SAMPLE_DATA)

    mock_gen.assert_called_once()
    args = mock_gen.call_args[0]
    assert args[0] == EXPLAIN_SURFACES_SYSTEM_PROMPT
    assert args[1][0]["role"] == "user"
    assert result == "Surface looks fine."
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_explain_surfaces.py -v 2>&1 | tail -20
```

Expected: ImportError or similar — `src/ai/explain_surfaces.py` does not exist yet (if running before Task 4) or all pass (if running after).

- [ ] **Step 3: Run after Task 4 implementation**

```
python -m pytest tests/test_explain_surfaces.py -v
```

Expected: 6 tests pass.

---

## Task 6: Route endpoint

**Files:**
- Modify: `src/api/routes/ai.py`
- Modify: `tests/test_ai_routes.py`

- [ ] **Step 1: Add import and endpoint to `src/api/routes/ai.py`**

Add to imports:
```python
from src.ai.explain_surfaces import call_explain_surfaces
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    ExplainRequest,
    ExplainResponse,
    SurfaceExplainRequest,
    SurfaceExplainResponse,
)
```

Add endpoint after the existing `/ai/explain` handler:
```python
@router.post("/ai/explain_surfaces", response_model=SurfaceExplainResponse)
def explain_surfaces(payload: SurfaceExplainRequest) -> SurfaceExplainResponse:
    try:
        explanation = call_explain_surfaces(payload.model_dump())
        return SurfaceExplainResponse(explanation=explanation)
    except GeminiError as exc:
        _raise_gemini_error(exc)
```

- [ ] **Step 2: Add route tests to `tests/test_ai_routes.py`**

Append to the file:
```python
SURFACE_EXPLAIN_PAYLOAD = {
    "user_level": "finance_student",
    "ticker": "AAPL",
    "option_type": "call",
    "smile_intensity": 0.12,
    "put_skew": 0.08,
    "deep_itm_bias": -0.15,
    "divergence_threshold": 0.25,
    "buckets": [
        {
            "t_label": "0.25–0.50",
            "m_label": "0.90–1.00",
            "spike_count": 2,
            "mean_signed_div": 0.05,
            "mean_abs_div": 0.08,
            "pct_large_div": 0.03,
            "count_large_div": 1,
            "volume": 1200,
            "open_interest": 5000,
        }
    ],
}


def test_explain_surfaces_returns_explanation():
    with patch("src.api.routes.ai.call_explain_surfaces", return_value="Surface looks healthy."):
        response = client.post("/api/v1/ai/explain_surfaces", json=SURFACE_EXPLAIN_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["explanation"] == "Surface looks healthy."


def test_explain_surfaces_returns_502_on_gemini_error():
    with patch("src.api.routes.ai.call_explain_surfaces", side_effect=GeminiError("quota")):
        response = client.post("/api/v1/ai/explain_surfaces", json=SURFACE_EXPLAIN_PAYLOAD)
    assert response.status_code == 502


def test_explain_surfaces_returns_422_on_missing_field():
    payload = {**SURFACE_EXPLAIN_PAYLOAD}
    del payload["smile_intensity"]
    response = client.post("/api/v1/ai/explain_surfaces", json=payload)
    assert response.status_code == 422
```

- [ ] **Step 3: Run all backend tests**

```
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: all pass.

---

## Task 7: Frontend — `api.js`

**Files:**
- Modify: `frontend/src/lib/api.js`

- [ ] **Step 1: Append `explainSurfaces` function**

At the end of `frontend/src/lib/api.js`:
```js
export async function explainSurfaces(payload) {
  const res = await fetch(`${BASE}/ai/explain_surfaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.error || `Surface explain failed: ${res.status}`)
  }
  return res.json()
}
```

---

## Task 8: Frontend — `useSurfaceMetrics.js`

**Files:**
- Create: `frontend/src/lib/useSurfaceMetrics.js`

- [ ] **Step 1: Write the composable**

```js
import { ref, watch, computed } from 'vue'

const T_BUCKETS = [
  { label: '0.05–0.25', min: 0.05, max: 0.25 },
  { label: '0.25–0.50', min: 0.25, max: 0.50 },
  { label: '0.50–0.75', min: 0.50, max: 0.75 },
  { label: '0.75–1.00', min: 0.75, max: 1.00 },
  { label: '1.00–1.50', min: 1.00, max: 1.50 },
]

function computeMBuckets(volPoints, spot) {
  const sorted = volPoints
    .map(p => p.strike / spot)
    .filter(m => isFinite(m) && m > 0)
    .sort((a, b) => a - b)

  const N = sorted.length
  if (N === 0) return []

  const targetDensity = N / Math.ceil(Math.sqrt(N))
  const MAX_WIDTH = 0.15
  const MIN_WIDTH = 0.03

  const buckets = []
  let binStart = sorted[0]
  let accumulated = 0

  for (let i = 0; i < N; i++) {
    accumulated++
    const width = sorted[i] - binStart
    const isLast = i === N - 1
    const shouldClose = (accumulated >= targetDensity || width >= MAX_WIDTH) && width >= MIN_WIDTH

    if (shouldClose || isLast) {
      if (shouldClose) {
        buckets.push({ label: `${binStart.toFixed(2)}–${sorted[i].toFixed(2)}`, min: binStart, max: sorted[i] })
        binStart = i + 1 < N ? sorted[i + 1] : sorted[i]
        accumulated = 0
      } else {
        // isLast: merge remaining into last bucket or open a new one
        if (buckets.length > 0) {
          buckets[buckets.length - 1].max = sorted[i]
          buckets[buckets.length - 1].label =
            `${buckets[buckets.length - 1].min.toFixed(2)}–${sorted[i].toFixed(2)}`
        } else {
          buckets.push({ label: `${binStart.toFixed(2)}–${sorted[i].toFixed(2)}`, min: binStart, max: sorted[i] })
        }
      }
    }
  }

  return buckets
}

function assignTBucket(T) {
  return T_BUCKETS.find(b => T >= b.min && T < b.max) ??
    (T >= 1.00 ? T_BUCKETS[4] : null)
}

function assignMBucket(m, mBuckets) {
  return mBuckets.find(b => m >= b.min && m <= b.max) ?? null
}

function computeVolMetrics(volPoints, spot, mBuckets) {
  const atm = volPoints.filter(p => { const m = p.strike / spot; return m >= 0.97 && m <= 1.03 })
  const atm_iv = atm.length > 0 ? atm.reduce((s, p) => s + p.implied_vol, 0) / atm.length : null

  const otm = volPoints.filter(p => { const m = p.strike / spot; return m < 0.95 || m > 1.05 })
  const smile_intensity = atm_iv && otm.length > 0
    ? otm.reduce((s, p) => s + p.implied_vol, 0) / otm.length / atm_iv - 1 : 0

  const putOtm = volPoints.filter(p => { const m = p.strike / spot; return m >= 0.80 && m < 0.95 })
  const put_skew = atm_iv && putOtm.length > 0
    ? putOtm.reduce((s, p) => s + p.implied_vol, 0) / putOtm.length / atm_iv - 1 : 0

  // spike_count per (T, m) bucket
  const spikeMap = {}
  for (const tb of T_BUCKETS) {
    for (const mb of mBuckets) {
      const key = `${tb.label}|${mb.label}`
      const pts = volPoints.filter(p => {
        const m = p.strike / spot
        return p.T >= tb.min && p.T < tb.max && m >= mb.min && m <= mb.max
      })
      if (pts.length < 2) { spikeMap[key] = 0; continue }
      const ivs = pts.map(p => p.implied_vol)
      const mean = ivs.reduce((s, v) => s + v, 0) / ivs.length
      const std = Math.sqrt(ivs.reduce((s, v) => s + (v - mean) ** 2, 0) / ivs.length)
      spikeMap[key] = std > 0 ? ivs.filter(v => Math.abs(v - mean) / std > 2.0).length : 0
    }
  }

  return { smile_intensity, put_skew, spikeMap }
}

function interpolateModelPrice(K, T, K_values, T_values, z) {
  const nK = K_values.length
  const nT = T_values.length

  let ki = K_values.findIndex(k => k >= K)
  let ti = T_values.findIndex(t => t >= T)

  ki = ki <= 0 ? 1 : ki >= nK ? nK - 1 : ki
  ti = ti <= 0 ? 1 : ti >= nT ? nT - 1 : ti

  const k0 = ki - 1, k1 = ki, t0 = ti - 1, t1 = ti
  const wK = (K - K_values[k0]) / (K_values[k1] - K_values[k0])
  const wT = (T - T_values[t0]) / (T_values[t1] - T_values[t0])

  return (1 - wT) * ((1 - wK) * z[t0][k0] + wK * z[t0][k1]) +
         wT     * ((1 - wK) * z[t1][k0] + wK * z[t1][k1])
}

function computePriceMetrics(marketPoints, K_values, T_values, z, S_ref, mBuckets) {
  const MODEL_FLOOR = 0.10

  const enriched = marketPoints.map(pt => {
    const moneyness = pt.K / S_ref
    const modelPrice = interpolateModelPrice(pt.K, pt.T, K_values, T_values, z)
    if (modelPrice < MODEL_FLOOR) return { ...pt, moneyness, eligible: false, div: null }
    return { ...pt, moneyness, eligible: true, div: (pt.mid_price - modelPrice) / modelPrice }
  })

  const eligible = enriched.filter(p => p.eligible)
  const absDivs = eligible.map(p => Math.abs(p.div))
  const meanAbs = absDivs.length > 0 ? absDivs.reduce((s, v) => s + v, 0) / absDivs.length : 0
  const stdAbs = absDivs.length > 0
    ? Math.sqrt(absDivs.reduce((s, v) => s + (v - meanAbs) ** 2, 0) / absDivs.length) : 0
  const divergence_threshold = meanAbs + 2 * stdAbs

  const deepItm = eligible.filter(p => p.moneyness < 0.80)
  const deep_itm_bias = deepItm.length > 0
    ? deepItm.reduce((s, p) => s + p.div, 0) / deepItm.length : null

  // per-bucket stats
  const divMap = {}, volMap = {}
  for (const tb of T_BUCKETS) {
    for (const mb of mBuckets) {
      const key = `${tb.label}|${mb.label}`
      const pts = enriched.filter(p =>
        p.T >= tb.min && p.T < tb.max && p.moneyness >= mb.min && p.moneyness <= mb.max
      )
      const divs = pts.filter(p => p.eligible).map(p => p.div)
      const large = divs.filter(d => Math.abs(d) > divergence_threshold)

      divMap[key] = {
        mean_signed_div: divs.length > 0 ? divs.reduce((s, v) => s + v, 0) / divs.length : null,
        mean_abs_div:    divs.length > 0 ? divs.reduce((s, v) => s + Math.abs(v), 0) / divs.length : null,
        pct_large_div:   divs.length > 0 ? large.length / divs.length : null,
        count_large_div: large.length,
      }
      volMap[key] = {
        volume:          pts.reduce((s, p) => s + (p.volume || 0), 0),
        open_interest:   pts.reduce((s, p) => s + (p.open_interest || 0), 0),
      }
    }
  }

  return { deep_itm_bias, divergence_threshold, divMap, volMap }
}

export function useSurfaceMetrics(volData, priceData) {
  const metrics = ref(null)
  const ready   = ref(false)

  watch([volData, priceData], ([vd, pd]) => {
    if (!vd || !pd) { metrics.value = null; ready.value = false; return }

    const { points, spot } = vd
    const { market_points, K_values, T_values, z, S_ref } = pd

    if (!points?.length || !market_points || !K_values || !T_values || !z) return

    const mBuckets = computeMBuckets(points, spot)
    if (mBuckets.length === 0) return

    const { smile_intensity, put_skew, spikeMap } = computeVolMetrics(points, spot, mBuckets)
    const { deep_itm_bias, divergence_threshold, divMap, volMap } =
      computePriceMetrics(market_points, K_values, T_values, z, S_ref, mBuckets)

    const buckets = []
    for (const tb of T_BUCKETS) {
      for (const mb of mBuckets) {
        const key = `${tb.label}|${mb.label}`
        buckets.push({
          t_label: tb.label,
          m_label: mb.label,
          spike_count: spikeMap[key] ?? 0,
          ...divMap[key],
          ...volMap[key],
        })
      }
    }

    metrics.value = { smile_intensity, put_skew, deep_itm_bias, divergence_threshold, buckets }
    ready.value = true
  }, { deep: true })

  return { metrics, ready }
}
```

---

## Task 9: Emit from `VolSurface.vue`

**Files:**
- Modify: `frontend/src/components/VolSurface.vue`

- [ ] **Step 1: Add emit declaration and fire after successful load**

Add `defineEmits` after `defineProps`:
```js
const emit = defineEmits(['surfaceLoaded'])
```

At the end of the `try` block in `loadAndPlot`, after `plotted = true`, add:
```js
emit('surfaceLoaded', { points: data.points, spot: S })
```

The spot `S` is already computed at that point in the function as `const S = market?.spot_price ?? null`. Only emit when `S` is available (market data loaded):
```js
if (S !== null) emit('surfaceLoaded', { points: data.points, spot: S })
```

---

## Task 10: Emit from `PriceSurface.vue`

**Files:**
- Modify: `frontend/src/components/PriceSurface.vue`

- [ ] **Step 1: Add emit declaration and fire after successful load**

Add after `defineProps`:
```js
const emit = defineEmits(['surfaceLoaded'])
```

At the end of the `try` block in `loadAndPlot`, after `plotted = true`:
```js
emit('surfaceLoaded', {
  market_points: data.market_points,
  K_values: data.K_values,
  T_values: data.T_values,
  z: data.z,
  S_ref: data.S_ref,
})
```

---

## Task 11: Wire `App.vue`

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Import composable and new component**

Add to the imports at the top of `<script setup>`:
```js
import SurfaceExplainPanel from './components/SurfaceExplainPanel.vue'
import { useSurfaceMetrics } from './lib/useSurfaceMetrics.js'
```

- [ ] **Step 2: Add reactive refs and composable**

After the `const theme = ref('dark')` line:
```js
const volSurfaceData   = ref(null)
const priceSurfaceData = ref(null)
const { metrics: surfaceMetrics, ready: surfaceReady } = useSurfaceMetrics(volSurfaceData, priceSurfaceData)
```

- [ ] **Step 3: Reset on ticker change**

After the existing `watch([inputs, method, optionStyle], ...)` block:
```js
watch(ticker, () => {
  volSurfaceData.value   = null
  priceSurfaceData.value = null
})
```

- [ ] **Step 4: Update the surfaces template**

Replace:
```html
<div v-else class="flex flex-col gap-6">
  <VolSurface :ticker="ticker" :theme="theme" />
  <PriceSurface
    :ticker="ticker"
    :inputs="inputs"
    :option-style="optionStyle"
    :sigma-type="sigmaType"
    :theme="theme"
  />
</div>
```

With:
```html
<div v-else class="flex flex-col gap-6">
  <VolSurface
    :ticker="ticker"
    :theme="theme"
    @surface-loaded="volSurfaceData = $event"
  />
  <PriceSurface
    :ticker="ticker"
    :inputs="inputs"
    :option-style="optionStyle"
    :sigma-type="sigmaType"
    :theme="theme"
    @surface-loaded="priceSurfaceData = $event"
  />
  <SurfaceExplainPanel
    :metrics="surfaceMetrics"
    :ready="surfaceReady"
    :ticker="ticker"
  />
</div>
```

---

## Task 12: `SurfaceExplainPanel.vue`

**Files:**
- Create: `frontend/src/components/SurfaceExplainPanel.vue`

- [ ] **Step 1: Write the component**

```vue
<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { explainSurfaces } from '../lib/api.js'

const props = defineProps({
  metrics: { type: Object, default: null },
  ready:   { type: Boolean, default: false },
  ticker:  { type: String, default: null },
})

const LEVELS = [
  { key: 'beginner',        label: 'Beginner' },
  { key: 'finance_student', label: 'Student' },
  { key: 'professional',    label: 'Professional' },
]

const level       = ref('finance_student')
const explanation = ref(null)
const loading     = ref(false)
const error       = ref(null)

const explanationHtml = computed(() =>
  explanation.value ? marked.parse(explanation.value) : ''
)

async function runExplain() {
  if (!props.metrics || !props.ready) return
  loading.value     = true
  error.value       = null
  explanation.value = null
  try {
    const data = await explainSurfaces({
      ...props.metrics,
      user_level:  level.value,
      ticker:      props.ticker,
      option_type: 'call',
    })
    explanation.value = data.explanation
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="ticker" class="card">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">AI Surface Analysis</h2>
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] text-slate-500 uppercase tracking-widest font-semibold mr-1">Level:</span>
        <button
          v-for="lvl in LEVELS"
          :key="lvl.key"
          @click="level = lvl.key"
          :class="[
            'text-xs font-semibold rounded-full px-3 py-1 border transition-colors',
            level === lvl.key
              ? 'bg-violet-900/40 border-violet-600 text-violet-300'
              : 'border-slate-700 text-slate-500 hover:text-slate-300'
          ]"
        >{{ lvl.label }}</button>
      </div>
    </div>

    <!-- Computing hint -->
    <div v-if="!ready && !loading" class="text-[11px] text-slate-500 mb-3 flex items-center gap-1.5">
      <span class="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse"></span>
      Computing surface metrics…
    </div>

    <!-- Explain button -->
    <button
      @click="runExplain"
      :disabled="!ready || loading"
      class="w-full py-3 rounded-xl bg-violet-700 hover:bg-violet-600 active:bg-violet-800 text-white font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
    >
      <svg v-if="!loading" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ loading ? 'Analysing surfaces…' : 'Explain these surfaces' }}
    </button>

    <!-- Rendered markdown output -->
    <div
      v-if="explanationHtml"
      class="explain-prose mt-4 bg-slate-900/60 rounded-xl border border-slate-800 p-4"
      v-html="explanationHtml"
    />
    <div v-if="error" class="mt-3 text-sm text-rose-400">{{ error }}</div>

  </div>
</template>

<style scoped>
.explain-prose :deep(h1),
.explain-prose :deep(h2),
.explain-prose :deep(h3) {
  color: #c4b5fd;
  font-weight: 700;
  margin-top: 1rem;
  margin-bottom: 0.35rem;
}
.explain-prose :deep(h1) { font-size: 0.95rem; }
.explain-prose :deep(h2) { font-size: 0.875rem; }
.explain-prose :deep(h3) { font-size: 0.8rem; letter-spacing: 0.02em; }
.explain-prose :deep(p) {
  color: #cbd5e1;
  font-size: 0.8rem;
  line-height: 1.65;
  margin-bottom: 0.6rem;
}
.explain-prose :deep(ul),
.explain-prose :deep(ol) {
  color: #cbd5e1;
  font-size: 0.8rem;
  padding-left: 1.25rem;
  margin-bottom: 0.6rem;
  list-style: disc;
}
.explain-prose :deep(ol) { list-style: decimal; }
.explain-prose :deep(li) { margin-bottom: 0.2rem; line-height: 1.55; }
.explain-prose :deep(strong) { color: #e2e8f0; font-weight: 600; }
.explain-prose :deep(em) { color: #a5b4fc; font-style: italic; }
.explain-prose :deep(code) {
  background: #1e293b;
  color: #7dd3fc;
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}
.explain-prose :deep(hr) {
  border-color: #334155;
  margin: 0.75rem 0;
}
</style>
```

---

## Verification

- [ ] Run full backend test suite: `python -m pytest tests/ -v`
- [ ] Start dev server and open the Surfaces tab with a ticker loaded
- [ ] Confirm "Computing surface metrics…" hint appears briefly after charts load
- [ ] Confirm button becomes active after both charts finish loading
- [ ] Click "Explain these surfaces" — confirm Gemini response renders as markdown
- [ ] Change ticker — confirm button resets (ready goes false until both charts reload)
- [ ] Test with option_type = put (button should still work; metrics computed from call surface data, option_type passed to AI)
