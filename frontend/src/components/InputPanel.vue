<script setup>
import { ref, computed, watch } from 'vue'
import { fetchMarket, fetchRFR, WATCHED_TICKERS } from '../lib/api.js'

const props = defineProps({
  modelValue: Object,
  ticker:     { type: String,  default: null },
  method:     { type: String,  default: 'black_scholes' },
  optionStyle:{ type: String,  default: 'european' },
  sigmaType:  { type: String,  default: 'implied' },
})
const emit = defineEmits(['update:modelValue', 'update:ticker', 'update:method', 'update:optionStyle', 'update:sigmaType'])

const lastHistoricalVol = ref(null)
const lastImpliedVol = ref(null)

function sigmaForType(type) {
  if (type === 'implied') return lastImpliedVol.value ?? lastHistoricalVol.value ?? props.modelValue.sigma
  return lastHistoricalVol.value ?? props.modelValue.sigma
}

watch(() => props.sigmaType, (type) => {
  if (!props.ticker) return
  const val = sigmaForType(type)
  if (val != null) emit('update:modelValue', { ...props.modelValue, sigma: val })
})

const showAdvanced = ref(true)
const loading = ref(false)
const error = ref(null)

const EUROPEAN_METHODS = [
  { value: 'black_scholes', label: 'Black-Scholes' },
  { value: 'monte_carlo',   label: 'Monte Carlo' },
  { value: 'binomial_tree', label: 'Binomial Tree' },
]

const AMERICAN_METHODS = [
  { value: 'baw',                 label: 'BAW' },
  { value: 'longstaff_schwartz',  label: 'Longstaff-Schwartz' },
  { value: 'binomial_tree',       label: 'Binomial Tree' },
]

const methods = computed(() =>
  props.optionStyle === 'european' ? EUROPEAN_METHODS : AMERICAN_METHODS
)

function setStyle(s) {
  emit('update:optionStyle', s)
  // Reset method to the default for the new style if current is incompatible
  const valid = (s === 'european' ? EUROPEAN_METHODS : AMERICAN_METHODS).map(m => m.value)
  if (!valid.includes(props.method)) {
    emit('update:method', valid[0])
  }
}

