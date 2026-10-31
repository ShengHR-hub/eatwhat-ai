<script setup>
/**
 * 菜品卡（卡组用）。同一份结构渲染三种形态：
 *   - 顶卡（variant = 'full'）：完整信息 + 一级玻璃（G 方案，开折射，由父级加 .glass-card）
 *   - 露边卡（variant = 'ghost'）：只留名字与分数，磨砂降级（.glass-card--matte）
 *   - 紧凑索引不用它，索引是列表元素
 *
 * 视觉区统一使用菜品八维风味雷达：不依赖图片，合成菜与真实菜都能稳定展示。
 * 雷达只描述菜品自身风味，不代表用户匹配度；匹配度仍在正文单独展示。
 */
import { computed } from 'vue'

import DishRadar from './DishRadar.vue'
import NumberTicker from './NumberTicker.vue'

const props = defineProps({
  dish: { type: Object, required: true },
  variant: { type: String, default: 'full' }, // full | ghost
})

const isGhost = computed(() => props.variant === 'ghost')

const priceLabel = computed(() => {
  const v = props.dish?.price
  if (v == null) return '—'
  return `¥${Number(v).toFixed(0)}`
})

const score = computed(() => Number(props.dish?.total_score ?? 0))
</script>

<template>
  <article class="dishcard" :class="isGhost ? 'glass-card--matte' : 'glass-card'">
    <div v-if="!isGhost" class="dishcard__radar">
      <DishRadar :vector="dish.feature_vector" />
      <span v-if="dish.is_favorite" class="dishcard__flag">红榜</span>
    </div>

    <!-- 露边卡只作为"一摞卡"的边缘，不渲染任何文字，避免半透明叠字 -->
    <div v-if="!isGhost" class="dishcard__body">
      <!-- 一屏口径：卡面变高后，信息块在正文区里垂直居中，footer 压到底 -->
      <div class="dishcard__info">
      <h3 class="dishcard__name">{{ dish.name }}</h3>

      <p class="dishcard__meta">
        <span v-if="dish.restaurant_name">{{ dish.restaurant_name }}</span>
        <span v-if="dish.restaurant_name" class="dishcard__dot">·</span>
        <span class="dishcard__price">{{ priceLabel }}</span>
        <template v-if="!isGhost">
          <span class="dishcard__dot">·</span>
          <span>{{ dish.cuisine_type }}</span>
        </template>
      </p>

      <div class="dishcard__score">
        <span class="dishcard__score-k">匹配度</span>
        <span class="dishcard__score-v">
          <NumberTicker :value="score" :decimals="1" suffix="%" />
        </span>
      </div>

      <p v-if="!isGhost && dish.explain_reason" class="dishcard__reason">{{ dish.explain_reason }}</p>
      </div>

      <div v-if="!isGhost" class="dishcard__foot">
        <span class="dishcard__metric">
          防腻权重 <b class="tabular">{{ dish.decay_weight?.toFixed(2) ?? '—' }}</b>
        </span>
        <span class="dishcard__metric">菜品角色 <b>{{ dish.dish_role }}</b></span>
        <span class="dishcard__tap">点卡片看五维</span>
      </div>
    </div>
  </article>
</template>

<style scoped>


.dishcard {
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 24px;
  height: 100%;
  /* 覆盖 .glass-card 的 16px 内边距：图区要通栏，内边距交给 body */
  padding: 0;
  color: var(--on-glass);
}

.dishcard__radar {
  position: relative;
  /* 雷达区占整卡 38%，与旧图位同高，保证一屏布局不漂移 */
  flex: 0 0 38%;
  min-height: 0;
  border-bottom: 1px solid rgb(var(--rgb-white) / 0.08);
}

.dishcard__flag {
  position: absolute;
  top: 12px;
  left: 12px;
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 600;
  background: rgb(var(--rgb-ink) / 0.72);
  color: var(--color-white);
  backdrop-filter: blur(6px);
}

.dishcard__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px 14px;
}

.dishcard__info {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  min-height: 0;
}

.dishcard__name {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.dishcard__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

.dishcard__price {
  font-weight: 600;
  color: var(--on-glass);
}

.dishcard__dot {
  opacity: 0.5;
}

.dishcard__score {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 2px;
}

.dishcard__score-k {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--on-glass-dim);
}

.dishcard__score-v {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.dishcard__reason {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--on-glass-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* —— 露边卡：只留名字与分数，尺寸由父级缩放 —— */
:global(.dishcard--ghost) {
  height: 100%;
}

.dishcard__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 14px;
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px solid rgb(var(--rgb-white) / 0.1);
}

.dishcard__metric {
  font-size: 10px;
  color: var(--on-glass-dim);
}

.dishcard__metric b {
  font-weight: 650;
  color: var(--on-glass-soft);
}

.dishcard__tap {
  margin-left: auto;
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--on-glass-dim);
}
/* 矮屏（≤720px 高）：卡面被压到 260 左右时，图和正文要一起收，
   否则 footer 会被卡片圆角裁掉——2026-10-24 在 390×667 上踩过。 */
@media (max-height: 720px) {
  .dishcard__radar {
    flex: 0 0 32%;
  }

  .dishcard__name {
    font-size: 19px;
  }

  .dishcard__score {
    font-size: 24px;
  }

  .dishcard__reason {
    -webkit-line-clamp: 1;
  }

  .dishcard__foot {
    display: none;
  }
}
</style>
