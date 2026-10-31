<script setup>
/**
 * SwipeCardDeck.vue —— 可划卡组（BATCH2_PLAN v1.1）
 *
 * 形态：所有候选入组层叠，顶卡完整、后两张错位缩放露边；
 *      顶卡是一级玻璃（G 方案、开折射），露边卡是磨砂降级。
 * 手势：GSAP + Draggable（规范锁定的唯一划卡实现，禁止手写 touch / Swiper）。
 *   左划 >60px = 换一个（飞出 + 下一张补位，左上角渐显「换一个」印章）
 *   右划 >60px = 就吃这个（右上角渐显印章，松手进确认态，不直接落库）
 *   未过 60px = 弹簧回位；拖动 <10px = 点击（打开雷达，不误触）
 *
 * 纪律：gsap.context() + onUnmounted revert；registerPlugin 只在模块顶层一次。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import { Draggable } from 'gsap/Draggable'

import DishCard from './DishCard.vue'

gsap.registerPlugin(Draggable)

const THRESHOLD = 60 // 判定阈值（px）
const TAP_SLOP = 10 // 小于它算点击，不算拖动

const props = defineProps({
  cards: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  // single：首页单人卡组（左换一个 / 右确认）；room：房间四向投票
  variant: { type: String, default: 'single' },
})

const emit = defineEmits(['pass', 'confirm', 'tap', 'vote'])

const stageRef = ref(null)
const topRef = ref(null)
const stampPassRef = ref(null)
const stampLikeRef = ref(null)
const stampSuperRef = ref(null)
const stampVetoRef = ref(null)

const confirming = ref(null) // 右划后持卡确认
const busying = ref(false) // 飞出动画中，禁止再次拖动

const top = computed(() => props.cards[0] ?? null)
const ghostLayers = computed(() =>
  props.cards
    .slice(1, 3)
    .map((dish, i) => ({ dish, depth: i + 1 }))
    .reverse(),
)

let ctx = null
let drag = null
let moved = 0
/* 真机（iOS Safari / 部分微信内核）在 Draggable 接管 touch 之后不保证还派发 click，
   所以点击判定必须同时挂在 Draggable 的 onRelease 上，用时间戳去重。 */
let lastTapAt = 0

/** 印章：位置/倾斜都交给 gsap，避免内联 transform 覆盖 CSS 里的 rotate */
function stamp(el, value, rotation = 0) {
  if (!el) return
  gsap.set(el, { opacity: value, scale: 0.9 + 0.1 * value, rotation, xPercent: -50 })
}

function resetStamps() {
  stamp(stampPassRef.value, 0, -11)
  stamp(stampLikeRef.value, 0, 9)
  stamp(stampSuperRef.value, 0, 0)
  stamp(stampVetoRef.value, 0, 0)
}

/** 房间模式：按主导轴显示对应方向的印章（左换一个 / 右想吃 / 上超想吃 / 下不吃）。 */
function dragStamp(dx, dy) {
  const horizontal = Math.abs(dx) >= Math.abs(dy)
  const t = Math.min(1, Math.abs(horizontal ? dx : dy) / THRESHOLD)
  if (horizontal) {
    if (dx < 0) {
      stamp(stampPassRef.value, t, -11)
      stamp(stampLikeRef.value, 0, 9)
    } else {
      stamp(stampLikeRef.value, t, 9)
      stamp(stampPassRef.value, 0, -11)
    }
    stamp(stampSuperRef.value, 0, 0)
    stamp(stampVetoRef.value, 0, 0)
    return
  }
  if (dy < 0) {
    stamp(stampSuperRef.value, t, 0)
    stamp(stampVetoRef.value, 0, 0)
  } else {
    stamp(stampVetoRef.value, t, 0)
    stamp(stampSuperRef.value, 0, 0)
  }
  stamp(stampPassRef.value, 0, -11)
  stamp(stampLikeRef.value, 0, 9)
}

