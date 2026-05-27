<script setup>
defineProps({
  r:        { type: Number,  default: 4.5 },
  sigma:    { type: Number,  default: 20 },
  ticker:   { type: String,  default: null },
  theme:    { type: String,  default: 'dark' },
  chatOpen: { type: Boolean, default: false },
})

defineEmits(['toggle-theme', 'toggle-chat'])

const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
</script>

<template>
  <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between sm:h-20">

        <!-- Brand -->
        <div class="flex items-center gap-4 shrink-0">
          <div class="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center font-bold text-slate-950 text-xl select-none">
            Δ
          </div>
          <div>
            <div class="font-bold text-slate-100 text-xl leading-none tracking-tight">OptionDesk</div>
            <div class="text-xs text-slate-500 leading-none mt-1 hidden sm:block">
              Options Pricing, Made Simple.
            </div>
          </div>
        </div>

        <!-- Market data pills + controls -->
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
          <div class="hint hidden md:block">{{ today }}</div>

          <!-- Ask AI toggle -->
          <button
            @click="$emit('toggle-chat')"
            :class="[
              'flex items-center gap-2 rounded-xl border px-6 py-3 text-lg font-bold transition-colors',
              chatOpen
                ? 'bg-violet-700 border-violet-500 text-white shadow-lg shadow-violet-900/40'
                : 'border-violet-600 bg-violet-900/30 text-violet-300 hover:bg-violet-700 hover:border-violet-500 hover:text-white'
            ]"
            type="button"
            aria-label="Toggle AI chat panel"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
            Ask AI
          </button>

          <!-- Theme toggle -->
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
