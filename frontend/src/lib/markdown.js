import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function renderLatex(text) {
  // Display math \[ ... \]
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, math) =>
    katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })
  )
  // Inline math \( ... \)
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, math) =>
    katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })
  )
  // Note: we intentionally do NOT treat $...$ as math. The AI is instructed to
  // use \(...\) / \[...\] delimiters, so bare $ always means currency and is
  // left untouched.
  return text
}

export function parseMarkdown(text) {
  return marked.parse(renderLatex(text))
}
