<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { fetchVolSurface } from '../lib/api.js'

const props = defineProps({
  ticker: { type: String, default: null },
  theme:  { type: String, default: 'dark' },
})

const plotEl  = ref(null)
const loading = ref(false)
const error   = ref(null)
let plotted   = false

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
    scene: {
      bgcolor: c.plot,
      aspectmode: 'cube',
      camera: { eye: { x: 1.5, y: -1.8, z: 0.8 } },
      xaxis: {
        title: { text: 'Time to Maturity (years)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        gridcolor: c.grid,
        zerolinecolor: c.grid,
      },
      yaxis: {
        title: { text: 'Strike K ($)', font: { color: c.font, size: 11 } },
        tickfont: { color: c.font, size: 9 },
        gridcolor: c.grid,
        zerolinecolor: c.grid,
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
  loading.value = true
  error.value   = null
  plotted       = false
  try {
    const data  = await fetchVolSurface(props.ticker)
    const title = `Implied Volatility Surface — ${props.ticker}`
    const c     = colors(props.theme)

    let traces
    if (data.grid) {
      traces = [{
        type: 'surface',
        x: data.grid.T_values,
        y: data.grid.K_values,
        z: data.grid.z,
        colorscale: 'Plasma',
        colorbar: {
          title: { text: 'IV (%)', font: { color: c.font, size: 11 } },
          tickfont: { color: c.font, size: 9 },
          ticksuffix: '%',
          thickness: 14, len: 0.65, x: 1.01,
        },
        hovertemplate: 'T: %{x:.3f}y<br>K: $%{y:.1f}<br>IV: %{z:.1f}%<extra></extra>',
      }]
    } else {
      traces = [{
        type: 'scatter3d',
        mode: 'markers',
        x: data.points.map(p => p.T),
        y: data.points.map(p => p.strike),
        z: data.points.map(p => p.implied_vol * 100),
        marker: {
          size: 5,
          color: data.points.map(p => p.implied_vol * 100),
          colorscale: 'Plasma',
          showscale: true,
          colorbar: {
            title: { text: 'IV (%)', font: { color: c.font, size: 11 } },
            tickfont: { color: c.font, size: 9 },
            ticksuffix: '%',
            thickness: 14, len: 0.65, x: 1.01,
          },
        },
        hovertemplate: 'T: %{x:.3f}y<br>K: $%{y:.1f}<br>IV: %{z:.1f}%<extra></extra>',
      }]
    }

    Plotly.newPlot(plotEl.value, traces, buildLayout(props.theme, title), { responsive: true })
    plotted = true
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
        <span class="text-[10px] text-slate-600">Market-implied vol across strikes and maturities</span>
      </div>
      <div v-if="loading" class="flex items-center gap-1.5 text-[11px] text-slate-500">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        Loading…
      </div>
    </div>

    <div v-if="!ticker" class="flex items-center justify-center h-64 text-slate-600 text-sm">
      Select a ticker to view the volatility surface
    </div>
    <div v-else-if="error" class="flex items-center justify-center h-64 text-rose-400 text-sm">
      {{ error }}
    </div>
    <div v-else ref="plotEl" style="height: 520px;" class="w-full"></div>
  </div>
</template>