function placeCard(immediate = true) {
  const el = topRef.value
  if (!el) return
  const vars = { x: 0, y: 0, rotation: 0, opacity: 1 }
  if (immediate) gsap.set(el, vars)
  else gsap.to(el, { ...vars, duration: 0.42, ease: 'back.out(1.5)' })
  resetStamps()
}

function lockDrag() {
  busying.value = true
  drag?.disable()
}

function unlockDrag() {
  busying.value = false
  drag?.enable()
}

/** 左划：直接飞出并交牌 */
function flyAway() {
  const dish = top.value
  const el = topRef.value
  if (!dish || !el || busying.value) return
  lockDrag()
  stamp(stampPassRef.value, 1, -11)
  gsap.to(el, {
    x: -760,
    y: -24,
    rotation: -18,
    opacity: 0,
    duration: 0.44,
    ease: 'power2.in',
    onComplete: () => {
      emit('pass', dish)
      unlockDrag()
    },
  })
}

/** 右划：先停到"待确认"位，等用户点头 */
function holdForConfirm() {
  const dish = top.value
  const el = topRef.value
  if (!dish || !el || busying.value) return
  lockDrag()
  stamp(stampLikeRef.value, 1, 9)
  gsap.to(el, {
    /* 停位要克制：x 太大 + 旋转会让整卡越出右边界（390 视口下页宽变 406） */
    x: 10,
    y: -8,
    rotation: 1.5,
    duration: 0.34,
    ease: 'power2.out',
    onComplete: () => {
      confirming.value = dish
    },
  })
}

function cancelConfirm() {
  confirming.value = null
  unlockDrag()
  placeCard(false)
}

function acceptConfirm() {
  const dish = confirming.value
  if (!dish) return
  confirming.value = null
  gsap.to(topRef.value, {
    x: 720,
    y: -18,
    rotation: 16,
    opacity: 0,
    duration: 0.42,
    ease: 'power2.in',
    onComplete: () => {
      emit('confirm', dish)
      unlockDrag()
    },
  })
}

function emitTap() {
  if (moved > TAP_SLOP || confirming.value || busying.value) return
  if (!top.value) return
  lastTapAt = Date.now()
  emit('tap', top.value)
}

function onCardClick() {
  /* onRelease 已经处理过这次点击，别重复打开弹层 */
  if (Date.now() - lastTapAt < 600) return
  emitTap()
}

/** 房间模式四向飞出：方向与票型一一对应，票只在飞出完成后上报。 */
const ROOM_FLIGHT = {
  PASS: { x: -760, y: -18, rotation: -18 },
  LIKE: { x: 720, y: -18, rotation: 16 },
  SUPER_LIKE: { x: 0, y: -680, rotation: 0 },
  VETO: { x: 0, y: 680, rotation: 0 },
}

function castVote(voteType) {
  const dish = top.value
  const el = topRef.value
  const flight = ROOM_FLIGHT[voteType]
  if (!dish || !el || !flight || busying.value || props.disabled) return false
  lockDrag()
  const stampMap = {
    PASS: stampPassRef,
    LIKE: stampLikeRef,
    SUPER_LIKE: stampSuperRef,
    VETO: stampVetoRef,
  }
  stamp(stampMap[voteType]?.value, 1, voteType === 'PASS' ? -11 : voteType === 'LIKE' ? 9 : 0)
  gsap.to(el, {
    ...flight,
    opacity: 0,
    duration: 0.4,
    ease: 'power2.in',
    onComplete: () => {
      emit('vote', { dish, voteType })
      unlockDrag()
    },
  })
  return true
}

/**
 * 暴露给按钮 / 验收脚本：
 *   单人选 pass / like；房间四票型走 castVote。
 * `swipeTo` 用位移驱动同一套判定，便于真实拖拽测试复用。
 */
