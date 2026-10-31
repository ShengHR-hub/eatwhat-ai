import html2canvas from 'html2canvas'
import { alpha, tokens } from '../../utils/theme'

export function downloadDataUrl(dataUrl, filename) {
  if (!dataUrl || !dataUrl.startsWith('data:image/png')) {
    throw new Error('没有生成有效的 PNG 图像')
  }
  const anchor = document.createElement('a')
  anchor.href = dataUrl
  anchor.download = filename.endsWith('.png') ? filename : `${filename}.png`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

function inlineComputedStylesWithoutOklch(element, palette) {
  return (clonedDocument) => {
    const sourceNodes = [element, ...element.querySelectorAll('*')]
    const clonedRoot = clonedDocument.querySelector('[data-g4-export-root]')
    if (!clonedRoot) throw new Error('PNG 克隆根节点不存在')
    const clonedNodes = [clonedRoot, ...clonedRoot.querySelectorAll('*')]
    sourceNodes.forEach((source, index) => {
      const clone = clonedNodes[index]
      if (!clone?.style) return
      const computed = getComputedStyle(source)
      for (const property of computed) {
        let value = computed.getPropertyValue(property)
        if (value.includes('oklch')) {
          value = property.includes('color') ? palette.white : palette.ink
        }
        clone.style.setProperty(property, value, computed.getPropertyPriority(property))
      }
    })
    clonedDocument.querySelectorAll('style, link[rel="stylesheet"]').forEach((node) => node.remove())
  }
}

export async function exportElementPng(element, { title, note, filename }) {
  if (!element) throw new Error('导出区域不存在')
  const palette = tokens()
  element.setAttribute('data-g4-export-root', 'true')
  let captured
  try {
    captured = await html2canvas(element, {
      backgroundColor: palette.ink,
      scale: 2,
      useCORS: true,
      logging: false,
      onclone: inlineComputedStylesWithoutOklch(element, palette),
    })
  } finally {
    element.removeAttribute('data-g4-export-root')
  }
  const canvas = document.createElement('canvas')
  canvas.width = captured.width
  canvas.height = captured.height + 150
  const context = canvas.getContext('2d')
  context.fillStyle = palette.ink
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.fillStyle = palette.white
  context.font = '600 30px system-ui, sans-serif'
  context.textBaseline = 'top'
  context.fillText(title, 28, 24, canvas.width - 56)
  context.fillStyle = alpha(palette.silver, 0.82)
  context.font = '20px system-ui, sans-serif'
  context.fillText(`口径：${note}`, 28, 70, canvas.width - 56)
  context.drawImage(captured, 0, 130)
  downloadDataUrl(canvas.toDataURL('image/png'), filename)
}
