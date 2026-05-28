# Surface Explain Button — Design Spec

**Date:** 2026-05-28
**Branch:** `feature/ai-explain-chat`
**Status:** Approved, ready for implementation

---

## Goal

Add an AI explain button to the Surfaces tab that analyses both the implied-volatility surface and the price surface together. Metrics are computed silently in the frontend the moment surface data finishes loading. The button click sends a compact pre-computed metrics payload to a new backend endpoint, which builds a structured prompt and calls Gemini.

---

## Architecture

### Data flow

```
Tab switch → Surfaces view mounts
  VolSurface.vue loads → emits { points, spot } to App.vue
  PriceSurface.vue loads → emits { market_points, K_values, T_values, z, S_ref } to App.vue

App.vue passes both payloads to useSurfaceMetrics.js composable
  → computes shared bucket grid (boundaries from vol surface points)
  → computes vol surface metrics
  → computes price surface metrics
  → exposes { metrics, ready } reactively

SurfaceExplainPanel.vue
  → receives { metrics, ready } as props
  → button disabled until ready === true
  → on click: POST /ai/explain_surfaces with { metrics, user_level }
  → renders markdown response (same prose styles as ExplainPanel)
```

### Placement

```
Surfaces tab (App.vue):
  <VolSurface />
  <PriceSurface />
  <SurfaceExplainPanel />    ← new, below both cards
```

---

## Shared Bucket Grid

Buckets are defined once from vol surface points and reused identically on the price surface, so the LLM sees the same coordinate system for both surfaces. `data.points` (vol surface) and `market_points` (price surface) originate from the same OptionChain rows, so the bucket boundaries are equally representative of both.

### T buckets (fixed, 5 bins)

| Label | Range |
|-------|-------|
| `0.05–0.25` | [0.05, 0.25) |
| `0.25–0.50` | [0.25, 0.50) |
| `0.50–0.75` | [0.50, 0.75) |
| `0.75–1.00` | [0.75, 1.00) |
| `1.00–1.50` | [1.00, 1.50] |

### Moneyness buckets (adaptive)

```
m = K / S  for each vol surface point

1. target_n_bins = ceil(sqrt(N_points))
2. target_density = N_points / target_n_bins
3. Sort points by m ascending.
4. Scan: open a new bin when either:
     accumulated_count >= target_density
     OR current_bin_width >= 0.15
5. Minimum bin width: 0.03 (prevents single-point bins at extremes).
6. Resulting boundary list stored and reused for price surface market_points.
```

This gives fine-grained bins near ATM (where data is dense) and coarser bins in sparse OTM/ITM tails.

---

## Metrics Definition

### Vol surface (from `data.points` + spot `S`)

`atm_iv` is computed internally as the denominator for smile and skew; it is **not** included in the AI payload.

| Metric | Granularity | Formula |
|--------|-------------|---------|
| `smile_intensity` | scalar | `mean(OTM IV) / atm_iv − 1`; OTM = m outside [0.95, 1.05] |
| `put_skew` | scalar | `mean(IV for m ∈ [0.80, 0.95)) / atm_iv − 1` |
| `spike_count` | per (T, m)-bucket | Count of points with `|z| > 2.0`; z = `(IV − bin_mean) / bin_std` |

Z-scores are computed **within each (T, m)-bucket**, so the smile never registers as a spike — a high OTM IV is flagged only if it deviates from the local mean of that OTM bin.

### Price surface (from `market_points` + model grid `z`)

For each market point:
```
moneyness       = K / S_ref
model_price     = bilinear interpolation of z[T_idx][K_idx]

if model_price < 0.10: skip this point for divergence (still counted in volume/liquidity)
else: divergence = (mid_price − model_price) / model_price   [signed]
```

The `model_price < 0.10` floor prevents near-zero model prices on deep-OTM options from producing explosive percentage divergences (e.g. model=0.02, mid=0.05 → +150%) that would pollute both the 2-sigma threshold and the per-bucket means. Those points are still assigned to their bucket for volume/OI aggregation.

