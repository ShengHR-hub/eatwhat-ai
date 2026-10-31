<script setup>
/**
 * 单色 Lottie 图标（lottie-web）—— 天气 / 空状态 / 插画统一走这里。
 *
 * 素材来源：@meteocons/lottie 的 monochrome 风格（MIT，Bas Milius），
 * 现成 JSON 已落 `src/assets/lottie/`，来源与授权见 `docs/LOTTIE_SOURCES.md`。
 * 之所以选 meteocons 而不是 LottieFiles：LottieFiles 的下载页要登录且被 Cloudflare 拦，
 * 无法在本机稳定取件；meteocons 是 MIT、纯离线、自带 monochrome 单色风格，与单色体系一致。
 *
 * 颜色出口：素材本身是纯黑描边（var(--color-black)），深色玻璃上不可见。
 * 这里不改 JSON，用 `filter: invert(1)` 把黑翻成白，透明度统一交给 CSS 变量侧控制，
 * 组件内不出现任何颜色字面量。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** 文件名（不含扩展名），对应 src/assets/lottie/<name>.json */
  name: { type: String, required: true },
  /** 渲染尺寸（px），正方形 */
  size: { type: Number, default: 24 },
  /** 循环播放；静态插画传 false 只播一次 */
  loop: { type: Boolean, default: true },
})

const files = import.meta.glob('../assets/lottie/*.json', { eager: true, import: 'default' })

const host = ref(null)
const missing = ref(true)

let anim = null
let lib = null

const data = computed(() => files[`../assets/lottie/${props.name}.json`] ?? null)

function destroy() {
  if (anim) {
    anim.destroy()
    anim = null
  }
}

async function mount() {
  destroy()
  const payload = data.value
  if (!host.value || !payload) {
    missing.value = true
    return
  }
  try {
    // lottie_light：只保留渲染器，去掉表达式/插值那一套，包体小一半（我们的素材不需要表达式）
    lib = lib ?? (await import('lottie-web/build/player/lottie_light')).default
    missing.value = false
    anim = lib.loadAnimation({
      container: host.value,
      renderer: 'svg',
      loop: props.loop,
      autoplay: true,
      animationData: payload,
    })
  } catch (err) {
    missing.value = true
    console.warn(`[LottieIcon] ${props.name} 播放失败`, err)
  }
}

onMounted(mount)
onBeforeUnmount(destroy)
watch(() => props.name, mount)
</script>

<template>
  <span
    class="lottie-icon"
    :style="{ '--lottie-size': `${size}px` }"
    :data-missing="missing"
    aria-hidden="true"
  >
    <span ref="host" class="lottie-icon__host" />
    <!-- 素材缺失时的兜底：一个中性描边方块，不假装有动画 -->
    <svg v-if="missing" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="M8.5 12h7" stroke-linecap="round" />
    </svg>
  </span>
</template>

<style scoped>
.lottie-icon {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  width: var(--lottie-size);
  height: var(--lottie-size);
  align-items: center;
  justify-content: center;
}

.lottie-icon__host {
  width: 100%;
  height: 100%;
  /* 素材是纯黑线稿，深色底上反白；不透明度由外层控制 */
  filter: invert(1);
  opacity: 0.82;
}

.lottie-icon[data-missing='true'] .lottie-icon__host {
  display: none;
}

.lottie-icon svg {
  width: 100%;
  height: 100%;
  color: var(--color-steel);
}
</style>
