<script setup>
defineProps({
  r: { type: Number, default: 4.5 },
  sigma: { type: Number, default: 20 },
  ticker: { type: String, default: null },
  theme: { type: String, default: 'dark' },
})

defineEmits(['toggle-theme'])

const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
</script>

<template>
  <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:h-16">

        <!-- Brand -->
        <div class="flex items-center gap-3 shrink-0">
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
        <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto sm:justify-end">
          <div v-if="ticker" class="flex items-center gap-1.5 bg-emerald-900/30 border border-emerald-700/50 rounded-full px-3 py-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span class="text-xs font-mono font-semibold text-emerald-300">{{ ticker }}</span>
          </div>
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
          <button
            class="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-semibold text-slate-300 transition-colors hover:border-emerald-500 hover:text-emerald-400"
            @click="$emit('toggle-theme')"
            type="button"
            aria-label="Toggle light and dark mode"
          >
            <svg v-if="theme === 'light'" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.36 6.36-1.42-1.42M7.05 7.05 5.64 5.64m12.72 0-1.41 1.41M7.05 16.95l-1.41 1.41M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z" />
            </svg>
            <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 0 1 11.21 3 7 7 0 1 0 21 12.79z" />
            </svg>
            <span class="hidden sm:inline">{{ theme === 'light' ? 'Dark' : 'Light' }}</span>
          </button>
        </div>

      </div>
    </div>
  </header>
</template>
