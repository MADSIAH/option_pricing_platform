<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { fetchPriceSurface } from '../lib/api.js'

const props = defineProps({
  ticker:      { type: String, default: null },
  inputs:      { type: Object, required: true },
  optionStyle: { type: String, default: 'european' },
  sigmaType:   { type: String, default: 'implied' },
  theme:       { type: String, default: 'dark' },
})

const emit = defineEmits(['surfaceLoaded'])

const optionType = ref('call')
const loading    = ref(false)
const error      = ref(null)
const plotEl     = ref(null)
let plotted      = false

function colors(theme) {
  return theme === 'light'
    ? { paper: '#f8fafc', plot: '#f1f5f9', font: '#334155', grid: '#cbd5e1' }
    : { paper: '#0f172a', plot: '#1e293b', font: '#94a3b8', grid: '#334155' }
}

function buildLayout(theme, title) {
  const c = colors(theme)
  return {
    title: { text: title, font: { color: c.font, size: 13 }, x: 0.04 },
    paper_bgcolor: c.paper,
    plot_bgcolor:  c.plot,
    font: { color: c.font, size: 11 },
    margin: { l: 10, r: 10, t: 55, b: 10 },
    legend: { x: 0.01, y: 0.97, bgcolor: 'rgba(255,255,255,0.07)', font: { color: c.font, size: 10 } },
    scene: {
      bgcolor: c.plot,
      aspectmode: 'cube',
      camera: { eye: { x: 1.6, y: -1.9, z: 0.75 } },
      xaxis: {
        title: { text: 'Spot S ($)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        tickprefix: '$',
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
      yaxis: {
        title: { text: 'Time to Maturity (years)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
      zaxis: {
        title: { text: 'Option Price ($)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        tickprefix: '$',
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
    },
  }
}

async function loadAndPlot() {
  if (!props.ticker || !plotEl.value) return
  loading.value = true
  error.value   = null
  try {
    const payload = {
      ticker:     props.ticker,
      option_type: optionType.value,
      style:      props.optionStyle,
      sigma_type: props.sigmaType,
      r: props.inputs.r / 100,
      q: props.inputs.q / 100,
    }
    if (props.inputs.sigma > 0) payload.sigma = props.inputs.sigma / 100
    if (props.inputs.S > 0)     payload.S     = props.inputs.S

    const data   = await fetchPriceSurface(payload)
    const c      = colors(props.theme)
    const label  = `${optionType.value.charAt(0).toUpperCase() + optionType.value.slice(1)}`
    const title  = `${data.style === 'european' ? 'BS' : 'BAW'} Price Surface — ${props.ticker} ${label}s  (σ = ${(data.sigma * 100).toFixed(1)}%,  S₀ = ${data.S_ref.toFixed(2)})`

    // Mirror K → equivalent spot: x = 2*S_ref - K (notebook convention)
    // Low K (ITM call) → high x; high K (OTM call) → low x
    // Makes call prices rise as x increases, hockey stick blade on the right
    const xVals = data.K_values.map(k => 2 * data.S_ref - k)

    const surfaceTrace = {
      type: 'surface',
      name: `${data.style === 'european' ? 'BS' : 'BAW'} model`,
      x: xVals,
      y: data.T_values,
      z: data.z,
      colorscale: 'Viridis',
      opacity: 0.82,
      colorbar: {
        title: { text: 'Price ($)', font: { color: c.font } },
        tickfont: { color: c.font },
        thickness: 14,
        len: 0.7,
        x: 1.02,
      },
      hovertemplate: 'K: %{x:.1f}<br>T: %{y:.3f}y<br>Price: %{z:.4f}<extra>Model</extra>',
    }

    const traces = [surfaceTrace]

    if (data.market_points && data.market_points.length > 0) {
      traces.push({
        type: 'scatter3d',
        mode: 'markers',
        name: 'Market mid-price',
        x: data.market_points.map(p => 2 * data.S_ref - p.K),
        y: data.market_points.map(p => p.T),
        z: data.market_points.map(p => p.mid_price),
        marker: { size: 1.5, color: '#00bcd4', opacity: 0.6 },
        hovertemplate: 'K: %{x:.1f}<br>T: %{y:.3f}y<br>Mid: $%{z:.4f}<extra>Market</extra>',
      })
    }

    const layout = buildLayout(props.theme, title)

    if (plotted) {
      Plotly.react(plotEl.value, traces, layout, { responsive: true })
    } else {
      Plotly.newPlot(plotEl.value, traces, layout, { responsive: true })
      plotted = true
    }
    emit('surfaceLoaded', {
      market_points: data.market_points,
      K_values: data.K_values,
      T_values: data.T_values,
      z: data.z,
      S_ref: data.S_ref,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => loadAndPlot())
watch(
  () => [props.ticker, props.inputs, props.optionStyle, props.sigmaType, props.theme, optionType.value],
  () => { plotted = false; loadAndPlot() },
  { deep: true },
)
onUnmounted(() => { if (plotEl.value) Plotly.purge(plotEl.value) })
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="section-label">Price Surface</h2>
        <span class="hint">Model price across strikes and maturities vs market mid-prices</span>
      </div>
      <div class="flex items-center gap-3">
        <div v-if="loading" class="flex items-center gap-1.5 text-[11px] text-slate-500">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          Loading…
        </div>
        <div class="flex rounded-md overflow-hidden border border-slate-700 text-[10px] font-semibold">
          <button
            @click="optionType = 'call'"
            :class="['px-2.5 py-1 transition-colors', optionType === 'call' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-emerald-400']"
          >Call</button>
          <button
            @click="optionType = 'put'"
            :class="['px-2.5 py-1 transition-colors', optionType === 'put' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-rose-400']"
          >Put</button>
        </div>
      </div>
    </div>

    <div v-if="!ticker" class="flex items-center justify-center h-64 text-slate-400 text-sm text-center px-6">
      Go to the <strong class="text-slate-300 mx-1">Pricing &amp; Greeks</strong> tab and select a ticker and style to visualize the surface.
    </div>
    <div v-else-if="error" class="flex items-center justify-center h-64 text-rose-400 text-sm">
      {{ error }}
    </div>
    <div v-else ref="plotEl" style="height: 560px;" class="w-full"></div>

    <!-- Divergence note (shown when surface is rendered) -->
    <div v-if="ticker && !loading && !error" class="mt-4 rounded-lg bg-slate-800/70 border border-slate-600/60 px-4 py-3 text-[13px] text-slate-200 leading-relaxed">
      <p v-if="optionStyle === 'european'">
        <span class="text-blue-400 font-semibold">BSM vs. market:</span> Divergence may reflect the volatility smile or model assumptions — BSM uses a single flat vol, while market prices embed a different implied vol per strike. Note that BSM prices <em>European</em> options; most listed equity options are <em>American</em>.
      </p>
      <p v-else>
        <span class="text-blue-400 font-semibold">Model vs. market:</span> Divergence may reflect the volatility smile or the variation in implied vol across strikes — the model uses a single vol input, while market prices embed different IVs per contract.
      </p>
    </div>
  </div>
</template>