function update(field, raw) {
  const value = raw === '' ? 0 : Number(raw)
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

async function selectTicker(t) {
  emit('update:ticker', t)
  loading.value = true
  error.value = null
  try {
    const data = await fetchMarket(t)
    lastHistoricalVol.value = +(data.historical_vol * 100).toFixed(2)
    lastImpliedVol.value = data.atm_implied_vol != null ? +(data.atm_implied_vol * 100).toFixed(2) : null
    const sigma = sigmaForType(props.sigmaType)
    emit('update:modelValue', {
      ...props.modelValue,
      S: +data.spot_price.toFixed(2),
      r: +(data.risk_free_rate * 100).toFixed(2),
      sigma,
      q: +(data.dividend_yield * 100).toFixed(2),
    })
  } catch (e) {
    error.value = `Could not load data for ${t}`
    emit('update:ticker', null)
  } finally {
    loading.value = false
  }
}

async function selectManual() {
  emit('update:ticker', null)
  loading.value = true
  error.value = null
  let r = 0
  try {
    r = await fetchRFR()
  } catch (e) {
    error.value = 'Could not load risk-free rate'
  } finally {
    emit('update:modelValue', { ...props.modelValue, S: 0, r, sigma: 0, q: 0 })
    loading.value = false
  }
}

const moneyness = computed(() => {
  const { S, K } = props.modelValue
  if (!S || !K || S <= 0 || K <= 0) return null
  const ratio = S / K
  if (Math.abs(ratio - 1) <= 0.005) return { label: 'ATM', cls: 'bg-blue-900/40 text-blue-300 border-blue-800/40' }
  if (ratio > 1) return { label: 'ITM Call / OTM Put', cls: 'bg-emerald-900/40 text-emerald-300 border-emerald-800/40' }
  return { label: 'OTM Call / ITM Put', cls: 'bg-rose-900/40 text-rose-300 border-rose-800/40' }
})

const tYears = computed(() => (props.modelValue.T / 365).toFixed(4))
</script>

<template>
  <div class="card space-y-0">

    <!-- Header -->
    <div class="flex items-center justify-between mb-5">
      <h2 class="section-label">Parameters</h2>
      <span v-if="moneyness" :class="['text-[10px] font-semibold border rounded-full px-2.5 py-0.5', moneyness.cls]">
        {{ moneyness.label }}
      </span>
    </div>

    <!-- Ticker selector -->
    <div class="mb-5 space-y-2">
      <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Stock</p>
      <div class="flex gap-2">
        <button
          v-for="t in WATCHED_TICKERS"
          :key="t"
          @click="selectTicker(t)"
          :class="[
            'flex-1 py-1.5 rounded-lg text-xs font-semibold border transition-colors',
            ticker === t
              ? 'bg-emerald-500 border-emerald-500 text-slate-950'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-emerald-600 hover:text-emerald-400'
          ]"
        >{{ t }}</button>
        <button
          @click="selectManual"
          :class="[
            'flex-1 py-1.5 rounded-lg text-xs font-semibold border transition-colors',
            ticker === null
              ? 'bg-emerald-500 border-emerald-500 text-slate-950'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-emerald-600 hover:text-emerald-400'
          ]"
        >Other</button>
      </div>
      <div v-if="loading" class="flex items-center gap-1.5 text-[11px] text-slate-500">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        Loading market data…
      </div>
      <div v-if="error" class="text-[11px] text-rose-400">{{ error }}</div>
    </div>

    <div class="border-t border-slate-800 mb-5"></div>

    <!-- Option style -->
    <div class="mb-5 space-y-2">
      <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Style</p>
      <div class="flex gap-2">
        <button
          v-for="s in ['european', 'american']"
          :key="s"
          @click="setStyle(s)"
          :class="[
            'flex-1 py-1.5 rounded-lg text-xs font-semibold border capitalize transition-colors',
            optionStyle === s
              ? 'bg-blue-600 border-blue-600 text-white'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-blue-600 hover:text-blue-400'
          ]"
        >{{ s }}</button>
      </div>
    </div>

    <!-- Pricing method -->
    <div class="mb-5 space-y-2">
      <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Method</p>
      <div class="flex flex-col gap-1.5">
        <button
          v-for="m in methods"
          :key="m.value"
          @click="emit('update:method', m.value)"
          :class="[
            'w-full py-1.5 rounded-lg text-xs font-semibold border transition-colors text-left px-3',
            method === m.value
              ? 'bg-violet-600 border-violet-600 text-white'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-violet-600 hover:text-violet-400'
          ]"
        >{{ m.label }}</button>
      </div>
    </div>

    <div class="border-t border-slate-800 mb-5"></div>

    <!-- Position group -->
    <div class="space-y-4">
      <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Position</p>

      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Underlying Price <span class="text-slate-600">(S)</span></label>
        <div class="relative">
          <span class="input-prefix">$</span>
          <input type="number" :value="modelValue.S" @input="update('S', $event.target.value)"
            class="input-field pl-7" min="0.01" step="1" placeholder="150.00" />
        </div>
      </div>

      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Strike Price <span class="text-slate-600">(K)</span></label>
        <div class="relative">
          <span class="input-prefix">$</span>
          <input type="number" :value="modelValue.K" @input="update('K', $event.target.value)"
            class="input-field pl-7" min="0.01" step="1" placeholder="155.00" />
        </div>
      </div>

      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Time to Maturity <span class="text-slate-600">(T)</span></label>
        <div class="relative">
          <input type="number" :value="modelValue.T" @input="update('T', $event.target.value)"
            class="input-field pr-14" min="1" step="1" placeholder="90" />
          <span class="input-suffix">days</span>
        </div>
        <p class="text-[11px] text-slate-600 font-mono">≈ {{ tYears }} years</p>
      </div>
    </div>

    <div class="border-t border-slate-800 my-5"></div>

    <!-- Market Data group -->
    <div class="space-y-4">
      <div class="flex items-center gap-2">
        <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Market Data</p>
        <span class="flex items-center gap-1 text-[10px] text-emerald-500">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          {{ ticker ? 'live · editable' : 'editable' }}
        </span>
      </div>

      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Risk-Free Rate <span class="text-slate-600">(r)</span></label>
        <div class="relative">
          <input type="number" :value="modelValue.r" @input="update('r', $event.target.value)"
            class="input-field pr-8" step="0.01" placeholder="4.50" />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">US 3-Month T-Bill proxy</p>
      </div>

      <div class="space-y-1.5">
        <div class="flex items-center justify-between">
          <label class="text-xs text-slate-400 font-medium">
            {{ sigmaType === 'implied' ? 'Implied' : 'Historical' }} Volatility
            <span class="text-slate-600">(σ)</span>
          </label>
          <div class="flex rounded-md overflow-hidden border border-slate-700 text-[10px] font-semibold">
            <button
              @click="emit('update:sigmaType', 'implied')"
              :class="['px-2 py-0.5 transition-colors', sigmaType === 'implied' ? 'bg-violet-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-violet-400']"
            >IV</button>
            <button
              @click="emit('update:sigmaType', 'historical')"
              :class="['px-2 py-0.5 transition-colors', sigmaType === 'historical' ? 'bg-violet-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-violet-400']"
            >HV</button>
          </div>
        </div>
        <div class="relative">
          <input type="number" :value="modelValue.sigma" @input="update('sigma', $event.target.value)"
            class="input-field pr-8" min="0.1" step="0.1" placeholder="20.0" />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">Annualized {{ sigmaType === 'implied' ? 'implied' : 'historical' }} vol</p>
      </div>
    </div>

    <!-- Advanced toggle -->
    <div class="border-t border-slate-800 mt-5 pt-4">
      <button @click="showAdvanced = !showAdvanced"
        class="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors">
        <svg :class="['w-3.5 h-3.5 transition-transform', showAdvanced ? 'rotate-90' : '']"
          fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Advanced
      </button>

      <div v-if="showAdvanced" class="mt-4 space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Dividend Yield <span class="text-slate-600">(q)</span></label>
        <div class="relative">
          <input type="number" :value="modelValue.q" @input="update('q', $event.target.value)"
            class="input-field pr-8" min="0" step="0.1" placeholder="0.0" />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">Continuous dividend yield (0 for non-dividend stocks)</p>
      </div>
    </div>

  </div>
</template>
