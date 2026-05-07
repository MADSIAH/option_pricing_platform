<script setup>
defineProps({
  result: { type: Object, default: null },
  inputs: { type: Object, required: true },
})

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
    <h2 class="section-label mb-4">Option Prices</h2>

    <!-- Price cards -->
    <div v-if="result" class="grid grid-cols-2 gap-4">

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
        <div class="mt-2.5 text-[11px] text-slate-600 font-mono space-y-0.5">
          <div>d₁ = {{ fmt(result.d1) }}</div>
          <div>d₂ = {{ fmt(result.d2) }}</div>
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
        <div class="mt-2.5 text-[11px] text-slate-600 font-mono space-y-0.5">
          <div>C − P = ${{ fmt(result.call.price - result.put.price, 4) }}</div>
          <div>Parity = ${{ fmt(result.putCallParity, 4) }}</div>
        </div>
      </div>

    </div>

    <!-- Empty state -->
    <div v-else class="flex items-center justify-center h-28 text-slate-600 text-sm">
      Enter valid parameters to see prices
    </div>

    <!-- Put-call parity verification -->
    <div v-if="result" class="mt-4 pt-3 border-t border-slate-800">
      <div class="flex items-center gap-2 text-[11px] text-slate-600 font-mono">
        <span class="text-slate-700">Put-Call Parity</span>
        <span>C − P = Se^(−qT) − Ke^(−rT)</span>
        <span class="ml-auto text-emerald-600">✓ {{ Math.abs(result.call.price - result.put.price - result.putCallParity) < 1e-8 ? 'exact' : 'Δ=' + (result.call.price - result.put.price - result.putCallParity).toExponential(2) }}</span>
      </div>
    </div>
  </div>
</template>
