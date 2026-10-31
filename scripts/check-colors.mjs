#!/usr/bin/env node
/**
 * F12 颜色门禁（R2-04 / R2-05 / R3-02 返工版）
 *
 * 规则：
 *  1. 业务代码里不许出现裸 hex / rgb() / rgba() / hsl() / hsla()（大小写都算）；
 *  2. 允许 `rgb(var(--rgb-*) / a)` 这种「令牌 + 透明度」写法；
 *  3. 自定义属性的**裸色定义**只允许出现在批准的主题出口（THEME_EXPORT）；
 *     普通组件可以定义「引用全局令牌的别名」（`--x: var(--color-ink)`），但不能自造色值；
 *  4. 注释按**语言词法**剔除，只跳过注释本身——注释后的同行业务代码照样要查。
 *     - JS/Vue script：字符串、模板字符串、正则字面量、行/块注释；
 *     - CSS/Vue style：字符串、`url(...)`、块注释（CSS 没有 `//` 行注释）；
 *     - Vue template/HTML：`<!-- ... -->`。
 *     （R3-02：旧版共用一个状态机，`/[/*]/` 和 `url(https://…//…)` 会被误当注释。）
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

const ROOT = process.cwd()
const SRC = join(ROOT, 'frontend', 'src')

/** 上游原件（Vue Bits 三组件）：shader 颜色是取件原样，改不得 */
const UPSTREAM = new Set([
  'frontend/src/components/bits/Grainient.vue',
  'frontend/src/components/bits/LiquidChrome.vue',
  'frontend/src/components/bits/Silk.vue',
])

/**
 * 唯一允许「裸色定义」的主题出口：src/styles/ 下的三个令牌层文件。
 * 组件（Vue/JS）与其它 CSS 一律不许自造色值——这是 R2-05 的口径。
 */
const THEME_EXPORT = new Set([
  'frontend/src/styles/main.css',
  'frontend/src/styles/glass-card.css',
  'frontend/src/styles/glass-tokens.css',
])

/** JS→CSS 的唯一桥：值全部来自 readVar()，fallback 与 main.css 同值 */
const JS_BRIDGE = new Set(['frontend/src/utils/theme.js'])

const COLOR_RE = /#(?:[0-9a-fA-F]{3,8})\b|\b(?:rgb|rgba)\s*\((?!\s*var\()|\b(?:hsl|hsla)\s*\(/gi
const TOKEN_DECL_RE = /--[\w-]+\s*:\s*[^;}]+/g

/** 关键字之后出现的 `/` 是正则字面量起点，而不是除号 */
const REGEX_PREFIX_KEYWORDS = new Set([
  'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
  'throw', 'case', 'do', 'else', 'yield', 'await',
])

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) walk(full, out)
    else if (/\.(vue|js|css)$/.test(name)) out.push(full)
  }
  return out
}

function blankChar(ch) {
  return ch === '\n' ? '\n' : ' '
}

