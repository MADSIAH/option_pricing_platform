<script setup>
import { ref } from 'vue'

defineProps({
  result: { type: Object, default: null },
})

const activeTab = ref('call')

const greeks = [
  {
    key: 'delta',
    symbol: 'Δ',
    name: 'Delta',
    desc: 'Price Δ per $1 spot move',
    format: (v) => v.toFixed(4),
  },
  {
    key: 'gamma',
    symbol: 'Γ',
    name: 'Gamma',
    desc: 'Delta Δ per $1 spot move',
    format: (v) => Math.abs(v) < 0.0001 ? v.toExponential(3) : v.toFixed(5),
  },
  {
    key: 'vega',
    symbol: 'ν',
    name: 'Vega',
    desc: 'Price Δ per 1% vol move',
    format: (v) => v.toFixed(4),
  },
  {
    key: 'theta',
    symbol: 'Θ',
    name: 'Theta',
    desc: 'Price decay per day',
    format: (v) => v.toFixed(4),
  },
  {
    key: 'rho',
    symbol: 'ρ',
    name: 'Rho',
    desc: 'Price Δ per 1% rate move',
    format: (v) => v.toFixed(4),
  },
]

function valueClass(val) {
  if (val == null || isNaN(val)) return 'text-slate-400'
  return val > 0 ? 'text-emerald-400' : val < 0 ? 'text-rose-400' : 'text-slate-400'
}
</script>

<template>
  <div class="card">

    <!-- Header + tab toggle -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">Greeks</h2>
      <div v-if="result" class="flex gap-0.5 bg-slate-950 rounded-lg p-0.5 border border-slate-800">
        <button
          @click="activeTab = 'call'"
          :class="[
            'text-xs font-semibold px-3 py-1 rounded-md transition-all',
            activeTab === 'call'
              ? 'bg-emerald-600 text-white shadow'
              : 'text-slate-500 hover:text-slate-300'
          ]"
        >
          Call
        </button>
        <button
          @click="activeTab = 'put'"
          :class="[
            'text-xs font-semibold px-3 py-1 rounded-md transition-all',
            activeTab === 'put'
              ? 'bg-rose-600 text-white shadow'
              : 'text-slate-500 hover:text-slate-300'
          ]"
        >
          Put
        </button>
      </div>
    </div>

    <!-- Greek cards -->
    <div v-if="result" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      <div
        v-for="g in greeks"
        :key="g.key"
        class="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl p-3.5 transition-colors"
      >
        <!-- Symbol + name -->
        <div class="flex items-baseline gap-1.5 mb-2">
          <span class="text-base font-mono text-slate-500 leading-none">{{ g.symbol }}</span>
          <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{{ g.name }}</span>
        </div>
        <!-- Value -->
        <div :class="['text-lg font-mono font-bold leading-none', valueClass(result[activeTab][g.key])]">
          {{ g.format(result[activeTab][g.key]) }}
        </div>
        <!-- Description -->
        <div class="hint mt-2 leading-tight">{{ g.desc }}</div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="flex items-center justify-center h-20 text-slate-400 text-sm text-center px-4">
      Price an option using the Parameters panel on the left — Greeks will appear here.
    </div>

    <!-- Gamma/Vega note -->
    <div v-if="result" class="hint mt-3 pt-3 border-t border-slate-800 flex gap-4">
      <span>Gamma and Vega are identical for call and put under Black-Scholes (European options only; this symmetry does not hold for American-style options).</span>
    </div>

  </div>
</template>