defineExpose({
  swipeLeft: flyAway,
  swipeRight: holdForConfirm,
  castVote,
  reset: () => {
    confirming.value = null
    placeCard(true)
    unlockDrag()
  },
})

onMounted(() => {
  ctx = gsap.context(() => {
    drag = Draggable.create(topRef.value, {
      type: 'x,y',
      inertia: false,
      /* Draggable 默认在按下时把被拖元素 z-index 抬到 1000（zIndexBoost），
         导致确认面板（z-index 6）被压在卡下面 —— 必须关掉。 */
      zIndexBoost: false,
      cursor: 'grab',
      activeCursor: 'grabbing',
      allowNativeTouchScrolling: true,
      onPress() {
        moved = 0
      },
      onDrag() {
        const dx = this.x
        const dy = this.y
        moved = Math.max(moved, Math.hypot(dx, dy))
        if (props.variant === 'room') {
          dragStamp(dx, dy)
          gsap.set(this.target, { rotation: dx / 26 })
          return
        }
        const t = Math.min(1, Math.abs(dx) / THRESHOLD)
        if (dx < 0) {
          stamp(stampPassRef.value, t, -11)
          stamp(stampLikeRef.value, 0, 9)
        } else {
          stamp(stampLikeRef.value, t, 9)
          stamp(stampPassRef.value, 0, -11)
        }
        gsap.set(this.target, { rotation: dx / 26 })
      },
      /* 松手时位移仍在点击阈值内 = 一次点击（这是真机上唯一可靠的点击来源） */
      onRelease() {
        if (moved <= TAP_SLOP) emitTap()
      },
      onDragEnd() {
        const dx = this.x
        const dy = this.y

        if (props.variant === 'room') {
          const horizontal = Math.abs(dx) >= Math.abs(dy)
          const magnitude = Math.abs(horizontal ? dx : dy)
          if (magnitude < THRESHOLD) {
            placeCard(false)
            return
          }
          const voteType = horizontal
            ? dx > 0
              ? 'LIKE'
              : 'PASS'
            : dy < 0
              ? 'SUPER_LIKE'
              : 'VETO'
          castVote(voteType)
          return
        }

        if (Math.abs(dx) >= THRESHOLD) {
          if (dx > 0) holdForConfirm()
          else flyAway()
          return
        }
        gsap.set(this.target, { x: this.x, y: this.y })
        placeCard(false)
      },
    })[0]
  }, stageRef.value)

  placeCard(true)
})

watch(
  () => props.cards.map((d) => d.dish_id).join(','),
  () => {
    confirming.value = null
    nextTick(() => {
      placeCard(true)
      unlockDrag()
    })
  },
)

watch(
  () => props.disabled,
  (v) => (v ? lockDrag() : unlockDrag()),
)

onBeforeUnmount(() => {
  drag?.kill()
  drag = null
  ctx?.revert()
  ctx = null
})
</script>

<template>
  <div ref="stageRef" class="deck">
    <div
      v-for="layer in ghostLayers"
      :key="layer.dish.dish_id"
      class="deck__ghost"
      :style="{ '--depth': layer.depth }"
      aria-hidden="true"
    >
      <DishCard :dish="layer.dish" variant="ghost" />
    </div>

    <div
      v-if="top"
      ref="topRef"
      class="deck__top"
      role="button"
      tabindex="0"
      aria-label="查看这道菜的五维解释"
      @click="onCardClick"
      @keydown.enter.prevent="emitTap"
      @keydown.space.prevent="emitTap"
    >
      <slot name="card" :dish="top">
        <DishCard :dish="top" />
      </slot>

      <span ref="stampPassRef" class="stamp stamp--pass">换一个</span>
      <span ref="stampLikeRef" class="stamp stamp--like">就吃这个</span>
      <template v-if="variant === 'room'">
        <span ref="stampSuperRef" class="stamp stamp--super">超想吃</span>
        <span ref="stampVetoRef" class="stamp stamp--veto">不吃</span>
      </template>
    </div>

    <!-- 确认态固定在卡组层，不跟着卡旋转/位移，否则右滑后按钮会被裁出屏幕 -->
    <div v-if="confirming" class="confirm" @click.stop>
      <p class="confirm__text">
        就吃 <b>{{ confirming.name }}</b> 吗？
      </p>
      <div class="confirm__actions">
        <button type="button" class="confirm__btn" @click="cancelConfirm">再想想</button>
        <button type="button" class="confirm__btn confirm__btn--solid" @click="acceptConfirm">
          确认就吃这个
        </button>
      </div>
    </div>

    <p v-if="!top" class="deck__hint">这一批划完了</p>
  </div>