/** JS / Vue script：剔除行注释与块注释；字符串、模板字符串、正则原样保留。 */
function maskJsComments(text) {
  let out = ''
  let i = 0
  let canStartRegex = true
  const n = text.length
  while (i < n) {
    const c = text[i]
    const next = text[i + 1]

    if (c === '/' && next === '/') {
      out += '  '
      i += 2
      while (i < n && text[i] !== '\n') {
        out += ' '
        i += 1
      }
      continue
    }

    if (c === '/' && next === '*') {
      out += '  '
      i += 2
      while (i < n && !(text[i] === '*' && text[i + 1] === '/')) {
        out += blankChar(text[i])
        i += 1
      }
      if (i < n) {
        out += '  '
        i += 2
      }
      continue
    }

    if (c === '"' || c === "'") {
      const quote = c
      out += c
      i += 1
      while (i < n) {
        const ch = text[i]
        out += ch
        if (ch === '\\') {
          out += text[i + 1] ?? ''
          i += 2
          continue
        }
        i += 1
        if (ch === quote) break
      }
      canStartRegex = false
      continue
    }

    if (c === '`') {
      out += c
      i += 1
      while (i < n) {
        const ch = text[i]
        out += ch
        if (ch === '\\') {
          out += text[i + 1] ?? ''
          i += 2
          continue
        }
        i += 1
        if (ch === '`') break
      }
      canStartRegex = false
      continue
    }

    if (c === '/' && canStartRegex) {
      // 正则字面量：字符类里的 `/` 不是结束符
      out += c
      i += 1
      let inClass = false
      while (i < n) {
        const ch = text[i]
        out += ch
        if (ch === '\\') {
          out += text[i + 1] ?? ''
          i += 2
          continue
        }
        if (ch === '[') inClass = true
        else if (ch === ']') inClass = false
        else if (ch === '/' && !inClass) {
          i += 1
          break
        } else if (ch === '\n') {
          break
        }
        i += 1
      }
      while (i < n && /[a-z]/i.test(text[i])) {
        out += text[i]
        i += 1
      }
      canStartRegex = false
      continue
    }

    if (c === '/') {
      out += c
      i += 1
      canStartRegex = true
      continue
    }

    if (/[A-Za-z_$]/.test(c)) {
      const start = i
      i += 1
      while (i < n && /[A-Za-z0-9_$]/.test(text[i])) i += 1
      const word = text.slice(start, i)
      out += word
      canStartRegex = REGEX_PREFIX_KEYWORDS.has(word)
      continue
    }

    if (/[0-9]/.test(c)) {
      const start = i
      i += 1
      while (i < n && /[0-9A-Za-z_.]/.test(text[i])) i += 1
      out += text.slice(start, i)
      canStartRegex = false
      continue
    }

    out += c
    i += 1
    if (c === ')' || c === ']' || c === '}') canStartRegex = false
    else canStartRegex = true
  }
  return out
}

/** CSS / Vue style：剔除块注释；字符串与 `url(...)` 原样保留（URL 里没有注释语义）。 */
function maskCssComments(text) {
  let out = ''
  let i = 0
  const n = text.length
  while (i < n) {
    const c = text[i]
    const next = text[i + 1]

    if (c === '/' && next === '*') {
      out += '  '
      i += 2
      while (i < n && !(text[i] === '*' && text[i + 1] === '/')) {
        out += blankChar(text[i])
        i += 1
      }
      if (i < n) {
        out += '  '
        i += 2
      }
      continue
    }

    if (c === '"' || c === "'") {
      const quote = c
      out += c
      i += 1
      while (i < n) {
        const ch = text[i]
        out += ch
        if (ch === '\\') {
          out += text[i + 1] ?? ''
          i += 2
          continue
        }
        i += 1
        if (ch === quote) break
      }
      continue
    }

    if (/[A-Za-z_-]/.test(c)) {
      const start = i
      i += 1
      while (i < n && /[A-Za-z0-9_-]/.test(text[i])) i += 1
      const word = text.slice(start, i)
      let lookahead = i
      while (lookahead < n && /\s/.test(text[lookahead])) lookahead += 1
      if (word.toLowerCase() === 'url' && text[lookahead] === '(') {
        out += text.slice(start, lookahead + 1)
        i = lookahead + 1
        let depth = 1
        while (i < n && depth > 0) {
          const ch = text[i]
          out += ch
          if (ch === '\\') {
            out += text[i + 1] ?? ''
            i += 2
            continue
          }
          if (ch === '"' || ch === "'") {
            const quote = ch
            i += 1
            while (i < n) {
              const inner = text[i]
              out += inner
              if (inner === '\\') {
                out += text[i + 1] ?? ''
                i += 2
                continue
              }
              i += 1
              if (inner === quote) break
            }
            continue
          }
          if (ch === '(') depth += 1
          else if (ch === ')') depth -= 1
          i += 1
        }
        continue
      }
      out += word
      continue
    }

    out += c
    i += 1
  }
  return out
}