The grid is a regular linspace in both K and T, so bilinear interpolation reduces to direct index arithmetic (no external library needed).

**Adaptive divergence threshold:**
```
divergence_threshold = mean(|div|) + 2 × std(|div|)   across all eligible market_points
```
Adapts per ticker: tight for SPY (~10%), wider for TSLA (~40%). Passed as `divergence_threshold` in the payload so the LLM has the reference when interpreting `pct_large_divergence`.

| Metric | Granularity | Definition |
|--------|-------------|-----------|
| `mean_signed_divergence` | per (T, m)-bucket | Mean signed divergence |
| `mean_abs_divergence` | per (T, m)-bucket | Mean \|divergence\| |
| `pct_large_divergence` | per (T, m)-bucket | % of points with \|div\| > `divergence_threshold` |
| `count_large_divergence` | per (T, m)-bucket | Raw count with \|div\| > `divergence_threshold` |
| `deep_itm_bias` | scalar | Mean divergence for m < 0.80; null if no points there |
| `volume` | per (T, m)-bucket | Sum of `volume` |
| `open_interest` | per (T, m)-bucket | Sum of `open_interest` |

---

## Backend Changes

### 1. `src/api/schemas.py`

Extend `MarketPricePoint`:
```python
class MarketPricePoint(BaseModel):
    K: float
    T: float
    mid_price: float
    volume: int = 0
    open_interest: int = 0
```

Add new schemas:
```python
class BucketMetrics(BaseModel):
    t_label: str                     # e.g. "0.25–0.50"
    m_label: str                     # e.g. "0.90–1.00"
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
    # vol surface scalars
    smile_intensity: float
    put_skew: float
    # price surface scalars
    deep_itm_bias: float | None
    divergence_threshold: float      # adaptive 2-sigma threshold, for LLM context
    # shared bucket grid
    buckets: list[BucketMetrics]

class SurfaceExplainResponse(BaseModel):
    explanation: str
```

### 2. `src/api/routes/surface.py`

In the `price_surface` endpoint, populate `volume` and `open_interest` when building `market_points`:
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

### 3. `src/api/routes/ai.py`

```python
@router.post("/ai/explain_surfaces", response_model=SurfaceExplainResponse)
def explain_surfaces(payload: SurfaceExplainRequest) -> SurfaceExplainResponse:
    try:
        explanation = call_explain_surfaces(payload.model_dump())
        return SurfaceExplainResponse(explanation=explanation)
    except GeminiError as exc:
        _raise_gemini_error(exc)
```

### 4. `src/ai/explain_surfaces.py`

`build_surface_explain_message(data)` serialises the metrics dict into a structured user-turn message:
- Ticker, option type, user level
- Vol surface scalars: smile_intensity, put_skew
- Per-bucket table: t_label, m_label, spike_count, mean_signed_div, mean_abs_div, pct_large_div, count_large_div, volume, open_interest
- Price surface scalars: deep_itm_bias, divergence_threshold

`call_explain_surfaces(data)` calls `generate(EXPLAIN_SURFACES_SYSTEM_PROMPT, [...])`.

### 5. `src/ai/prompts/explain_surfaces_system.txt`

System prompt instructing Gemini to:
- Describe the shape of the vol smile and how pronounced it is
- Comment on put-side skew and what it implies about market sentiment
- Flag spike buckets and their likely causes (liquidity, data quality)
- Describe where the model diverges most from market prices, and why BSM/BAW would under/overprice there
- Comment on deep-ITM put bias (m < 0.80) if present
- Relate liquidity (volume/OI) to regions of high divergence or spike activity
- Draw cross-surface observations (e.g. high IV spike + high divergence in same bucket)
- Adapt depth and terminology to user level

