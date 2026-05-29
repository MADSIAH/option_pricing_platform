<script setup>
import { ref, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { sendChat } from '../lib/api.js'

const props = defineProps({
  open: { type: Boolean, required: true },
})
const emit = defineEmits(['close'])

const LEVELS = [
  { key: 'beginner',        label: 'Beginner' },
  { key: 'finance_student', label: 'Student' },
  { key: 'professional',    label: 'Professional' },
]

const level    = ref('finance_student')
const messages = ref([])
const input    = ref('')
const loading  = ref(false)
const error    = ref(null)
const listEl   = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

watch(() => messages.value.length, scrollToBottom)

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  error.value = null
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  try {
    const data = await sendChat(messages.value, level.value)
    messages.value.push({ role: 'model', content: data.reply })
  } catch (e) {
    error.value = e.message
    messages.value.pop()
    input.value = text
  } finally {
    loading.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function clear() {
  messages.value = []
  error.value = null
}
</script>

<template>
  <!-- Backdrop (mobile) -->
  <div
    v-if="open"
    class="fixed inset-0 bg-black/40 z-40 lg:hidden"
    @click="emit('close')"
  />

  <!-- Panel -->
  <div
    :class="[
      'fixed inset-y-0 right-0 z-50 w-96 max-w-full flex flex-col',
      'bg-slate-900 border-l border-slate-800 shadow-2xl',
      'transition-transform duration-300',
      open ? 'translate-x-0' : 'translate-x-full',
    ]"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
      <span class="text-sm font-semibold text-slate-200">Options Assistant</span>
      <div class="flex items-center gap-1.5">
        <button
          v-for="lvl in LEVELS"
          :key="lvl.key"
          @click="level = lvl.key"
          :class="[
            'text-[10px] font-semibold rounded-full px-2 py-0.5 border transition-colors',
            level === lvl.key
              ? 'bg-violet-900/40 border-violet-600 text-violet-300'
              : 'border-slate-700 text-slate-500 hover:text-slate-300'
          ]"
        >{{ lvl.label }}</button>
        <button
          @click="emit('close')"
          class="ml-2 text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
          aria-label="Close"
        >×</button>
      </div>
    </div>

    <!-- Message list -->
    <div ref="listEl" class="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
      <div v-if="messages.length === 0" class="text-center text-xs text-slate-400 mt-8">
        Ask anything about options, Greeks, or pricing models.
      </div>
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="[
          'max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed',
          msg.role === 'user'
            ? 'self-end bg-violet-900/50 border border-violet-800/60 text-violet-100 whitespace-pre-wrap'
            : 'self-start bg-slate-800 border border-slate-700 text-slate-200 chat-prose'
        ]"
      >
        <template v-if="msg.role === 'user'">{{ msg.content }}</template>
        <span v-else v-html="marked.parse(msg.content)" />
      </div>

      <!-- Typing indicator -->
      <div v-if="loading" class="self-start flex items-center gap-1 px-3 py-2">
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:0ms"/>
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:150ms"/>
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style="animation-delay:300ms"/>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="px-4 pb-2 text-xs text-rose-400 shrink-0">{{ error }}</div>

    <!-- Footer: clear + input -->
    <div class="px-4 py-3 border-t border-slate-800 flex flex-col gap-2 shrink-0">
      <div class="flex justify-end">
        <button
          @click="clear"
          class="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
        >Clear conversation</button>
      </div>
      <div class="flex gap-2 items-end">
        <textarea
          v-model="input"
          @keydown="onKeydown"
          rows="1"
          placeholder="Ask about options…"
          class="flex-1 resize-none bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-600 transition-colors"
          style="max-height: 6rem; overflow-y: auto;"
          :disabled="loading"
        />
        <button
          @click="send"
          :disabled="loading || !input.trim()"
          class="px-3 py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
        >Send</button>
      </div>
      <p class="text-[9px] text-slate-500 text-center">Enter to send · Shift+Enter for new line</p>
      <p class="text-[9px] text-rose-400/80 text-center font-bold tracking-wide">Educational tool — not investment advice.</p>
    </div>
  </div>
</template>

<style scoped>
.chat-prose :deep(h1),
.chat-prose :deep(h2),
.chat-prose :deep(h3) {
  color: #c4b5fd;
  font-weight: 700;
  margin-top: 0.75rem;
  margin-bottom: 0.25rem;
}
.chat-prose :deep(h1) { font-size: 0.85rem; }
.chat-prose :deep(h2) { font-size: 0.8rem; }
.chat-prose :deep(h3) { font-size: 0.75rem; }
.chat-prose :deep(p) {
  color: #cbd5e1;
  font-size: 0.75rem;
  line-height: 1.6;
  margin-bottom: 0.4rem;
}
.chat-prose :deep(ul),
.chat-prose :deep(ol) {
  color: #cbd5e1;
  font-size: 0.75rem;
  padding-left: 1.1rem;
  margin-bottom: 0.4rem;
  list-style: disc;
}
.chat-prose :deep(ol) { list-style: decimal; }
.chat-prose :deep(li) { margin-bottom: 0.15rem; line-height: 1.5; }
.chat-prose :deep(strong) { color: #e2e8f0; font-weight: 600; }
.chat-prose :deep(em) { color: #a5b4fc; font-style: italic; }
.chat-prose :deep(code) {
  background: #0f172a;
  color: #7dd3fc;
  padding: 0.1rem 0.25rem;
  border-radius: 0.2rem;
  font-size: 0.7rem;
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}
.chat-prose :deep(hr) {
  border-color: #334155;
  margin: 0.5rem 0;
}
</style>
