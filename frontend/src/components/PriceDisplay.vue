<script setup>
defineProps({
  result:  { type: Object,  default: null },
  inputs:  { type: Object,  required: true },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})

const METHOD_LABELS = {
  black_scholes:       'Black-Scholes',
  monte_carlo:         'Monte Carlo',
  binomial_tree:       'Binomial Tree',
  baw:                 'Barone-Adesi-Whaley',
  longstaff_schwartz:  'Longstaff-Schwartz',
}

function fmt(val, d = 4) {
  if (val == null || isNaN(val)) return '—'
  return val.toFixed(d)
}

function fmtPrice(val) {
  if (val == null || isNaN(val)) return '—'
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function moneynessBadge(S, K, isCall) {
  if (!S || !K) return null
  const ratio = S / K
  const atm = Math.abs(ratio - 1) <= 0.005
  if (atm) return { label: 'ATM', cls: 'text-blue-400' }
  const itm = isCall ? ratio > 1 : ratio < 1
  return itm
    ? { label: 'ITM', cls: 'text-emerald-400' }
    : { label: 'OTM', cls: 'text-slate-500' }
}
</script>

<template>
  <div class="card">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">Option Prices</h2>
      <div v-if="result" class="flex items-center gap-2">
        <span class="text-[10px] font-semibold border border-violet-800/60 bg-violet-900/20 text-violet-300 rounded-full px-2.5 py-0.5">
          {{ METHOD_LABELS[result.method] || result.method }}
        </span>
        <span class="text-[10px] font-semibold border border-blue-800/60 bg-blue-900/20 text-blue-300 rounded-full px-2.5 py-0.5 capitalize">
          {{ result.style }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-28 gap-2 text-slate-500 text-sm">
      <span class="w-2 h-2 rounded-full bg-violet-400 animate-pulse"></span>
      Computing…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex items-center justify-center h-28 text-rose-400 text-sm px-4 text-center">
      {{ error }}
    </div>

    <!-- Price cards -->
    <div v-else-if="result" class="grid grid-cols-2 gap-4">

      <!-- Call -->
      <div class="bg-slate-950 rounded-xl border border-emerald-900/40 p-4 sm:p-5">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold text-emerald-500 uppercase tracking-widest">Call</span>
          <span v-if="moneynessBadge(inputs.S, inputs.K, true)"
            :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, true).cls]">
            {{ moneynessBadge(inputs.S, inputs.K, true).label }}
          </span>
        </div>
        <div class="text-2xl sm:text-3xl font-mono font-bold text-emerald-400 leading-none">
          ${{ fmtPrice(result.call.price) }}
        </div>
      </div>

      <!-- Put -->
      <div class="bg-slate-950 rounded-xl border border-rose-900/40 p-4 sm:p-5">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-bold text-rose-500 uppercase tracking-widest">Put</span>
          <span v-if="moneynessBadge(inputs.S, inputs.K, false)"
            :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, false).cls]">
            {{ moneynessBadge(inputs.S, inputs.K, false).label }}
          </span>
        </div>
        <div class="text-2xl sm:text-3xl font-mono font-bold text-rose-400 leading-none">
          ${{ fmtPrice(result.put.price) }}
        </div>
      </div>

    </div>

    <!-- Empty state -->
    <div v-else class="flex items-center justify-center h-28 text-slate-600 text-sm">
      Enter valid parameters to see prices
    </div>

    <!-- Put-call parity — only meaningful for European options -->
    <div v-if="result && result.style === 'european'" class="mt-4 pt-3 border-t border-slate-800">
      <div class="flex items-center gap-2 text-[11px] text-slate-600 font-mono flex-wrap">
        <span class="text-slate-700">Put-Call Parity</span>
        <span>C − P = Se^(−qT) − Ke^(−rT)</span>
      </div>
    </div>

  </div>
</template>