**Critical framing instruction for divergence metrics (must be in system prompt):**
- `mean_abs_div` per bucket is the typical magnitude of model-vs-market divergence for that region — this is the primary signal for how well the model fits.
- `pct_large_div` and `count_large_div` identify local outliers within the ticker's own distribution (threshold = mean + 2σ of all divergences). By construction ~2–5% of points exceed this. Do not interpret near-zero counts as "the model fits well" — a bucket where `pct_large_div = 0` but `mean_abs_div = 0.35` still shows substantial systematic mispricing. Conversely, do not alarm if a few buckets have `pct_large_div > 0` — these are the locally unusual contracts, not catastrophic failures.
- Always anchor the narrative on `mean_abs_div` and `mean_signed_div` first; treat `pct_large_div` as a secondary signal for spotting concentrated outlier clusters.

---

## Frontend Changes

### 1. `frontend/src/lib/api.js`

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

### 2. `frontend/src/lib/useSurfaceMetrics.js`

Composable accepting `volData` (ref) and `priceData` (ref), returning `{ metrics, ready }`.

Internal functions:
```
computeBucketGrid(volPoints, spot)
  → { tBuckets, mBuckets }           (shared boundary lists)

computeVolMetrics(volPoints, spot, tBuckets, mBuckets)
  → { smile_intensity, put_skew, bucketSpikeStats }

computePriceMetrics(marketPoints, K_values, T_values, z, S_ref, tBuckets, mBuckets)
  → { deep_itm_bias, divergence_threshold, bucketDivStats, bucketVolumeStats }

mergeBuckets(bucketSpikeStats, bucketDivStats, bucketVolumeStats)
  → list[BucketMetrics]
```

Watching `volData` and `priceData`: when both are non-null, runs computation and sets `ready = true`. Both refs reset to `null` when ticker changes to force recomputation.

Bilinear interpolation helper (inline, ~10 lines):
```js
function interpolateModelPrice(K, T, K_values, T_values, z) {
  // K_values and T_values are linspace → direct index arithmetic
  // bilinear blend of z[t0][k0], z[t0][k1], z[t1][k0], z[t1][k1]
}
```

### 3. `frontend/src/components/VolSurface.vue`

After successful load, emit:
```js
emit('surfaceLoaded', { points: data.points, spot: S })
```

### 4. `frontend/src/components/PriceSurface.vue`

After successful load, emit:
```js
emit('surfaceLoaded', {
  market_points: data.market_points,
  K_values: data.K_values,
  T_values: data.T_values,
  z: data.z,
  S_ref: data.S_ref,
})
```

### 5. `frontend/src/App.vue`

```js
const volSurfaceData   = ref(null)
const priceSurfaceData = ref(null)
const { metrics, ready } = useSurfaceMetrics(volSurfaceData, priceSurfaceData)

watch(ticker, () => { volSurfaceData.value = null; priceSurfaceData.value = null })
```

```html
<VolSurface   :ticker="ticker" :theme="theme" @surface-loaded="volSurfaceData = $event" />
<PriceSurface :ticker="ticker" ... :theme="theme" @surface-loaded="priceSurfaceData = $event" />
<SurfaceExplainPanel :metrics="metrics" :ready="ready" :ticker="ticker" />
```

### 6. `frontend/src/components/SurfaceExplainPanel.vue`

Mirrors `ExplainPanel.vue` in structure:
- Level selector (Beginner / Student / Professional)
- Button: "Explain these surfaces" — disabled while `!ready || loading`
- Subtle hint while `!ready && ticker`: "Computing metrics…"
- On click: calls `explainSurfaces({ ...metrics, user_level: level })`
- Renders markdown response with same `.explain-prose` styles

---

## Out of Scope

- Server-side metric computation (all math stays in the frontend composable)
- Smoothing or arbitrage-free post-processing of the vol surface before metric computation
- Per-T-bucket breakdown of smile/skew scalars (kept as overall scalars to avoid overwhelming the LLM)
- Global `total_spike_count` scalar (spike information lives per-bucket only; the LLM reads the bucket grid)
- `atm_iv` in the AI payload (internal denominator only, not sent to the LLM)
