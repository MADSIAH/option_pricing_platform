<script setup>
import { ref, computed } from 'vue'
import { compute, computeRange } from './lib/blackScholes.js'
import NavBar from './components/NavBar.vue'
import InputPanel from './components/InputPanel.vue'
import PriceDisplay from './components/PriceDisplay.vue'
import GreeksGrid from './components/GreeksGrid.vue'
import SensitivityChart from './components/SensitivityChart.vue'

// Default inputs – r and sigma pre-populated from market context shown in NavBar
const inputs = ref({
  S: 150,
  K: 155,
  T: 90,       // calendar days
  r: 4.50,     // percent
  sigma: 20.0, // percent (implied vol)
  q: 0.0,      // percent dividend yield
})

const result = computed(() => {
  const { S, K, T, r, sigma, q } = inputs.value
  return compute(S, K, T / 365, r / 100, sigma / 100, q / 100)
})

const chartData = computed(() => {
  const { S, K, T, r, sigma, q } = inputs.value
  if (!S || S <= 0) return null
  const sMin = S * 0.55
  const sMax = S * 1.45
  return computeRange(K, T / 365, r / 100, sigma / 100, q / 100, sMin, sMax)
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100" style="font-family: Inter, system-ui, sans-serif;">
    <NavBar :r="inputs.r" :sigma="inputs.sigma" />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">

        <!-- Left: parameter inputs -->
        <div class="lg:col-span-2">
          <InputPanel v-model="inputs" />
        </div>

        <!-- Right: results -->
        <div class="lg:col-span-3 flex flex-col gap-5">
          <PriceDisplay :result="result" :inputs="inputs" />
          <GreeksGrid :result="result" />
          <SensitivityChart :chart-data="chartData" :current-s="inputs.S" />
        </div>

      </div>
    </main>

    <footer class="mt-12 border-t border-slate-800 py-6 text-center text-xs text-slate-600">
      Black-Scholes-Merton · European options only · For educational purposes
    </footer>
  </div>
</template>
