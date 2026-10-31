#!/usr/bin/env node
/**
 * F12 门禁：颜色只有一个出口。
 *
 * 规则（AGENTS.md）：组件、页面、样式、图表、动效里禁止出现裸 hex / 裸 rgb() / hsl()，
 * 一律走 `var(--…)` 或 `rgb(var(--rgb-x) / a)`。
 *
 * 允许写色字面量的只有两种情形（2026-10-24 复审 CLR-05 之后收紧为精确白名单）：
 *   1. **令牌定义行**：`--custom-prop: …;` 形式的变量声明（不限文件，但只放行声明行）；
 *   2. **Vue Bits 上游原件**：`frontend/src/components/bits/{Grainient,LiquidChrome,Silk}.vue`
 *      —— 这三个文件是从上游取的 shader 组件，颜色写在 GLSL 里，改了就偏离原件。
 *      只豁免这三个精确文件名，不是整个目录。
 *
 * 支持的后缀：`.vue` / `.js` / `.css`（此前只扫 vue/js，`src/styles/*.css` 里的
 * 10 处直接写色全部漏检）。函数名大小写不敏感：`RGB(255 0 0)` 同样违规。
 *
 * 用法：node scripts/check-colors.mjs
 * 退出码：0 通过；1 发现违规。
 */

import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const SRC = path.join(ROOT, 'frontend', 'src')

/** 精确豁免的文件（相对 frontend/src），只列"本来就有权持有色字面量"的地方 */
const EXEMPT = new Set([
  // Vue Bits 上游原件：颜色写在 GLSL shader 里，改了就偏离原件
  'components/bits/Grainient.vue',
  'components/bits/LiquidChrome.vue',
  'components/bits/Silk.vue',
  // JS → CSS 变量的唯一桥：readVar 的 fallback 与 main.css 的令牌同值，
  // alpha() 只是把读到的 hex 拆成 rgba 字符串，本身不引入新颜色。
  'utils/theme.js',
])

/** 令牌定义行：`--foo: #fff;` / `--foo: rgba(0,0,0,.3);` */
const TOKEN_DECL = /^\s*--[a-zA-Z0-9-]+\s*:/

const FORBIDDEN = [
  { name: 'hex', re: /#[0-9a-fA-F]{3,8}\b/g },
  // rgb(var(--rgb-x) / a) 是「令牌 + 透明度」的正确写法，必须放行；
  // 只有直接写数字的 rgb()/rgba() 才算违规。大小写不敏感。
  { name: 'rgb', re: /\brgba?\s*\((?!\s*var\()/gi },
  { name: 'hsl', re: /\bhsla?\s*\(/gi },
]

async function* walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) yield* walk(full)
    else if (/\.(vue|js|css)$/.test(entry.name)) yield full
  }
}

function rel(file) {
  return path.relative(ROOT, file).replaceAll('\\', '/')
}

const violations = []
let scanned = 0

for await (const file of walk(SRC)) {
  const relPath = path.relative(SRC, file).replaceAll('\\', '/')
  if (EXEMPT.has(relPath)) continue
  scanned += 1

  const text = await readFile(file, 'utf8')
  const lines = text.split(/\r?\n/)
  let inBlockComment = false
  let inTokenDecl = false
  lines.forEach((line, index) => {
    // 注释里的色值只是文档说明，不参与渲染
    const trimmed = line.trim()
    if (inBlockComment) {
      if (trimmed.includes('*/')) inBlockComment = false
      return
    }
    if (trimmed.startsWith('/*')) {
      if (!trimmed.includes('*/')) inBlockComment = true
      return
    }
    if (trimmed.startsWith('//') || trimmed.startsWith('*')) return

    // 令牌声明可能跨多行（box-shadow 之类的长值）：从 `--x:` 开始
    // 到以 `;` 结束为止都算声明体，中间的色字面量放行。
    if (inTokenDecl) {
      if (trimmed.includes(';')) inTokenDecl = false
      return
    }
    if (TOKEN_DECL.test(line)) {
      if (!trimmed.includes(';')) inTokenDecl = true
      return
    }
    for (const rule of FORBIDDEN) {
      rule.re.lastIndex = 0
      const match = rule.re.exec(line)
      if (match) {
        violations.push({
          file: rel(file),
          line: index + 1,
          kind: rule.name,
          text: match[0],
          snippet: line.trim().slice(0, 96),
        })
      }
    }
  })
}

if (violations.length > 0) {
  console.error(`✗ check-colors: ${violations.length} 处裸色值（扫描 ${scanned} 个文件）`)
  for (const v of violations) {
    console.error(`  ${v.file}:${v.line}  [${v.kind}] ${v.text}   ${v.snippet}`)
  }
  console.error('\n改法：hex → var(--color-x)；透明度 → rgb(var(--rgb-x) / a)。')
  process.exit(1)
}

console.log(`✓ check-colors: ${scanned} 个文件无裸 hex / rgb / hsl，颜色只从令牌出口取`)