/** HTML / Vue template：只剔除 `<!-- ... -->`，其余内容（含 style 属性）照查。 */
function maskHtmlComments(text) {
  let out = ''
  let i = 0
  const n = text.length
  while (i < n) {
    if (text.startsWith('<!--', i)) {
      out += '    '
      i += 4
      while (i < n && !text.startsWith('-->', i)) {
        out += blankChar(text[i])
        i += 1
      }
      if (i < n) {
        out += '   '
        i += 3
      }
      continue
    }
    out += text[i]
    i += 1
  }
  return out
}

/** Vue SFC：HTML 段走 HTML 注释规则，<script>/<style> 块分别走 JS/CSS 规则。 */
function maskVue(text) {
  const blockRe = /<(script|style)\b[^>]*>([\s\S]*?)<\/\1\s*>/gi
  let out = ''
  let cursor = 0
  let match
  while ((match = blockRe.exec(text)) !== null) {
    out += maskHtmlComments(text.slice(cursor, match.index))
    const full = match[0]
    const bodyStart = match.index + full.indexOf('>') + 1
    const bodyEnd = bodyStart + match[2].length
    out += text.slice(match.index, bodyStart)
    const body = text.slice(bodyStart, bodyEnd)
    out += match[1].toLowerCase() === 'script'
      ? maskJsComments(body)
      : maskCssComments(body)
    out += text.slice(bodyEnd, match.index + full.length)
    cursor = match.index + full.length
  }
  out += maskHtmlComments(text.slice(cursor))
  return out
}

function stripComments(text, ext) {
  if (ext === '.js') return maskJsComments(text)
  if (ext === '.css') return maskCssComments(text)
  return maskVue(text)
}

/** 主题出口文件里，把 `--x: <value>;` 整段涂成空格（保留换行），后续只查业务声明 */
function maskTokenDeclarations(text) {
  return text.replace(/--[\w-]+\s*:[^;]*;/g, (m) => m.replace(/[^\n]/g, ' '))
}

const violations = []
const files = walk(SRC)

for (const file of files) {
  const rel = relative(ROOT, file).split(sep).join('/')
  if (UPSTREAM.has(rel) || JS_BRIDGE.has(rel)) continue

  const raw = readFileSync(file, 'utf8')
  const ext = file.slice(file.lastIndexOf('.'))
  const withoutComments = stripComments(raw, ext)
  const isTheme = THEME_EXPORT.has(rel)
  const cleaned = isTheme ? maskTokenDeclarations(withoutComments) : withoutComments

  // R2-05：非主题出口文件里的「裸色令牌定义」本身就是违规
  if (!isTheme) {
    TOKEN_DECL_RE.lastIndex = 0
    let m
    while ((m = TOKEN_DECL_RE.exec(cleaned)) !== null) {
      const decl = m[0]
      if (/(?:#|rgb|hsl)/i.test(decl) && !decl.includes('var(--')) {
        const line = cleaned.slice(0, m.index).split('\n').length
        violations.push({ rel, line, kind: 'token-literal', text: decl.trim().slice(0, 80) })
      }
    }
  }

  cleaned.split('\n').forEach((line, idx) => {
    COLOR_RE.lastIndex = 0
    if (COLOR_RE.test(line)) {
      violations.push({ rel, line: idx + 1, kind: 'literal', text: line.trim().slice(0, 120) })
    }
  })
}

if (violations.length === 0) {
  console.log(`✓ check-colors: ${files.length} 个文件无裸 hex / rgb / hsl，颜色只从令牌出口取`)
  process.exit(0)
}

console.error(`✗ check-colors: ${violations.length} 处裸色值（扫描 ${files.length} 个文件）`)
for (const v of violations) console.error(`  ${v.rel}:${v.line} [${v.kind}] ${v.text}`)
process.exit(1)
