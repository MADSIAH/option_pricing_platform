<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { computeRange } from './lib/blackScholes.js'
import { fetchRFR, priceOption } from './lib/api.js'
import NavBar from './components/NavBar.vue'
import InputPanel from './components/InputPanel.vue'
import PriceDisplay from './components/PriceDisplay.vue'
import GreeksGrid from './components/GreeksGrid.vue'
import SensitivityChart from './components/SensitivityChart.vue'

const ticker = ref(null)
const method = ref('black_scholes')
const optionStyle = ref('european')

const inputs = ref({ S: 0, K: 0, T: 0, r: 0, sigma: 0, q: 0 })

const result = ref(null)
const priceLoading = ref(false)
const priceError = ref(null)

onMounted(async () => {
  try { inputs.value.r = await fetchRFR() } catch { /* leave at 0 */ }
})

const canPrice = computed(() => {
  const { S, K, T, sigma } = inputs.value
  return S > 0 && K > 0 && T > 0 && sigma > 0
})

// Sensitivity chart stays on local JS BS — needs to be instant/real-time
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
      r: inputs.value.r / 100,
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
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100" style="font-family: Inter, system-ui, sans-serif;">
    <NavBar :r="inputs.r" :sigma="inputs.sigma" :ticker="ticker" />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">

        <!-- Left: parameter inputs -->
        <div class="lg:col-span-2">
          <InputPanel
            v-model="inputs"
            v-model:ticker="ticker"
            v-model:method="method"
            v-model:optionStyle="optionStyle"
          />
        </div>

        <!-- Right: results -->
        <div class="lg:col-span-3 flex flex-col gap-5">
          <PriceDisplay
            :result="result"
            :inputs="inputs"
            :loading="priceLoading"
            :error="priceError"
          />
          <GreeksGrid :result="result" />
          <SensitivityChart :chart-data="chartData" :current-s="inputs.S" />
        </div>

      </div>
    </main>

    <footer class="mt-12 border-t border-slate-800 py-6 text-center text-xs text-slate-600">
      Option Pricing Platform · Black-Scholes · Monte Carlo · Binomial Tree · BAW · For educational purposes
    </footer>
  </div>
</template>
