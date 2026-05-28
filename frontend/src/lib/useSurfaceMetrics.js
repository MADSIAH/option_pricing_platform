import { ref, watch } from 'vue'

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

    if (shouldClose) {
      buckets.push({ label: `${binStart.toFixed(2)}–${sorted[i].toFixed(2)}`, min: binStart, max: sorted[i] })
      binStart = i + 1 < N ? sorted[i + 1] : sorted[i]
      accumulated = 0
    } else if (isLast) {
      if (buckets.length > 0) {
        buckets[buckets.length - 1].max = sorted[i]
        buckets[buckets.length - 1].label =
          `${buckets[buckets.length - 1].min.toFixed(2)}–${sorted[i].toFixed(2)}`
      } else {
        buckets.push({ label: `${binStart.toFixed(2)}–${sorted[i].toFixed(2)}`, min: binStart, max: sorted[i] })
      }
    }
  }

  return buckets
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

  return { smile_intensity, put_skew, atm_iv, spikeMap }
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
         wT       * ((1 - wK) * z[t1][k0] + wK * z[t1][k1])
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
        volume:        pts.reduce((s, p) => s + (p.volume || 0), 0),
        open_interest: pts.reduce((s, p) => s + (p.open_interest || 0), 0),
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

    const { smile_intensity, put_skew, atm_iv, spikeMap } = computeVolMetrics(points, spot, mBuckets)
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

    metrics.value = { smile_intensity, put_skew, atm_iv, deep_itm_bias, divergence_threshold, buckets }
    ready.value = true
  }, { deep: true })

  return { metrics, ready }
}
