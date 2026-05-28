<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { explainSurfaces } from '../lib/api.js'

const props = defineProps({
  metrics:      { type: Object, default: null },
  ready:        { type: Boolean, default: false },
  ticker:       { type: String, default: null },
  priceSurface: { type: Object, default: null },
  inputs:       { type: Object, default: null },
})

const LEVELS = [
  { key: 'beginner',        label: 'Beginner' },
  { key: 'finance_student', label: 'Student' },
  { key: 'professional',    label: 'Professional' },
]

const level       = ref('finance_student')
const explanation = ref(null)
const loading     = ref(false)
const error       = ref(null)

const explanationHtml = computed(() =>
  explanation.value ? marked.parse(explanation.value) : ''
)

async function runExplain() {
  if (!props.metrics || !props.ready) return
  loading.value     = true
  error.value       = null
  explanation.value = null
  try {
    const ps = props.priceSurface
    const inp = props.inputs
    const context = ps ? {
      pricing_model: ps.style === 'european' ? 'Black-Scholes' : 'Barone-Adesi-Whaley',
      spot_price:    ps.S_ref ?? null,
      vol_used:      ps.sigma ?? null,
      vol_source:    ps.sigma_source ?? null,
      risk_free_rate: inp ? +(inp.r / 100).toFixed(4) : null,
      dividend_yield: inp ? +(inp.q / 100).toFixed(4) : null,
      has_dividend:   inp ? inp.q > 0 : null,
      atm_iv:        props.metrics?.atm_iv ?? null,
      surface_date:  ps.updated_at ?? null,
    } : {}

    const data = await explainSurfaces({
      ...props.metrics,
      ...context,
      user_level:  level.value,
      ticker:      props.ticker,
      option_type: 'call',
    })
    explanation.value = data.explanation
  } catch (e) {
    error.value = e.message.includes('unavailable') || e.message.includes('503') || e.message.includes('502')
      ? 'Gemini is temporarily overloaded — please try again in a moment.'
      : e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="ticker" class="card">

    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="section-label">AI Surface Analysis</h2>
        <span class="hint">Vol smile, model divergence, and liquidity across the surface</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] text-slate-500 uppercase tracking-widest font-semibold mr-1">Level:</span>
        <button
          v-for="lvl in LEVELS"
          :key="lvl.key"
          @click="level = lvl.key"
          :class="[
            'text-xs font-semibold rounded-full px-3 py-1 border transition-colors',
            level === lvl.key
              ? 'bg-violet-900/40 border-violet-600 text-violet-300'
              : 'border-slate-700 text-slate-500 hover:text-slate-300'
          ]"
        >{{ lvl.label }}</button>
      </div>
    </div>

    <!-- Computing hint -->
    <div v-if="!ready && !loading" class="text-[11px] text-slate-500 mb-3 flex items-center gap-1.5">
      <span class="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse"></span>
      Computing surface metrics…
    </div>

    <!-- Explain button -->
    <button
      @click="runExplain"
      :disabled="!ready || loading"
      class="w-full py-3 rounded-xl bg-violet-700 hover:bg-violet-600 active:bg-violet-800 text-white font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
    >
      <svg v-if="!loading" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ loading ? 'Analysing surfaces…' : 'Explain these surfaces' }}
    </button>

    <!-- Disclaimer -->
    <p class="mt-2 text-center text-[10px] text-rose-400/80 font-bold tracking-wide">
      Educational tool — not investment advice.
    </p>

    <!-- Rendered markdown output -->
    <div
      v-if="explanationHtml"
      class="explain-prose mt-4 bg-slate-900/60 rounded-xl border border-slate-800 p-4"
      v-html="explanationHtml"
    />
    <div v-if="error" class="mt-3 text-sm text-rose-400">{{ error }}</div>

  </div>
</template>

<style scoped>
.explain-prose :deep(h1),
.explain-prose :deep(h2),
.explain-prose :deep(h3) {
  color: #c4b5fd;
  font-weight: 700;
  margin-top: 1rem;
  margin-bottom: 0.35rem;
}
.explain-prose :deep(h1) { font-size: 0.95rem; }
.explain-prose :deep(h2) { font-size: 0.875rem; }
.explain-prose :deep(h3) { font-size: 0.8rem; letter-spacing: 0.02em; }
.explain-prose :deep(p) {
  color: #cbd5e1;
  font-size: 0.8rem;
  line-height: 1.65;
  margin-bottom: 0.6rem;
}
.explain-prose :deep(ul),
.explain-prose :deep(ol) {
  color: #cbd5e1;
  font-size: 0.8rem;
  padding-left: 1.25rem;
  margin-bottom: 0.6rem;
  list-style: disc;
}
.explain-prose :deep(ol) { list-style: decimal; }
.explain-prose :deep(li) { margin-bottom: 0.2rem; line-height: 1.55; }
.explain-prose :deep(strong) { color: #e2e8f0; font-weight: 600; }
.explain-prose :deep(em) { color: #a5b4fc; font-style: italic; }
.explain-prose :deep(code) {
  background: #1e293b;
  color: #7dd3fc;
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}
.explain-prose :deep(hr) {
  border-color: #334155;
  margin: 0.75rem 0;
}
</style>
