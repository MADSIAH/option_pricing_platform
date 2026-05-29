import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function renderLatex(text) {
  // Display math $$...$$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) =>
    katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })
  )
  // Inline math $...$ — only when content contains a backslash (LaTeX command),
  // so bare currency like $3.86 or $1 is left alone
  text = text.replace(/\$([^$\n]+?)\$/g, (match, math) => {
    if (!math.includes('\\')) return match
    return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })
  })
  return text
}

export function parseMarkdown(text) {
  return marked.parse(renderLatex(text))
}