</template>

<style scoped>
.deck {
  position: relative;
  /*
   * 卡面高度由 flex 分配（审查 F06）：
   *   上限 min(47vh, 400px) —— 不铺满屏幕；
   *   可收缩      flex: 1 1 auto + min-height: 0 —— 矮屏（667）自动让位给操作行，
   *              不会像写死高度那样把按钮顶到底栏下面。
   */
  flex: 1 1 auto;
  width: 100%;
  max-height: min(53vh, 440px);
  min-height: 0;
  margin: 0;
  /* 顶卡飞出时要越界显示，但页面本身不允许横向滚动 */
  overflow: visible;
}

.deck__ghost,
.deck__top {
  /* 底部留 26px 给露边卡探出来，卡面本身仍是一屏里最大的一块 */
  position: absolute;
  inset: 0 0 18px;
  will-change: transform;
}

.deck__ghost {
  --offset: calc(var(--depth) * 24px);
  --shrink: calc(1 - var(--depth) * 0.05);
  transform: translateY(var(--offset)) scale(var(--shrink));
  transform-origin: 50% 50%;
  pointer-events: none;
  opacity: calc(0.9 - var(--depth) * 0.18);
}

.deck__top {
  z-index: 3;
  cursor: grab;
  touch-action: pan-y;
}

.deck__top:active {
  cursor: grabbing;
}

/* 顶卡内层不裁切阴影 */
.deck__top > :deep(.dishcard) {
  box-shadow: var(--glass-card-shadow);
}
 
.stamp {
  position: absolute;
  top: 24%;
  left: 50%;
  padding: 8px 14px;
  border-radius: 12px;
  border: 2px solid rgb(var(--rgb-white) / 0.8);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-white);
  background: rgb(var(--rgb-ink) / 0.32);
  backdrop-filter: blur(4px);
  opacity: 0;
  pointer-events: none;
}

 
.stamp--like {
  background: rgb(var(--rgb-white) / 0.92);
  color: var(--color-ink);
  border-color: rgb(var(--rgb-white) / 0.92);
}

.stamp--super,
.stamp--veto {
  top: 38%;
}

.stamp--super {
  background: var(--color-white);
  color: var(--color-ink);
  border-color: var(--color-white);
}

.stamp--veto {
  background: rgb(var(--rgb-ink) / 0.72);
  border-style: dashed;
}
 
.confirm {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 0;
  z-index: 6;
  padding: 14px;
  border-radius: 18px;
  background: rgb(var(--rgb-panel) / 0.92);
  backdrop-filter: blur(18px) saturate(150%);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.16), 0 12px 28px rgb(var(--rgb-black) / 0.45);
}

.confirm__text {
  margin: 0 0 10px;
  font-size: 13.5px;
  color: var(--on-glass-soft);
}

.confirm__text b {
  color: var(--color-white);
}

.confirm__actions {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 8px;
}

.confirm__btn {
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgb(var(--rgb-white) / 0.24);
  background: transparent;
  color: var(--color-white);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.confirm__btn--solid {
  border-color: transparent;
  background: var(--color-white);
  color: var(--color-ink);
}

.deck__hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 13px;
  color: var(--on-glass-dim);
}
</style>
