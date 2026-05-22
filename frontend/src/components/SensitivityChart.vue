<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

Chart.register(LineController, LineElement, PointElement, LinearScale, Tooltip, Legend, Filler)

// Inline plugin: draws a vertical dashed line at current spot price
const currentSpotPlugin = {
  id: 'currentSpot',
  afterDraw(chart) {
  const currentSpot = chart.config.options.plugins?.currentSpot
  const S = currentSpot?.value
  if (S == null || !chart.scales.x) return
  const { ctx, scales, chartArea } = chart
  const xPx = scales.x.getPixelForValue(S)
  if (xPx < chartArea.left || xPx > chartArea.right) return

  ctx.save()
  ctx.beginPath()
  ctx.moveTo(xPx, chartArea.top)
  ctx.lineTo(xPx, chartArea.bottom)
  ctx.lineWidth = 1.5
  ctx.strokeStyle = currentSpot?.lineColor || 'rgba(148,163,184,0.35)'
  ctx.setLineDash([5, 5])
  ctx.stroke()

  ctx.fillStyle = currentSpot?.textColor || 'rgba(148,163,184,0.7)'
  ctx.font = '10px JetBrains Mono, monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  ctx.fillText(`$${S.toFixed(0)}`, xPx, chartArea.top - 6)
    ctx.restore()
  },
}

const props = defineProps({
  chartData: { type: Object, default: null },
  currentS: { type: Number, default: 0 },
  theme: { type: String, default: 'dark' },
})

const canvasEl = ref(null)
let chart = null

function paletteForTheme(theme) {
  if (theme === 'light') {
    return {
      tickColor: '#334155',
      gridColor: '#e2e8f0',
      borderColor: '#e2e8f0',
      titleColor: '#64748b',
      tooltipBg: '#ffffff',
      tooltipBorder: '#e2e8f0',
      tooltipTitle: '#64748b',
      tooltipBody: '#0f172a',
      spotLine: 'rgba(100,116,139,0.35)',
      spotText: 'rgba(100,116,139,0.9)',
    }
  }
  return {
    tickColor: '#475569',
    gridColor: '#1e293b',
    borderColor: '#1e293b',
    titleColor: '#475569',
    tooltipBg: '#1e293b',
    tooltipBorder: '#334155',
    tooltipTitle: '#94a3b8',
    tooltipBody: '#e2e8f0',
    spotLine: 'rgba(148,163,184,0.35)',
    spotText: 'rgba(148,163,184,0.7)',
  }
}

function buildChart(data) {
  if (!canvasEl.value || !data) return
  if (chart) { chart.destroy(); chart = null }

  const { spots, calls, puts } = data
  const xMin = spots[0]
  const xMax = spots[spots.length - 1]
  const palette = paletteForTheme(props.theme)

  chart = new Chart(canvasEl.value, {
    type: 'line',
    plugins: [currentSpotPlugin],
    data: {
      datasets: [
        {
          label: 'Call Price',
          data: spots.map((s, i) => ({ x: s, y: calls[i] })),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.07)',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: '#10b981',
          fill: true,
          tension: 0.35,
        },
        {
          label: 'Put Price',
          data: spots.map((s, i) => ({ x: s, y: puts[i] })),
          borderColor: '#f43f5e',
          backgroundColor: 'rgba(244,63,94,0.07)',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: '#f43f5e',
          fill: true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: window.innerWidth < 640 ? 1.4 : 2.2,
      interaction: { mode: 'index', intersect: false },
      layout: {
        padding: { top: 24 },
      },
      plugins: {
        currentSpot: { value: props.currentS, lineColor: palette.spotLine, textColor: palette.spotText },
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: palette.tooltipBg,
          titleColor: palette.tooltipTitle,
          bodyColor: palette.tooltipBody,
          borderColor: palette.tooltipBorder,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            title: (items) => `Spot: $${Number(items[0].parsed.x).toFixed(2)}`,
            label: (item) => ` ${item.dataset.label}: $${item.parsed.y.toFixed(4)}`,
          },
        },
      },
      scales: {
        x: {
          type: 'linear',
          min: xMin,
          max: xMax,
          ticks: {
            color: palette.tickColor,
            font: { size: 11, family: 'JetBrains Mono, monospace' },
            maxTicksLimit: 7,
            callback: (v) => `$${Number(v).toFixed(0)}`,
          },
          grid: { color: palette.gridColor },
          border: { color: palette.borderColor },
          title: {
            display: true,
            text: 'Underlying Price (S)',
            color: palette.titleColor,
            font: { size: 11 },
          },
        },
        y: {
          ticks: {
            color: palette.tickColor,
            font: { size: 11, family: 'JetBrains Mono, monospace' },
            callback: (v) => `$${v.toFixed(2)}`,
          },
          grid: { color: palette.gridColor },
          border: { color: palette.borderColor },
          beginAtZero: true,
          title: {
            display: true,
            text: 'Option Price',
            color: palette.titleColor,
            font: { size: 11 },
          },
        },
      },
    },
  })
}

function updateChart(data) {
  if (!chart || !data) return
  const { spots, calls, puts } = data
  const xMin = spots[0]
  const xMax = spots[spots.length - 1]
  const palette = paletteForTheme(props.theme)
  chart.data.datasets[0].data = spots.map((s, i) => ({ x: s, y: calls[i] }))
  chart.data.datasets[1].data = spots.map((s, i) => ({ x: s, y: puts[i] }))
  chart.config.options.plugins.currentSpot.value = props.currentS
  chart.config.options.plugins.currentSpot.lineColor = palette.spotLine
  chart.config.options.plugins.currentSpot.textColor = palette.spotText
  chart.config.options.plugins.tooltip.backgroundColor = palette.tooltipBg
  chart.config.options.plugins.tooltip.titleColor = palette.tooltipTitle
  chart.config.options.plugins.tooltip.bodyColor = palette.tooltipBody
  chart.config.options.plugins.tooltip.borderColor = palette.tooltipBorder
  chart.config.options.scales.x.ticks.color = palette.tickColor
  chart.config.options.scales.x.grid.color = palette.gridColor
  chart.config.options.scales.x.border.color = palette.borderColor
  chart.config.options.scales.x.title.color = palette.titleColor
  chart.config.options.scales.y.ticks.color = palette.tickColor
  chart.config.options.scales.y.grid.color = palette.gridColor
  chart.config.options.scales.y.border.color = palette.borderColor
  chart.config.options.scales.y.title.color = palette.titleColor
  chart.config.options.scales.x.min = xMin
  chart.config.options.scales.x.max = xMax
  chart.update('active')
}

onMounted(() => buildChart(props.chartData))

watch(
  () => [props.chartData, props.currentS, props.theme],
  ([newData]) => {
    if (!newData) {
      if (chart) { chart.destroy(); chart = null }
      return
    }
    if (!chart) buildChart(newData)
    else updateChart(newData)
  },
  { deep: true },
)

onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="card">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-4">
      <div>
        <h2 class="section-label">Sensitivity Analysis</h2>
        <span class="text-[10px] text-slate-600">Option price vs underlying spot</span>
      </div>
      <div class="flex items-center gap-4 text-[11px] text-slate-300">
        <span class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full border-2 border-emerald-400"></span>
          Call Price
        </span>
        <span class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full border-2 border-rose-400"></span>
          Put Price
        </span>
      </div>
    </div>

    <div v-if="chartData">
      <canvas ref="canvasEl"></canvas>
    </div>
    <div v-else class="flex items-center justify-center h-40 text-slate-600 text-sm">
      Enter valid parameters to see chart
    </div>
  </div>
</template>
