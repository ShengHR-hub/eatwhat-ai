#!/usr/bin/env node
/**
 * F12 颜色门禁（R2-04 / R2-05 返工版）
 *
 * 规则：
 *  1. 业务代码里不许出现裸 hex / rgb() / rgba() / hsl() / hsla()（大小写都算）；
 *  2. 允许 `rgb(var(--rgb-*) / a)` 这种「令牌 + 透明度」写法；
 *  3. 自定义属性的**裸色定义**只允许出现在批准的主题出口（THEME_EXPORT）；
 *     普通组件可以定义「引用全局令牌的别名」（`--x: var(--color-ink)`），但不能自造色值；
 *  4. 注释按词法范围剔除，只跳过注释本身——同一行里注释之后的业务代码照样要查
 *     （R2-04：旧版 `*`/`//`/令牌行整行返回，导致三例漏检）。
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

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) walk(full, out)
    else if (/\.(vue|js|css)$/.test(name)) out.push(full)
  }
  return out
}

/** 把注释替换成等长空格，保留行列位置；字符串里的 // 通过「前一个非空白字符是 :」排除 */
function stripComments(text) {
  let out = ''
  let i = 0
  let inBlock = false
  let inLine = false
  let quote = null
  while (i < text.length) {
    const c = text[i]
    const n = text[i + 1]
    if (inBlock) {
      if (c === '*' && n === '/') { out += '  '; i += 2; inBlock = false; continue }
      out += c === '\n' ? '\n' : ' '
      i += 1
      continue
    }
    if (inLine) {
      if (c === '\n') { out += '\n'; inLine = false; i += 1; continue }
      out += ' '
      i += 1
      continue
    }
    if (quote) {
      out += c
      if (c === '\\') { out += text[i + 1] ?? ''; i += 2; continue }
      if (c === quote) quote = null
      i += 1
      continue
    }
    if (c === '"' || c === "'" || c === '`') { quote = c; out += c; i += 1; continue }
    if (c === '/' && n === '*') { out += '  '; i += 2; inBlock = true; continue }
    if (c === '/' && n === '/') {
      const prev = text.slice(Math.max(0, i - 1), i)
      if (prev !== ':') { out += '  '; i += 2; inLine = true; continue }
    }
    out += c
    i += 1
  }
  return out
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
  const withoutComments = stripComments(raw)
  const isTheme = THEME_EXPORT.has(rel)
  const cleaned = isTheme ? maskTokenDeclarations(withoutComments) : withoutComments

  // R2-05：非主题出口文件里的「裸色令牌定义」本身就是违规
  if (!isTheme) {
    TOKEN_DECL_RE.lastIndex = 0
    let m
    while ((m = TOKEN_DECL_RE.exec(cleaned)) !== null) {
      const decl = m[0]
      if (/\b(?:#|rgb|hsl)/i.test(decl) && !decl.includes('var(--')) {
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
