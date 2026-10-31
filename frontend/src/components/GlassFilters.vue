<script setup>
/**
 * 液态玻璃卡的 SVG 折射滤镜（G 方案 ① 折射层的位移部分）。
 *
 * 只定义一次、全局共用；`glass-card.css` 里用 `filter: url(#glass-refract)` 引用。
 * 位移强度（scale）与噪声频率属于 §4.1 基准参数，定稿后改这里的两个数值即可。
 *
 * 注意：Chromium 的 backdrop-filter 不接受 url()，所以位移作用在卡片的边缘折射环上，
 * 真实背景采样由 backdrop-filter: blur(4px) saturate(170%) 完成。见文件头说明。
 */
</script>

<template>
  <svg class="glass-filters" aria-hidden="true" focusable="false">
    <defs>
      <filter
        id="glass-refract"
        x="-25%"
        y="-25%"
        width="150%"
        height="150%"
        color-interpolation-filters="sRGB"
      >
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.012 0.02"
          numOctaves="2"
          seed="7"
          result="noise"
        />
        <feGaussianBlur in="noise" stdDeviation="1.6" result="soft" />
        <feDisplacementMap
          in="SourceGraphic"
          in2="soft"
          scale="12"
          xChannelSelector="R"
          yChannelSelector="G"
        />
      </filter>
    </defs>
  </svg>
</template>

<style scoped>
.glass-filters {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
  pointer-events: none;
}
</style>
