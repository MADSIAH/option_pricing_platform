<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { computeRange } from './lib/blackScholes.js'
import { fetchRFR, priceOption } from './lib/api.js'
import NavBar from './components/NavBar.vue'
import InputPanel from './components/InputPanel.vue'
import PriceDisplay from './components/PriceDisplay.vue'
import GreeksGrid from './components/GreeksGrid.vue'
import SensitivityChart from './components/SensitivityChart.vue'
import VolSurface from './components/VolSurface.vue'
import PriceSurface from './components/PriceSurface.vue'
import ChatPanel from './components/ChatPanel.vue'
import ExplainPanel from './components/ExplainPanel.vue'
import SurfaceExplainPanel from './components/SurfaceExplainPanel.vue'
import { useSurfaceMetrics } from './lib/useSurfaceMetrics.js'

const ticker = ref(null)
const method = ref('black_scholes')
const optionStyle = ref('european')
const sigmaType = ref('implied')
const view = ref('pricing')
const isStale = ref(false)
const marketUpdatedAt = ref(null)
const chatOpen = ref(false)

const inputs = ref({ S: 0, K: 0, T: 0, r: 0, sigma: 0, q: 0 })

const result = ref(null)
const priceLoading = ref(false)
const priceError = ref(null)

const theme = ref('dark')

const volSurfaceData   = ref(null)
const priceSurfaceData = ref(null)
const { metrics: surfaceMetrics, ready: surfaceReady } = useSurfaceMetrics(volSurfaceData, priceSurfaceData)

function applyTheme(value) {
  const root = document.documentElement
  root.classList.toggle('theme-light', value === 'light')
  localStorage.setItem('theme', value)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  applyTheme(theme.value)
}

onMounted(async () => {
  const storedTheme = localStorage.getItem('theme')
  if (storedTheme === 'light' || storedTheme === 'dark') {
    theme.value = storedTheme
  } else {
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
    if (prefersLight) theme.value = 'light'
  }
  applyTheme(theme.value)
  try { inputs.value.r = await fetchRFR() } catch { /* leave at 0 */ }
})

const canPrice = computed(() => {
  const { S, K, T, sigma } = inputs.value
  return S > 0 && K > 0 && T > 0 && sigma > 0
})

const chartData = computed(() => {
  const { S, K, T, r, sigma, q } = inputs.value
  if (!canPrice.value) return null
  const sMin = S * 0.55
  const sMax = S * 1.45
  return computeRange(K, T / 365, r / 100, sigma / 100, q / 100, sMin, sMax)
})

let debounceTimer = null

async function loadPrices() {
  if (!canPrice.value) { result.value = null; return }
  priceLoading.value = true
  priceError.value = null
  try {
    const base = {
      S: inputs.value.S,
      K: inputs.value.K,
      T: inputs.value.T / 365,
      r: inputs.value.r != null ? inputs.value.r / 100 : null,
      q: inputs.value.q / 100,
      sigma: inputs.value.sigma / 100,
      style: optionStyle.value,
      method: 'all',
      mc_paths: optionStyle.value === 'european' ? 50000 : 5000,
    }
    const [callRes, putRes] = await Promise.all([
      priceOption({ ...base, option_type: 'call' }),
      priceOption({ ...base, option_type: 'put' }),
    ])

    const mKey = method.value
    const cm = callRes.prices[mKey]
    const pm = putRes.prices[mKey]

    result.value = {
      call: { price: cm.price, ...cm.greeks },
      put:  { price: pm.price, ...pm.greeks },
      allPrices: Object.fromEntries(
        Object.entries(callRes.prices).map(([k, v]) => [k, { call: v.price, put: putRes.prices[k].price }])
      ),
      sigma: callRes.sigma,
      method: method.value,
      style: optionStyle.value,
    }
  } catch (e) {
    priceError.value = e.message
    result.value = null
  } finally {
    priceLoading.value = false
  }
}

watch([inputs, method, optionStyle], () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadPrices, 500)
}, { deep: true })

watch(ticker, () => {
  volSurfaceData.value   = null
  priceSurfaceData.value = null
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100" style="font-family: Inter, system-ui, sans-serif;">
    <NavBar
      :r="inputs.r"
      :sigma="inputs.sigma"
      :spot="inputs.S"
      :ticker="ticker"
      :theme="theme"
      :chat-open="chatOpen"
      @toggle-theme="toggleTheme"
      @toggle-chat="chatOpen = !chatOpen"
    />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">

      <!-- Tab navigation -->
      <div class="flex gap-1 mb-6 border-b border-slate-800">
        <button
          v-for="tab in [{ key: 'pricing', label: 'Pricing & Greeks' }, { key: 'surfaces', label: 'Surfaces' }]"
          :key="tab.key"
          @click="view = tab.key"
          :class="[
            'px-7 py-3.5 text-lg font-bold transition-colors border-b-2 -mb-px',
            view === tab.key
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-300'
          ]"
        >{{ tab.label }}</button>
      </div>

      <!-- Pricing & Greeks view -->
      <div v-if="view === 'pricing'" class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-2">
          <InputPanel
            v-model="inputs"
            v-model:ticker="ticker"
            v-model:method="method"
            v-model:optionStyle="optionStyle"
            v-model:sigmaType="sigmaType"
            v-model:isStale="isStale"
            v-model:updatedAt="marketUpdatedAt"
          />
        </div>
        <div class="lg:col-span-3 flex flex-col gap-5">
          <PriceDisplay
            :result="result"
            :inputs="inputs"
            :loading="priceLoading"
            :error="priceError"
          />
          <GreeksGrid :result="result" />

          <!-- Navigation nudge: only when a ticker is selected (hidden in manual mode) -->
          <div v-if="result && ticker" class="text-[12px] text-slate-200 border border-emerald-700/60 rounded-xl px-4 py-3 bg-emerald-900/20 leading-snug">
            Explore the <button @click="view = 'surfaces'" class="text-emerald-400 hover:underline font-semibold">Vol Surface</button> to see how implied volatility varies across strikes and maturities — or the <button @click="view = 'surfaces'" class="text-emerald-400 hover:underline font-semibold">Price Surface</button> to compare model prices against the market.
          </div>

          <ExplainPanel :result="result" :inputs="inputs" />
          <SensitivityChart v-if="optionStyle === 'european'" :chart-data="chartData" :current-s="inputs.S" :current-k="inputs.K" :theme="theme" />
        </div>
      </div>

      <!-- Surfaces view -->
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
          :price-surface="priceSurfaceData"
          :inputs="inputs"
        />
      </div>

    </main>

    <footer class="mt-12 border-t border-slate-800 py-6 text-center text-xs text-slate-500">
      Option Pricing Platform · BSM · CRR (Binomial Tree) · Monte Carlo · BAW · Longstaff-Schwartz · For educational purposes
    </footer>

    <!-- Chat panel (rendered outside main flow, fixed positioned) -->
    <ChatPanel :open="chatOpen" @close="chatOpen = false" />
  </div>
</template>
