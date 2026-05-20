<script setup>
defineProps({
  result:  { type: Object,  default: null },
  inputs:  { type: Object,  required: true },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
})

const METHOD_LABELS = {
  black_scholes:      'Black-Scholes',
  monte_carlo:        'Monte Carlo',
  binomial_tree:      'Binomial Tree',
  baw:                'BAW',
  longstaff_schwartz: 'Longstaff-Schwartz',
}

function fmt6(val) {
  if (val == null || isNaN(val)) return '—'
  return val.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 6 })
}

function moneynessBadge(S, K, isCall) {
  if (!S || !K) return null
  const ratio = S / K
  const atm = Math.abs(ratio - 1) <= 0.005
  if (atm) return { label: 'ATM', cls: 'text-blue-400' }
  const itm = isCall ? ratio > 1 : ratio < 1
  return itm ? { label: 'ITM', cls: 'text-emerald-400' } : { label: 'OTM', cls: 'text-slate-500' }
}
</script>

<template>
  <div class="card">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-label">Option Prices</h2>
      <div v-if="result" class="flex items-center gap-2">
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

    <template v-else-if="result">

      <!-- Primary price cards (selected method) -->
      <div class="grid grid-cols-2 gap-4 mb-5">

        <!-- Call -->
        <div class="bg-slate-950 rounded-xl border border-emerald-900/40 p-4 sm:p-5">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold text-emerald-500 uppercase tracking-widest">Call</span>
            <span v-if="moneynessBadge(inputs.S, inputs.K, true)"
              :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, true).cls]">
              {{ moneynessBadge(inputs.S, inputs.K, true).label }}
            </span>
          </div>
          <div class="text-xl sm:text-2xl font-mono font-bold text-emerald-400 leading-none">
            ${{ fmt6(result.call.price) }}
          </div>
          <div class="mt-1.5 text-[10px] text-violet-400 font-semibold">
            {{ METHOD_LABELS[result.method] }}
          </div>
        </div>

        <!-- Put -->
        <div class="bg-slate-950 rounded-xl border border-rose-900/40 p-4 sm:p-5">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold text-rose-500 uppercase tracking-widest">Put</span>
            <span v-if="moneynessBadge(inputs.S, inputs.K, false)"
              :class="['text-[10px] font-semibold', moneynessBadge(inputs.S, inputs.K, false).cls]">
              {{ moneynessBadge(inputs.S, inputs.K, false).label }}
            </span>
          </div>
          <div class="text-xl sm:text-2xl font-mono font-bold text-rose-400 leading-none">
            ${{ fmt6(result.put.price) }}
          </div>
          <div class="mt-1.5 text-[10px] text-violet-400 font-semibold">
            {{ METHOD_LABELS[result.method] }}
          </div>
        </div>

      </div>

      <!-- Method comparison table -->
      <div class="border-t border-slate-800 pt-4">
        <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold mb-3">Method Comparison</p>
        <table class="w-full text-xs">
          <thead>
            <tr class="text-[10px] text-slate-600 uppercase tracking-wider">
              <th class="text-left font-semibold pb-2 pr-4">Method</th>
              <th class="text-right font-semibold pb-2 pr-4">Call</th>
              <th class="text-right font-semibold pb-2">Put</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(prices, mKey) in result.allPrices"
              :key="mKey"
              :class="[
                'border-t border-slate-800/60 transition-colors',
                mKey === result.method ? 'bg-violet-900/10' : ''
              ]"
            >
              <td class="py-2 pr-4">
                <div class="flex items-center gap-2">
                  <span :class="[
                    'font-medium',
                    mKey === result.method ? 'text-violet-300' : 'text-slate-400'
                  ]">{{ METHOD_LABELS[mKey] }}</span>
                  <span v-if="mKey === result.method"
                    class="text-[9px] font-bold text-violet-400 border border-violet-700/50 rounded-full px-1.5 py-0.5">
                    active
                  </span>
                </div>
              </td>
              <td :class="[
                'py-2 pr-4 text-right font-mono',
                mKey === result.method ? 'text-emerald-400 font-bold' : 'text-slate-400'
              ]">
                ${{ fmt6(prices.call) }}
              </td>
              <td :class="[
                'py-2 text-right font-mono',
                mKey === result.method ? 'text-rose-400 font-bold' : 'text-slate-400'
              ]">
                ${{ fmt6(prices.put) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Put-call parity note (European only) -->
      <div v-if="result.style === 'european'" class="mt-3 pt-3 border-t border-slate-800">
        <div class="text-[10px] text-slate-700 font-mono">
          Put-Call Parity: C − P = Se^(−qT) − Ke^(−rT)
        </div>
      </div>

    </template>

    <!-- Empty state -->
    <div v-else class="flex items-center justify-center h-28 text-slate-600 text-sm">
      Enter valid parameters to see prices
    </div>

  </div>
</template>
