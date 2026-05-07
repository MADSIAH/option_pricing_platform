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
    const S = chart.config.options.plugins?.currentSpot?.value
    if (S == null || !chart.scales.x) return
    const { ctx, scales, chartArea } = chart
    const xPx = scales.x.getPixelForValue(S)
    if (xPx < chartArea.left || xPx > chartArea.right) return

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(xPx, chartArea.top)
    ctx.lineTo(xPx, chartArea.bottom)
    ctx.lineWidth = 1.5
    ctx.strokeStyle = 'rgba(148,163,184,0.35)'
    ctx.setLineDash([5, 5])
    ctx.stroke()

    ctx.fillStyle = 'rgba(148,163,184,0.7)'
    ctx.font = '10px JetBrains Mono, monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`$${S.toFixed(0)}`, xPx, chartArea.top - 6)
    ctx.restore()
  },
}

const props = defineProps({
  chartData: { type: Object, default: null },
  currentS: { type: Number, default: 0 },
})

const canvasEl = ref(null)
let chart = null

function buildChart(data) {
  if (!canvasEl.value || !data) return
  if (chart) { chart.destroy(); chart = null }

  const { spots, calls, puts } = data

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
      plugins: {
        currentSpot: { value: props.currentS },
        legend: {
          position: 'top',
          labels: {
            color: '#94a3b8',
            font: { size: 12, family: 'Inter' },
            usePointStyle: true,
            pointStyleWidth: 12,
            padding: 16,
          },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#94a3b8',
          bodyColor: '#e2e8f0',
          borderColor: '#334155',
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
          ticks: {
            color: '#475569',
            font: { size: 11, family: 'JetBrains Mono, monospace' },
            maxTicksLimit: 7,
            callback: (v) => `$${Number(v).toFixed(0)}`,
          },
          grid: { color: '#1e293b' },
          border: { color: '#1e293b' },
          title: {
            display: true,
            text: 'Underlying Price (S)',
            color: '#475569',
            font: { size: 11 },
          },
        },
        y: {
          ticks: {
            color: '#475569',
            font: { size: 11, family: 'JetBrains Mono, monospace' },
            callback: (v) => `$${v.toFixed(2)}`,
          },
          grid: { color: '#1e293b' },
          border: { color: '#1e293b' },
          beginAtZero: true,
          title: {
            display: true,
            text: 'Option Price',
            color: '#475569',
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
  chart.data.datasets[0].data = spots.map((s, i) => ({ x: s, y: calls[i] }))
  chart.data.datasets[1].data = spots.map((s, i) => ({ x: s, y: puts[i] }))
  chart.config.options.plugins.currentSpot.value = props.currentS
  chart.update('active')
}

onMounted(() => buildChart(props.chartData))

watch(
  () => [props.chartData, props.currentS],
  ([newData]) => {
    if (!newData) return
    if (!chart) buildChart(newData)
    else updateChart(newData)
  },
  { deep: true },
)

onUnmounted(() => { if (chart) chart.destroy() })
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">Sensitivity Analysis</h2>
      <span class="text-[10px] text-slate-600">Option price vs underlying spot</span>
    </div>

    <div v-if="chartData">
      <canvas ref="canvasEl"></canvas>
    </div>
    <div v-else class="flex items-center justify-center h-40 text-slate-600 text-sm">
      Enter valid parameters to see chart
    </div>
  </div>
</template>
