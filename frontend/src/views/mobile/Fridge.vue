<script setup>
/**
 * 虚拟冰箱（批次 3 前半）。
 *
 * 契约：MASTER_SPEC.md 第五章「模块3」
 *   GET  /fridge/{user_id}       临期置顶，is_expiring_soon 由后端算（<=2 天）
 *   POST /fridge/{user_id}       ADD 幂等 upsert / REMOVE 按名字删
 *   POST /fridge/shopping-list   多菜谱主辅料并集 - 冰箱现有
 *
 * 单色体系：临期不用红色，用「实白底 + ink 字」的最高对比徽章表达紧急度，
 * 与全站的双模式不靠颜色的规则一致。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAutoAnimate } from '@formkit/auto-animate/vue'
import { fetchFridge, fetchHomeDishes, fetchShoppingList, scanFridge, scanImportFridge, upsertFridge } from '../../api'
import { usePersonaStore } from '../../stores/persona'

const persona = usePersonaStore()

const CATEGORIES = ['肉禽蛋奶', '新鲜果蔬', '冷冻速食', '豆制品与干货']

const items = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const formOpen = ref(false)
const form = ref({ ingredient_name: '', category: '新鲜果蔬', quantity_desc: '适量', expire_days: 3 })

const homeDishes = ref([])
const picked = ref([])
const shopping = ref(null)
const shoppingBusy = ref(false)
const shoppingError = ref('')
const scanOpen = ref(false)
const scanning = ref(false)
const hasScanned = ref(false)
const scanInput = ref(null)
const scanPreview = ref('')
const scanError = ref('')
const scanMessage = ref('')
let scanTimer = 0
onBeforeUnmount(() => clearTimeout(scanTimer))
const scanResults = ref([
  { name: '番茄', category: '新鲜果蔬', quantity: '2 个', days: 3, selected: true },
  { name: '牛腩', category: '肉禽蛋奶', quantity: '300g', days: 2, selected: true },
  { name: '青菜', category: '新鲜果蔬', quantity: '1 把', days: 2, selected: true },
  { name: '鸡蛋', category: '肉禽蛋奶', quantity: '6 个', days: 7, selected: true },
])

const [listRef] = useAutoAnimate({ duration: 220 })
const [buyRef] = useAutoAnimate({ duration: 220 })

const expiringCount = computed(() => items.value.filter((it) => it.is_expiring_soon).length)

const grouped = computed(() => {
  // 后端已按「临期优先、剩余天数」排好序，这里只做分组，不重排组内顺序
  return CATEGORIES.map((name) => ({
    name,
    rows: items.value.filter((it) => it.category === name),
  })).filter((group) => group.rows.length > 0)
})

const pickedCount = computed(() => picked.value.length)

function expireText(days) {
  if (days <= 0) return '已到期'
  if (days === 1) return '明天到期'
  if (days <= 2) return `${days} 天后到期`
  return `还有 ${days} 天`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchFridge(persona.userId)
    items.value = data.items || []
  } catch (err) {
    error.value = err?.message || '冰箱没打开，稍后再试'
  } finally {
    loading.value = false
  }
}

async function addItem() {
  const name = form.value.ingredient_name.trim()
  if (!name) {
    error.value = '先写个食材名字'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const data = await upsertFridge(persona.userId, {
      ingredient_name: name,
      category: form.value.category,
      quantity_desc: form.value.quantity_desc || '适量',
      expire_days: Number(form.value.expire_days) || 0,
      action: 'ADD',
    })
    items.value = data.items || []
    form.value = { ingredient_name: '', category: form.value.category, quantity_desc: '适量', expire_days: 3 }
  } catch (err) {
    error.value = err?.message || '没存进去'
  } finally {
    busy.value = false
  }
}

function openScan() {
  scanOpen.value = true
  scanning.value = false
  hasScanned.value = false
  scanError.value = ''
  scanMessage.value = ''
  scanResults.value = scanResults.value.map((item) => ({ ...item, selected: true }))
  scanPreview.value = ''
}

function closeScan() {
  if (scanning.value) return
  scanOpen.value = false
}

function startScan() {
  scanInput.value?.click()
}

function useDemoScan() {
  scanning.value = false
  hasScanned.value = true
  scanError.value = ''
  scanResults.value = scanResults.value.map((item) => ({ ...item, selected: true }))
}

async function onScanFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  scanPreview.value = URL.createObjectURL(file)
  scanning.value = true
  scanError.value = ''
  hasScanned.value = false
  try {
    const data = await scanFridge(file)
    scanResults.value = (data.items || []).map((item) => ({
      name: item.ingredient_name,
      category: item.category,
      quantity: item.quantity_desc,
      days: item.expire_days,
      selected: Number(item.confidence ?? 1) >= 0.5,
    }))
    hasScanned.value = true
  } catch (err) {
    scanError.value = err?.detail || err?.message || '识别失败'
  } finally {
    scanning.value = false
  }
}

function toggleScanItem(index) {
  scanResults.value[index].selected = !scanResults.value[index].selected
}

async function confirmScan() {
  const chosen = scanResults.value.filter((item) => item.selected)
  if (!chosen.length) {
    scanError.value = '至少选一样食材'
    return
  }
  busy.value = true
  scanError.value = ''
  try {
    const data = await scanImportFridge(persona.userId, chosen.map((item) => ({
      ingredient_name: item.name,
      category: item.category,
      quantity_desc: item.quantity,
      expire_days: item.days,
      confidence: 0.9,
    })))
    items.value = data.items || []
    scanOpen.value = false
    scanMessage.value = `已加入冰箱：${chosen.map((item) => item.name).join('、')}`
    clearTimeout(scanTimer)
    scanTimer = window.setTimeout(() => (scanMessage.value = ''), 2400)
  } catch (err) {
    scanError.value = err?.message || '入库失败'
  } finally {
    busy.value = false
  }
}

async function removeItem(item) {
  busy.value = true
  error.value = ''
  try {
    const data = await upsertFridge(persona.userId, {
      ingredient_name: item.ingredient_name,
      category: item.category,
      action: 'REMOVE',
    })
    items.value = data.items || []
  } catch (err) {
    error.value = err?.message || '没删掉'
  } finally {
    busy.value = false
  }
}

async function loadDishes() {
  try {
    homeDishes.value = (await fetchHomeDishes()).slice(0, 24)
  } catch {
    homeDishes.value = []
  }
}

function togglePick(id) {
  picked.value = picked.value.includes(id)
    ? picked.value.filter((x) => x !== id)
    : [...picked.value, id]
}

async function buildShoppingList() {
  if (!picked.value.length) {
    shoppingError.value = '先选一两道想做的菜'
    return
  }
  shoppingBusy.value = true
  shoppingError.value = ''
  try {
    shopping.value = await fetchShoppingList(picked.value)
  } catch (err) {
    shoppingError.value = err?.message || '清单没生成出来'
    shopping.value = null
  } finally {
    shoppingBusy.value = false
  }
}

function clearShopping() {
  shopping.value = null
  picked.value = []
  shoppingError.value = ''
}

onMounted(async () => {
  await Promise.all([load(), loadDishes()])
})

// S01：角色切换后冰箱必须重新拉取，不能继续显示上一个角色缓存
watch(() => persona.userId, async () => {
  picked.value = []
  shopping.value = null
  shoppingError.value = ''
  await load()
})
</script>

<template>
  <div class="fridge">
    <header class="fridge__head">
      <div>
        <p class="fridge__eyebrow">虚拟冰箱</p>
        <h1 class="fridge__title">冰箱里有什么</h1>
        <p class="fridge__sub">临期先吃，别放坏了</p>
      </div>
      <button type="button" class="scan-btn" @click="openScan">拍照入库</button>
    </header>

    <section class="summary glass-card">
      <div class="summary__cell">
        <span class="summary__num tabular">{{ items.length }}</span>
        <span class="summary__label">件食材</span>
      </div>
      <div class="summary__cell">
        <span class="summary__num tabular">{{ expiringCount }}</span>
        <span class="summary__label">件临期</span>
      </div>
      <div class="summary__cell">
        <span class="summary__num tabular">{{ pickedCount }}</span>
        <span class="summary__label">道想做的菜</span>
      </div>
    </section>

    <p v-if="error" class="hint hint--warn">{{ error }}</p>
    <p v-if="scanMessage" class="hint">{{ scanMessage }}</p>

    <section v-if="expiringCount" class="alert glass-card">
      <span class="alert__dot" aria-hidden="true" />
      <p class="alert__text">
        有 <b>{{ expiringCount }}</b> 件快到期了，今明两天优先用掉它们
      </p>
    </section>

    <section class="section">
      <div class="section__head">
        <h2 class="section__title">库存</h2>
        <button type="button" class="link-btn" @click="formOpen = !formOpen">
          {{ formOpen ? '收起' : '＋ 添加食材' }}
        </button>
      </div>

      <form v-if="formOpen" class="form glass-card" @submit.prevent="addItem">
        <input
          v-model="form.ingredient_name"
          class="field"
          type="text"
          maxlength="32"
          placeholder="食材名，比如 鸡蛋"
        />
        <div class="form__row">
          <select v-model="form.category" class="field field--select">
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
          <input v-model="form.quantity_desc" class="field field--qty" type="text" maxlength="32" placeholder="适量" />
          <label class="field field--days">
            <input v-model.number="form.expire_days" type="number" min="0" max="365" />
            <span>天</span>
          </label>
        </div>
        <button type="submit" class="btn-ink" :disabled="busy">{{ busy ? '保存中…' : '放进冰箱' }}</button>
      </form>

      <p v-if="loading" class="hint">正在打开冰箱…</p>
      <p v-else-if="!items.length" class="hint">冰箱是空的，先加点食材吧</p>

      <div v-else ref="listRef" class="groups">
        <section v-for="group in grouped" :key="group.name" class="group">
          <h3 class="group__title">{{ group.name }}<span class="group__count">{{ group.rows.length }}</span></h3>
          <ul class="rows">
            <li v-for="item in group.rows" :key="item.id" class="row glass-card--matte">
              <div class="row__main">
                <p class="row__name">{{ item.ingredient_name }}</p>
                <p class="row__meta">
                  <span>{{ item.quantity_desc || '适量' }}</span>
                  <span class="row__sep">·</span>
                  <span :class="item.is_expiring_soon ? 'row__expire row__expire--hot' : 'row__expire'">
                    {{ expireText(item.expire_days) }}
                  </span>
                </p>
              </div>
              <button type="button" class="row__del" :disabled="busy" @click="removeItem(item)">用完了</button>
            </li>
          </ul>
        </section>
      </div>
    </section>

    <section class="section">
      <div class="section__head">
        <h2 class="section__title">买菜清单</h2>
        <span class="section__hint">选菜 → 扣掉冰箱现有</span>
      </div>

      <p v-if="!homeDishes.length" class="hint">菜谱还没加载出来</p>
      <div v-else class="picks">
        <button
          v-for="dish in homeDishes"
          :key="dish.dish_id"
          type="button"
          class="pick"
          :class="{ 'pick--on': picked.includes(dish.dish_id) }"
          @click="togglePick(dish.dish_id)"
        >
          {{ dish.name }}
        </button>
      </div>

      <div class="section__actions">
        <button type="button" class="btn-ink" :disabled="shoppingBusy" @click="buildShoppingList">
          {{ shoppingBusy ? '正在算…' : `生成清单${pickedCount ? `（${pickedCount} 道）` : ''}` }}
        </button>
        <button v-if="shopping" type="button" class="btn-ghost-ink" @click="clearShopping">清空</button>
      </div>

      <p v-if="shoppingError" class="hint hint--warn">{{ shoppingError }}</p>

      <div v-if="shopping" class="result">
        <div class="result__col">
          <h3 class="result__title">冰箱已有 <span class="group__count">{{ shopping.owned_ingredients.length }}</span></h3>
          <p v-if="!shopping.owned_ingredients.length" class="hint">这次要用的食材冰箱里都没有</p>
          <ul v-else class="rows">
            <li v-for="it in shopping.owned_ingredients" :key="it.ingredient" class="row glass-card--matte">
              <div class="row__main">
                <p class="row__name">{{ it.ingredient }}</p>
                <p class="row__meta">用于 {{ it.used_by.join('、') }}</p>
              </div>
              <span class="tag">够用</span>
            </li>
          </ul>
        </div>

        <div class="result__col">
          <h3 class="result__title">还要买 <span class="group__count">{{ shopping.to_buy_ingredients.length }}</span></h3>
          <p v-if="!shopping.to_buy_ingredients.length" class="hint">冰箱里的料够做这些菜了</p>
          <ul v-else ref="buyRef" class="rows">
            <li v-for="it in shopping.to_buy_ingredients" :key="it.ingredient" class="row glass-card--matte">
              <div class="row__main">
                <p class="row__name">{{ it.ingredient }}</p>
                <p class="row__meta">用于 {{ it.used_by.join('、') }}</p>
              </div>
              <span class="tag tag--buy">{{ it.used_by.length }} 道菜</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>

    <div v-if="scanOpen" class="scan-overlay" @click.self="closeScan">
      <aside class="scan-sheet" aria-label="拍照入库">
        <header class="scan-head"><div><p>VISION · CLOUD</p><h2>拍照入库</h2></div><button type="button" @click="closeScan">×</button></header>
        <div class="scan-view">
          <img v-if="scanPreview" class="scan-photo" :src="scanPreview" alt="上传的食材照片" />
          <svg v-else viewBox="0 0 340 220" aria-label="冰箱食材识别示意"><rect width="340" height="220" fill="var(--v5-scan-bg)"/><rect y="154" width="340" height="7" fill="var(--v5-illus-line)"/><circle cx="50" cy="128" r="16" fill="var(--v5-illus-warm-1)"/><circle cx="74" cy="133" r="12" fill="var(--v5-illus-warm-2)"/><path d="M130 138c-8-24 7-38 24-38 4 18 0 34-12 43-5 3-9 1-12-5Z" fill="var(--v5-illus-green-1)"/><path d="M155 141c2-22 15-34 29-31-1 17-8 31-21 39-5 2-8-2-8-8Z" fill="var(--v5-illus-green-2)"/><rect x="220" y="108" width="40" height="38" rx="8" fill="var(--v5-illus-warm-3)"/><rect x="225" y="113" width="30" height="28" rx="5" fill="var(--v5-illus-warm-4)"/><ellipse cx="291" cy="122" rx="13" ry="17" fill="var(--v5-illus-light-1)"/><ellipse cx="310" cy="126" rx="12" ry="16" fill="var(--v5-illus-light-2)"/></svg>
          <span class="scan-line" :class="{ 'is-on': scanning }" />
          <span class="scan-status">{{ scanning ? '云端识别中…' : scanPreview ? `识别完成 · ${scanResults.length} 样` : '示意画面 · 对准食材后拍一张' }}</span>
        </div>
        <input ref="scanInput" type="file" accept="image/*" capture="environment" hidden @change="onScanFile" /><button type="button" class="scan-action" :disabled="scanning || busy" @click="startScan">{{ scanning ? '识别中…' : '拍照识别' }}</button>
        <p v-if="scanError" class="scan-error">{{ scanError }}</p>
        <button v-if="scanError" type="button" class="scan-demo" @click="useDemoScan">使用演示结果</button>
        <div v-if="!scanning && hasScanned" class="scan-results">
          <div class="scan-results__head"><b>识别到 {{ scanResults.length }} 样</b><span>请确认后入库</span></div>
          <button v-for="(item, index) in scanResults" :key="item.name" type="button" class="scan-item" :class="{ 'is-on': item.selected }" @click="toggleScanItem(index)">
            <span class="scan-check">✓</span><span class="scan-item__name">{{ item.name }}</span><span class="scan-item__meta">{{ item.quantity }} · {{ item.days }} 天</span>
          </button>
          <button type="button" class="scan-confirm" :disabled="busy" @click="confirmScan">{{ busy ? '入库中…' : '确认入库' }}</button>
        </div>
      </aside>
    </div>
</template>

<style scoped>
.fridge {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 4px;
  color: var(--on-glass);
}

.fridge__eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--on-glass-dim);
}

.fridge__title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.25;
}

.fridge__sub {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--on-glass-soft);
}

.summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 12px 14px;
  border-radius: 1.125rem;
}

.summary__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary__num {
  font-size: 21px;
  font-weight: 700;
  line-height: 1.1;
}

.summary__label {
  font-size: 10.5px;
  color: var(--on-glass-soft);
}

.alert {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 13px;
  border-radius: 1rem;
}

.alert__dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 50%;
  background: var(--on-glass);
}

.alert__text {
  margin: 0;
  font-size: 12px;
  color: var(--on-glass-soft);
}

.alert__text b {
  color: var(--on-glass);
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.section__title {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.section__hint {
  font-size: 11px;
  color: var(--on-glass-dim);
}

.section__actions {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.link-btn {
  border: 0;
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
}

.link-btn:hover {
  color: var(--on-glass);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 1rem;
}

.form__row {
  display: grid;
  grid-template-columns: 1fr 84px 78px;
  gap: 8px;
}

.field {
  width: 100%;
  min-height: 36px;
  padding: 0 10px;
  border-radius: 0.75rem;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: rgb(var(--rgb-white) / 0.08);
  color: var(--on-glass);
  font-size: 12.5px;
}

.field::placeholder {
  color: var(--on-glass-dim);
}

.field--select option {
  color: var(--color-ink);
}

.field--days {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  font-size: 11px;
  color: var(--on-glass-soft);
}

.field--days input {
  width: 100%;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--on-glass);
  font-size: 12.5px;
}

.groups {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group__title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--on-glass-soft);
}

.group__count {
  min-width: 16px;
  padding: 1px 5px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
  font-size: 9.5px;
  text-align: center;
  color: var(--on-glass-soft);
}

.rows {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 0.95rem;
}

.row__name {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
}

.row__meta {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin: 3px 0 0;
  font-size: 11px;
  color: var(--on-glass-dim);
}

.row__expire--hot {
  color: var(--on-glass);
  font-weight: 600;
}

.row__del {
  flex: 0 0 auto;
  padding: 6px 11px;
  border-radius: 999px;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 11px;
  cursor: pointer;
}

.row__del:hover {
  background: rgb(var(--rgb-white) / 0.1);
  color: var(--on-glass);
}

.picks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 112px;
  overflow-y: auto;
  padding: 2px 1px;
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--rgb-white) / 0.24) transparent;
}

.picks::-webkit-scrollbar {
  width: 4px;
}

.picks::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.24);
}

.pick {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 11.5px;
  cursor: pointer;
}

.pick--on {
  background: var(--on-glass);
  border-color: transparent;
  color: var(--color-ink);
  font-weight: 600;
}

.result {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 4px;
}

.result__title {
  margin: 0 0 7px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--on-glass-soft);
}

.tag {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
  font-size: 10px;
  color: var(--on-glass-soft);
}

.tag--buy {
  background: var(--on-glass);
  color: var(--color-ink);
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-glass-soft);
}

.hint--warn {
  color: var(--on-glass);
}

.btn-ink {
  min-height: 38px;
  border: 0;
  border-radius: 999px;
  background: var(--on-glass);
  color: var(--color-ink);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.btn-ink:disabled {
  opacity: 0.55;
  cursor: default;
}

.btn-ghost-ink {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 12.5px;
  cursor: pointer;
}

.fridge__head { position: relative; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.scan-btn { flex: 0 0 auto; height: 30px; padding: 0 11px; border-radius: 15px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 10px; font-weight: 600; }
.scan-overlay { position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(390px, 100vw); height: min(812px, 100dvh); z-index: 60; display: flex; align-items: flex-end; justify-content: center; overflow: hidden; border-radius: 42px; background: rgb(var(--rgb-v5-shadow) / .32); }
.scan-sheet { width: 100%; max-height: 92%; overflow-y: auto; padding: 10px 18px calc(80px + env(safe-area-inset-bottom,0px)); border-radius: 26px 26px 0 0; background: var(--v5-illus-panel); border-top: 1px solid rgb(var(--rgb-white) / .9); box-shadow: 0 -20px 60px rgb(var(--rgb-v5-shadow) / .2); }
.scan-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 4px 0 10px; }
.scan-head p { margin: 0 0 3px; font-size: 8.5px; letter-spacing: .14em; color: var(--on-glass-dim); }
.scan-head h2 { margin: 0; font-size: 19px; font-weight: 600; color: var(--on-glass); }
.scan-head button { width: 30px; height: 30px; border-radius: 50%; background: rgb(var(--rgb-v5-ink) / .06); color: var(--on-glass-soft); font-size: 17px; }
.scan-view { position: relative; height: 210px; overflow: hidden; border-radius: 16px; background: var(--v5-scan-bg); }
.scan-view svg { width: 100%; height: 100%; display: block; }
.scan-photo { width: 100%; height: 100%; object-fit: cover; display: block; }
.scan-line { position: absolute; left: 7%; right: 7%; top: 12%; height: 1px; background: rgb(var(--rgb-v5-photo-ink) / .7); opacity: 0; }
.scan-line.is-on { opacity: 1; animation: scan-move 1.1s ease-in-out infinite; }
@keyframes scan-move { 0%,100% { transform: translateY(0); } 50% { transform: translateY(150px); } }
.scan-status { position: absolute; left: 50%; bottom: 8px; transform: translateX(-50%); padding: 4px 8px; border-radius: 8px; background: rgb(var(--rgb-v5-illus-scrim) / .72); color: rgb(var(--rgb-v5-photo-ink) / .85); font-size: 8.5px; white-space: nowrap; }
.scan-action { width: 100%; height: 38px; margin-top: 10px; border-radius: 11px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 11px; font-weight: 600; }
.scan-error { margin: 8px 0 0; font-size: 9px; color: var(--v5-danger); }
.scan-demo { margin-top: 6px; padding: 0; font-size: 9px; color: var(--v5-muted); text-decoration: underline; text-underline-offset: 3px; }
.scan-results { margin-top: 12px; padding-top: 10px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .1); }
.scan-results__head { display: flex; justify-content: space-between; margin-bottom: 7px; font-size: 9px; color: var(--on-glass-soft); }
.scan-results__head b { color: var(--on-glass); font-weight: 600; }
.scan-item { width: 100%; display: grid; grid-template-columns: 20px 1fr auto; gap: 8px; align-items: center; padding: 7px 0; border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .08); text-align: left; }
.scan-check { width: 17px; height: 17px; border-radius: 5px; border: 1px solid rgb(var(--rgb-v5-ink) / .2); display: grid; place-items: center; color: transparent; font-size: 10px; }
.scan-item.is-on .scan-check { background: var(--v5-ink); border-color: var(--v5-ink); color: var(--v5-paper-strong); }
.scan-item__name { font-size: 10px; color: var(--on-glass); }
.scan-item__meta { font-size: 8.5px; color: var(--on-glass-dim); }
.scan-confirm { width: 100%; height: 40px; margin-top: 11px; border-radius: 12px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 11px; font-weight: 600; }

</style>
