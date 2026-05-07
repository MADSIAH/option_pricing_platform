<script setup>
defineProps({
  r: { type: Number, default: 4.5 },
  sigma: { type: Number, default: 20 },
})

const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
</script>

<template>
  <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-14 sm:h-16">

        <!-- Brand -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center font-bold text-slate-950 text-base select-none">
            Δ
          </div>
          <div>
            <div class="font-semibold text-slate-100 text-base leading-none tracking-tight">OptionDesk</div>
            <div class="text-[10px] text-slate-500 leading-none mt-0.5 hidden sm:block">
              Black-Scholes · European Options
            </div>
          </div>
        </div>

        <!-- Market data pills -->
        <div class="flex items-center gap-2 sm:gap-3">
          <div class="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="text-xs text-slate-400 hidden sm:inline">Risk-Free</span>
            <span class="text-xs font-mono font-semibold text-emerald-400">{{ r.toFixed(2) }}%</span>
          </div>
          <div class="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
            <span class="text-xs text-slate-400 hidden sm:inline">Vol</span>
            <span class="text-xs font-mono font-semibold text-blue-400">{{ sigma.toFixed(1) }}%</span>
          </div>
          <div class="text-[10px] text-slate-600 hidden md:block">{{ today }}</div>
        </div>

      </div>
    </div>
  </header>
</template>
