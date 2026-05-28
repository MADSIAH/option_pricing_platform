<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { fetchVolSurface, fetchMarket } from '../lib/api.js'

const props = defineProps({
  ticker: { type: String, default: null },
  theme:  { type: String, default: 'dark' },
})

const emit = defineEmits(['surfaceLoaded'])

const plotEl    = ref(null)
const loading   = ref(false)
const error     = ref(null)
const updatedAt = ref(null)
const isStale   = ref(false)
let plotted     = false

function fmtUpdated(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false, timeZoneName: 'short' })
}

function colors(theme) {
  return theme === 'light'
    ? { paper: '#f8fafc', plot: '#f1f5f9', font: '#334155', grid: '#cbd5e1' }
    : { paper: '#0f172a', plot: '#1e293b', font: '#94a3b8', grid: '#334155' }
}

function buildLayout(theme, title, hasSpot) {
  const c = colors(theme)
  return {
    title: { text: title, font: { color: c.font, size: 13 }, x: 0.04 },
    paper_bgcolor: c.paper,
    plot_bgcolor:  c.plot,
    font: { color: c.font, size: 11 },
    margin: { l: 10, r: 10, t: 55, b: 10 },
    scene: {
      bgcolor: c.plot,
      aspectmode: 'cube',
      camera: { eye: { x: -0.8, y: 1.8, z: 0.8 } },
      xaxis: {
        title: { text: 'Time to Maturity (years)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
      yaxis: {
        title: { text: hasSpot ? 'Moneyness (K/S)' : 'Strike K ($)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        gridcolor: c.grid,
        zerolinecolor: c.grid,
        autorange: true,
      },
      zaxis: {
        title: { text: 'Implied Volatility (%)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        ticksuffix: '%',
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
    },
  }
}

async function loadAndPlot() {
  if (!props.ticker || !plotEl.value) return
  loading.value   = true
  error.value     = null
  updatedAt.value = null
  isStale.value   = false
  plotted         = false
  try {
    const [data, market] = await Promise.all([
      fetchVolSurface(props.ticker),
      fetchMarket(props.ticker).catch(() => null),
    ])
    updatedAt.value = data.updated_at ?? null
    isStale.value   = data.stale === true
    const title = `Implied Volatility Surface — ${props.ticker}`
    const c     = colors(props.theme)
    const S     = market?.spot_price ?? null

    const toMoneyness = K => S ? K / S : K

    let traces
    if (data.grid) {
      traces = [{
        type: 'surface',
        x: data.grid.T_values,
        y: data.grid.K_values.map(toMoneyness),
        z: data.grid.z,
        colorscale: 'Viridis',
        colorbar: {
          title: { text: 'IV (%)', font: { color: c.font, size: 11 } },
          tickfont: { color: c.font, size: 9 },
          ticksuffix: '%',
          thickness: 14, len: 0.65, x: 1.01,
        },
        contours: {
          x: { show: true, color: c.grid, width: 1, highlight: false },
          y: { show: true, color: c.grid, width: 1, highlight: false },
          z: { show: true, color: c.grid, width: 1, highlight: false },
        },
        hovertemplate: S
          ? 'T: %{x:.3f}y<br>Moneyness: %{y:.3f}<br>IV: %{z:.1f}%<extra></extra>'
          : 'T: %{x:.3f}y<br>K: $%{y:.1f}<br>IV: %{z:.1f}%<extra></extra>',
      }]
    } else {
      traces = [{
        type: 'scatter3d',
        mode: 'markers',
        x: data.points.map(p => p.T),
        y: data.points.map(p => toMoneyness(p.strike)),
        z: data.points.map(p => p.implied_vol * 100),
        marker: {
          size: 5,
          color: data.points.map(p => p.implied_vol * 100),
          colorscale: 'Viridis',
          showscale: true,
          colorbar: {
            title: { text: 'IV (%)', font: { color: c.font, size: 11 } },
            tickfont: { color: c.font, size: 9 },
            ticksuffix: '%',
            thickness: 14, len: 0.65, x: 1.01,
          },
        },
        hovertemplate: S
          ? 'T: %{x:.3f}y<br>Moneyness: %{y:.3f}<br>IV: %{z:.1f}%<extra></extra>'
          : 'T: %{x:.3f}y<br>K: $%{y:.1f}<br>IV: %{z:.1f}%<extra></extra>',
      }]
    }

    Plotly.newPlot(plotEl.value, traces, buildLayout(props.theme, title, S !== null), { responsive: true })
    plotted = true
    if (S !== null) emit('surfaceLoaded', { points: data.points, spot: S })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => loadAndPlot())
watch(() => [props.ticker, props.theme], () => loadAndPlot())
onUnmounted(() => { if (plotEl.value) Plotly.purge(plotEl.value) })
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="section-label">Implied Volatility Surface</h2>
        <span class="hint">Market-implied vol across strikes and maturities</span>
      </div>
      <div v-if="loading" class="flex items-center gap-1.5 text-[11px] text-slate-500">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        Loading…
      </div>
      <span v-else-if="updatedAt" :class="['text-[10px] font-mono', isStale ? 'text-amber-400' : 'text-emerald-500']">
        last updated: {{ fmtUpdated(updatedAt) }}
      </span>
    </div>

    <div v-if="!ticker" class="flex items-center justify-center h-64 text-slate-400 text-sm text-center px-6">
      Go to the <strong class="text-slate-300 mx-1">Pricing &amp; Greeks</strong> tab and select a ticker to visualize the surface.
    </div>
    <div v-else-if="error" class="flex items-center justify-center h-64 text-rose-400 text-sm">
      {{ error }}
    </div>
    <div v-else ref="plotEl" style="height: 520px;" class="w-full"></div>

    <!-- Vol smile + data quality note (shown only when surface is rendered) -->
    <div v-if="ticker && !loading && !error" class="mt-4 rounded-lg bg-slate-800/70 border border-slate-600/60 px-4 py-3 text-[13px] text-slate-200 leading-relaxed space-y-2">
      <p><span class="text-emerald-400 font-semibold">Volatility smile:</span> Implied vol is typically higher for deep ITM and OTM strikes than ATM — a pattern that models using a single volatility (like BSM) cannot capture by design.</p>
      <p><span class="text-amber-400 font-semibold">Data note:</span> Isolated spikes or irregular patches are real market artifacts — low-liquidity contracts, wide bid-ask spreads, or sparse option chains. These are not rendering bugs.</p>
    </div>
  </div>
</template>
