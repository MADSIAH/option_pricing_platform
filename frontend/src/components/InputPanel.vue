<script setup>
import { ref, computed } from 'vue'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const showAdvanced = ref(false)

function update(field, raw) {
  const value = raw === '' ? 0 : Number(raw)
  emit('update:modelValue', { ...props.modelValue, [field]: value })
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

    <!-- Position group -->
    <div class="space-y-4">
      <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Position</p>

      <!-- Underlying Price -->
      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Underlying Price <span class="text-slate-600">(S)</span></label>
        <div class="relative">
          <span class="input-prefix">$</span>
          <input
            type="number"
            :value="modelValue.S"
            @input="update('S', $event.target.value)"
            class="input-field pl-7"
            min="0.01" step="1" placeholder="150.00"
          />
        </div>
      </div>

      <!-- Strike Price -->
      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Strike Price <span class="text-slate-600">(K)</span></label>
        <div class="relative">
          <span class="input-prefix">$</span>
          <input
            type="number"
            :value="modelValue.K"
            @input="update('K', $event.target.value)"
            class="input-field pl-7"
            min="0.01" step="1" placeholder="155.00"
          />
        </div>
      </div>

      <!-- Time to Maturity -->
      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Time to Maturity <span class="text-slate-600">(T)</span></label>
        <div class="relative">
          <input
            type="number"
            :value="modelValue.T"
            @input="update('T', $event.target.value)"
            class="input-field pr-14"
            min="1" step="1" placeholder="90"
          />
          <span class="input-suffix">days</span>
        </div>
        <p class="text-[11px] text-slate-600 font-mono">≈ {{ tYears }} years</p>
      </div>
    </div>

    <!-- Divider -->
    <div class="border-t border-slate-800 my-5"></div>

    <!-- Market Data group -->
    <div class="space-y-4">
      <div class="flex items-center gap-2">
        <p class="text-[10px] text-slate-600 uppercase tracking-widest font-semibold">Market Data</p>
        <span class="flex items-center gap-1 text-[10px] text-emerald-500">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          pre-filled · editable
        </span>
      </div>

      <!-- Risk-Free Rate -->
      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Risk-Free Rate <span class="text-slate-600">(r)</span></label>
        <div class="relative">
          <input
            type="number"
            :value="modelValue.r"
            @input="update('r', $event.target.value)"
            class="input-field pr-8"
            step="0.01" placeholder="4.50"
          />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">US 3-Month T-Bill proxy</p>
      </div>

      <!-- Implied Volatility -->
      <div class="space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Implied Volatility <span class="text-slate-600">(σ)</span></label>
        <div class="relative">
          <input
            type="number"
            :value="modelValue.sigma"
            @input="update('sigma', $event.target.value)"
            class="input-field pr-8"
            min="0.1" step="0.1" placeholder="20.0"
          />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">Annualized implied vol for this option</p>
      </div>
    </div>

    <!-- Advanced toggle -->
    <div class="border-t border-slate-800 mt-5 pt-4">
      <button
        @click="showAdvanced = !showAdvanced"
        class="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <svg
          :class="['w-3.5 h-3.5 transition-transform', showAdvanced ? 'rotate-90' : '']"
          fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Advanced
      </button>

      <div v-if="showAdvanced" class="mt-4 space-y-1.5">
        <label class="text-xs text-slate-400 font-medium">Dividend Yield <span class="text-slate-600">(q)</span></label>
        <div class="relative">
          <input
            type="number"
            :value="modelValue.q"
            @input="update('q', $event.target.value)"
            class="input-field pr-8"
            min="0" step="0.1" placeholder="0.0"
          />
          <span class="input-suffix">%</span>
        </div>
        <p class="text-[11px] text-slate-600">Continuous dividend yield (0 for non-dividend stocks)</p>
      </div>
    </div>

  </div>
</template>
