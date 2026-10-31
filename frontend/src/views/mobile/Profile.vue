<script setup>
/**
 * Profile.vue —— 用户主页，四区块（MASTER_SPEC 第六章 §3）：
 *   1. 人设卡 + 「切换演示室友账号」一键切换
 *   2. 饮食基因八维进度条 + 默认预算滑块 + 忌口红线胶囊（auto-animate 增删）
 *   3. 美食红黑榜：红榜只菜品；黑榜分菜品 / 门店两类，可一键移出
 *   4. 干饭战绩：累计决策次数、外食 / 下厨花费占比、多人房间战绩
 *
 * 数据全部来自 /users/{id}/profile；红黑榜只有 id，用 /catalog/* 翻名字。
 * 不写死任何颜色，灰阶全走 CSS 变量。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAutoAnimate } from '@formkit/auto-animate/vue'

import { fetchDishes, fetchFridge, fetchMe, fetchRestaurants, logoutAccount, savePreferences, updateProfileBasic, uploadAvatar } from '../../api'
import { clearToken, getToken, setUserId } from '../../api/client'
import { usePersonaStore } from '../../stores/persona'
import V5Radar from '../../components/V5Radar.vue'

const persona = usePersonaStore()

const [userListRef] = useAutoAnimate({ duration: 200 })
const [vetoRef] = useAutoAnimate({ duration: 200 })
const [boardRef] = useAutoAnimate({ duration: 200 })

const dishMap = ref(new Map())
const restaurantMap = ref(new Map())
const switching = ref(false)
const showUsers = ref(false)
const newVeto = ref('')
const saving = ref('')
const tab = ref('fav')
const budgetDraft = ref(null)
const notice = ref('')
// 提示条计时器：卸载时要清，否则会在已销毁的组件上写状态
let noticeTimer = 0
const token = ref(getToken())
// 管理后台入口只对 ADMIN 显示；角色来自 /auth/me，未登录或普通用户一律不显示
const isAdmin = ref(false)
// 资料编辑：昵称与头像走独立接口，与偏好（预算/忌口/向量）分开
const editing = ref(false)
const editDraft = reactive({ nickname: '', avatar: '' })
const editSaving = ref(false)
const avatarUploading = ref(false)
const geneEditing = ref(false)
const geneSaving = ref(false)
const geneDraft = reactive({})

/** 头像是图片路径还是 emoji，决定用 img 还是文本渲染 */
function isImageAvatar(value) {
  return typeof value === 'string' && (value.startsWith('/uploads/') || value.startsWith('http'))
}

async function pickAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  avatarUploading.value = true
  try {
    const body = await uploadAvatar(persona.userId, file)
    editDraft.avatar = body.avatar
    await persona.loadProfile()
  } catch (err) {
    notice.value = err?.detail || '头像上传失败'
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 2000))
  } finally {
    avatarUploading.value = false
    event.target.value = ''
  }
}

function openEdit() {
  editDraft.nickname = profile.value?.nickname || ''
  editDraft.avatar = profile.value?.avatar || ''
  editing.value = true
}

async function saveProfile() {
  if (editSaving.value) return
  editSaving.value = true
  try {
    await updateProfileBasic(persona.userId, {
      nickname: editDraft.nickname.trim(),
      avatar: editDraft.avatar.trim(),
    })
    await persona.loadProfile()
    editing.value = false
    notice.value = '资料已更新'
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 1600))
  } catch (err) {
    notice.value = err?.detail || '保存失败'
  } finally {
    editSaving.value = false
  }
}
const BG_KEY = 'eatwhat.v5.background'
const bgMode = ref('default')
const bgUrl = ref('')
const bgName = ref('')
const bgOverlay = ref(42)
const bgTextMode = ref('auto')
const bgLum = ref(0.5)
try {
  const saved = JSON.parse(localStorage.getItem(BG_KEY) || 'null')
  if (saved) {
    bgMode.value = saved.mode || 'default'
    bgUrl.value = saved.url || ''
    bgName.value = saved.name || ''
    bgOverlay.value = Number(saved.overlay ?? 42)
    bgTextMode.value = saved.textMode || 'auto'
    bgLum.value = Number(saved.luminance ?? 0.5)
  }
} catch {}
function pickBackground(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, 1024 / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
      const thumb = document.createElement('canvas')
      thumb.width = 48
      thumb.height = 48
      const tc = thumb.getContext('2d')
      tc.drawImage(img, 0, 0, 48, 48)
      const data = tc.getImageData(0, 0, 48, 48).data
      let sum = 0
      for (let i = 0; i < data.length; i += 4) sum += (data[i] + data[i + 1] + data[i + 2]) / 3
      bgLum.value = sum / (data.length / 4) / 255
      bgUrl.value = canvas.toDataURL('image/jpeg', 0.72)
      bgName.value = file.name
      bgMode.value = 'image'
    }
    img.src = reader.result
  }
  reader.readAsDataURL(file)
}
function saveBackground() {
  try {
    localStorage.setItem(BG_KEY, JSON.stringify(bgMode.value === 'image' ? { mode: 'image', url: bgUrl.value, name: bgName.value, overlay: bgOverlay.value, textMode: bgTextMode.value, luminance: bgLum.value } : { mode: 'default' }))
    notice.value = bgMode.value === 'image' ? '背景已保存，首页生效' : '已恢复默认水彩'
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 1800))
  } catch {
    notice.value = '图片太大，保存失败'
  }
  // 通知 MobileShell 重读，否则只有首页会更新
  window.dispatchEvent(new Event('eatwhat:background-changed'))
}

const GENES = [
  { key: 'spicy_level', name: '辣度', hint: '无辣不欢 ↔ 一点不沾' },
  { key: 'oily_level', name: '油度', hint: '重油爆炒 ↔ 清汤寡水' },
  { key: 'soup_level', name: '汤感', hint: '爱喝汤 ↔ 不喝汤' },
  { key: 'temp_fit', name: '温度适配', hint: '对冷热敏感程度' },
  { key: 'satiety_level', name: '饱腹需求', hint: '要吃饱 ↔ 垫一口' },
  { key: 'prep_speed', name: '出餐速度', hint: '能等 ↔ 立刻要' },
  { key: 'social_fit', name: '社交友好', hint: '一个人吃 ↔ 拼桌' },
  { key: 'comfort_level', name: '治愈程度', hint: '随便吃 ↔ 要慰藉' },
]

const VETO_PRESETS = ['折耳根', '香菜', '海鲜', '花生', '牛奶', '内脏']

const neutralVector = computed(() =>
  GENES.every((gene) => Math.abs(Number(profile.value?.base_vector?.[gene.key] ?? 0.5) - 0.5) < 0.01)
)

function openGeneEditor() {
  for (const gene of GENES) {
    geneDraft[gene.key] = Number(profile.value?.base_vector?.[gene.key] ?? 0.5)
  }
  geneEditing.value = true
}

async function saveGenes() {
  if (geneSaving.value) return
  geneSaving.value = true
  try {
    const baseVector = {}
    for (const gene of GENES) baseVector[gene.key] = Number(geneDraft[gene.key] ?? 0.5)
    await savePreferences(persona.userId, { base_vector: baseVector })
    await persona.loadProfile()
    geneEditing.value = false
    notice.value = '饮食基因已更新，推荐与后台画像同步'
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 2000))
  } catch (err) {
    notice.value = err?.detail || err?.message || '饮食基因保存失败'
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 2200))
  } finally {
    geneSaving.value = false
  }
}

const profile = computed(() => persona.profile)
const budget = computed(() => Number(profile.value?.default_budget ?? 0))
const vetoTags = computed(() => profile.value?.veto_tags ?? [])
const favDishes = computed(() => toDishes(profile.value?.favorite_dish_ids))
const blackDishes = computed(() => toDishes(profile.value?.blacklist_dish_ids))
const blackRestaurants = computed(() => toRestaurants(profile.value?.blacklist_restaurant_ids))
const achievements = computed(() => profile.value?.achievements ?? {})

const tabs = computed(() => [
  { key: 'fav', name: '红榜菜品', count: favDishes.value.length },
  { key: 'blackdish', name: '黑榜菜品', count: blackDishes.value.length },
  { key: 'blackrest', name: '黑榜门店', count: blackRestaurants.value.length },
])

const activeRows = computed(() => {
  if (tab.value === 'fav') return favDishes.value
  if (tab.value === 'blackdish') return blackDishes.value
  return blackRestaurants.value
})

const spend = computed(() => {
  const out = Number(achievements.value.out_dining_spent ?? 0)
  const home = Number(achievements.value.home_cooking_spent ?? 0)
  const total = out + home
  const outPct = total > 0 ? Math.round((out / total) * 100) : 0
  return { out, home, total, outPct, homePct: total > 0 ? 100 - outPct : 0 }
})

function toDishes(ids) {
  return (ids ?? []).map((id) => {
    const dish = dishMap.value.get(Number(id))
    return {
      id: Number(id),
      name: dish?.name ?? `菜品 #${id}`,
      meta: dish ? [dish.cuisine_type, `¥${Number(dish.price).toFixed(0)}`].filter(Boolean).join(' · ') : '',
    }
  })
}

function toRestaurants(ids) {
  return (ids ?? []).map((id) => {
    const shop = restaurantMap.value.get(Number(id))
    return {
      id: Number(id),
      name: shop?.name ?? `门店 #${id}`,
      meta: shop ? [shop.category, shop.avg_price ? `人均 ¥${Number(shop.avg_price).toFixed(0)}` : ''].filter(Boolean).join(' · ') : '',
    }
  })
}

async function loadCatalog() {
  const dishIds = [...(profile.value?.favorite_dish_ids ?? []), ...(profile.value?.blacklist_dish_ids ?? [])]
  const shopIds = profile.value?.blacklist_restaurant_ids ?? []
  const [dishes, shops] = await Promise.all([
    dishIds.length ? fetchDishes(dishIds) : Promise.resolve([]),
    shopIds.length ? fetchRestaurants(shopIds) : Promise.resolve([]),
  ])
  dishMap.value = new Map((dishes ?? []).map((d) => [Number(d.dish_id), d]))
  restaurantMap.value = new Map((shops ?? []).map((s) => [Number(s.restaurant_id), s]))
}

async function boot() {
  if (!persona.demoUsers.length) await persona.loadDemoUsers()
  await persona.loadProfile()
  await loadCatalog()
}

/** 冰箱入口的数字：件数 / 临期件数（拿不到就显示"—"，不编数据） */
const fridge = ref({ total: null, expiring: null })

async function loadFridgeSummary() {
  try {
    const data = await fetchFridge(persona.userId)
    const items = data.items || []
    fridge.value = {
      total: items.length,
      expiring: items.filter((it) => it.is_expiring_soon).length,
    }
  } catch {
    fridge.value = { total: null, expiring: null }
  }
}

onBeforeUnmount(() => clearTimeout(noticeTimer))

onMounted(async () => {
  await boot()
  await loadFridgeSummary()
  if (token.value) {
    try {
      const me = await fetchMe()
      isAdmin.value = String(me?.role || '').toUpperCase() === 'ADMIN'
    } catch {
      isAdmin.value = false
    }
  }
})
watch(() => persona.userId, async () => {
  budgetDraft.value = null
  await loadCatalog()
  await loadFridgeSummary()
})

async function pickUser(user) {
  if (user.id === persona.userId) {
    showUsers.value = false
    return
  }
  switching.value = true
  try {
    await persona.switchUser(user.id)
    await loadCatalog()
    notice.value = `已切到 ${user.nickname}`
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 1600))
  } finally {
    switching.value = false
    showUsers.value = false
  }
}

/** 忌口胶囊：增删都走 PUT /users/{id}/preferences，成功后用返回的 profile 覆盖本地 */
async function commitVeto(next) {
  saving.value = 'veto'
  try {
    await persona.persistPreferences({ veto_tags: next })
  } catch (e) {
    notice.value = e?.message || '忌口保存失败'
  } finally {
    saving.value = ''
  }
}

function addVeto(tag) {
  const value = String(tag ?? newVeto.value).trim()
  if (!value || vetoTags.value.includes(value)) {
    newVeto.value = ''
    return
  }
  newVeto.value = ''
  commitVeto([...vetoTags.value, value])
}

function removeVeto(tag) {
  commitVeto(vetoTags.value.filter((t) => t !== tag))
}

function onBudgetInput(event) {
  budgetDraft.value = Number(event.target.value)
}

async function onBudgetCommit(event) {
  const value = Number(event.target.value)
  budgetDraft.value = null
  if (!Number.isFinite(value) || value === budget.value) return
  saving.value = 'budget'
  try {
    await persona.persistPreferences({ default_budget: value })
    notice.value = `默认预算改成 ¥${value}`
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 1600))
  } catch (e) {
    notice.value = e?.message || '预算保存失败'
  } finally {
    saving.value = ''
  }
}

async function removeFromBoard(row) {
  const payload =
    tab.value === 'fav'
      ? { target_type: 'DISH', target_id: row.id, list_type: 'FAV', action: 'REMOVE' }
      : tab.value === 'blackdish'
        ? { target_type: 'DISH', target_id: row.id, list_type: 'BLACK', action: 'REMOVE' }
        : { target_type: 'RESTAURANT', target_id: row.id, list_type: 'BLACK', action: 'REMOVE' }
  saving.value = `board-${row.id}`
  try {
    await persona.toggleRedBlack(payload)
    notice.value = `已移出${tab.value === 'fav' ? '红榜' : '黑榜'}：${row.name}`
    (clearTimeout(noticeTimer), noticeTimer = setTimeout(() => (notice.value = ''), 1800))
  } catch (e) {
    notice.value = e?.message || '移出失败'
  } finally {
    saving.value = ''
  }
}

const geneVector = computed(() => {
  const vector = {}
  for (const gene of GENES) vector[gene.key] = Number(profile.value?.base_vector?.[gene.key] ?? 0)
  return vector
})

async function logout() {
  try { await logoutAccount() } catch {}
  clearToken()
  setUserId(1)
  token.value = ''
  window.location.assign('/login')
}

function geneValue(key) {
  return Math.round(Number(profile.value?.base_vector?.[key] ?? 0) * 100)
}
</script>

<template>
  <div class="pf pf--v5">
    <header class="pf-head"><h1>我的</h1><p>你的饮食基因与记录</p></header>

    <section class="account-block">
      <div><span>账号</span><b>{{ token ? (isAdmin ? '已登录 · 管理员' : '已登录') : '演示身份' }}</b></div>
      <div class="account-block__ops">
        <router-link v-if="isAdmin" to="/admin/data">管理后台</router-link>
        <button v-if="token" type="button" @click="logout">退出登录</button>
        <router-link v-else to="/login">登录 / 注册</router-link>
      </div>
    </section>
    <p v-if="persona.error" class="pf__error">{{ persona.error }}</p>

    <!-- 1. 人设卡 + 演示角色切换 -->
    <section class="persona glass-card">
      <div class="persona__main">
        <img v-if="isImageAvatar(profile?.avatar)" class="persona__avatar persona__avatar--img" :src="profile.avatar" alt="头像">
        <span v-else class="persona__avatar" aria-hidden="true">{{ profile?.avatar || '🍚' }}</span>
        <div class="persona__text">
          <h1 class="persona__name">{{ profile?.nickname || '演示用户' }}<button class="persona__edit" type="button" @click="openEdit">编辑</button></h1>
          <p class="persona__title">{{ profile?.persona_title || '还没有人设称号' }}</p>
          <div class="persona__chips"><span>预算 ¥{{ budget }}</span><span v-if="vetoTags.length">忌口 {{ vetoTags.slice(0, 2).join(' / ') }}</span></div>
        </div>
        <!-- 登录后身份锁定：切换 X-User-Id 等于登录了还能看别人的数据，与账号体系冲突。
             未登录时保留演示切换，答辩演示走登录页的快捷账号。 -->
        <button v-if="!token" class="persona__switch" type="button" :aria-expanded="showUsers" @click="showUsers = !showUsers">
          {{ showUsers ? '收起名单' : '🔄 切换室友' }}
        </button>
      </div>

      <ul v-if="showUsers" ref="userListRef" class="roster">
        <li v-for="user in persona.demoUsers" :key="user.id">
          <button
            class="roster__row"
            type="button"
            :data-active="user.id === persona.userId"
            :disabled="switching"
            @click="pickUser(user)"
          >
            <span class="roster__avatar">{{ user.avatar }}</span>
            <span class="roster__text">
              <b>{{ user.nickname }}</b>
              <small>{{ user.persona_title }}</small>
            </span>
            <span class="roster__mark">{{ user.id === persona.userId ? '当前' : '切换' }}</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- 冰箱入口：/m/fridge 只做二级页，不占 Tab 位 -->
    <router-link class="entry glass-card" to="/m/fridge">
      <span class="entry__icon" aria-hidden="true">🧊</span>
      <span class="entry__text">
        <b>虚拟冰箱</b>
        <small v-if="fridge.total !== null">
          {{ fridge.total }} 件食材<template v-if="fridge.expiring"> · {{ fridge.expiring }} 件临期</template>
        </small>
        <small v-else>看看库存与买菜清单</small>
      </span>
      <span class="entry__arrow" aria-hidden="true">›</span>
    </router-link>

    <!-- 房间入口：多人实时划卡，和冰箱一样是二级页 -->
    <router-link class="entry glass-card" to="/m/room">
      <span class="entry__icon" aria-hidden="true">👥</span>
      <span class="entry__text">
        <b>多人干饭房间</b>
        <small>建房或输房间码，和室友一起划卡定菜</small>
      </span>
      <span class="entry__arrow" aria-hidden="true">›</span>
    </router-link>

    <!-- 2. 饮食基因 + 预算 + 忌口 -->
    <section class="block">
      <div class="block__head">
        <h2 class="block__title">饮食基因</h2>
        <button type="button" class="gene-edit-btn" @click="openGeneEditor">{{ neutralVector ? '设置口味' : '编辑' }}</button>
      </div>
      <div class="gene-v5">
        <div class="gene-v5__radar"><V5Radar :vector="geneVector" /></div>
        <div class="gene-v5__side">
          <div><span>预算</span><b>¥{{ budget }}<small>/ 餐</small></b></div>
          <div><span>忌口</span><b>{{ vetoTags.length ? vetoTags.join(' / ') : '无' }}</b></div>
          <div><span>偏好</span><b>{{ geneValue('spicy_level') >= 60 ? '重辣' : '温和' }} · {{ geneValue('soup_level') >= 60 ? '爱汤' : '少汤' }}</b></div>
        </div>
      </div>
      <p v-if="neutralVector" class="gene-edit-hint">当前还是默认中性口味，点「设置口味」选择你的八维偏好，后台画像会同步。</p>
    </section>

    <section class="block">
      <div class="block__head">
        <h2 class="block__title">日常默认预算</h2>
        <span class="block__hint">{{ saving === 'budget' ? '保存中…' : `当前 ¥${budget}` }}</span>
      </div>
      <div class="budget">
        <input
          class="slider-ink range range-xs"
          type="range"
          min="8"
          max="80"
          step="1"
          aria-label="日常默认预算"
          :value="budgetDraft ?? budget"
          @input="onBudgetInput"
          @change="onBudgetCommit"
        />
        <span class="budget__val tabular">¥{{ budgetDraft ?? budget }}</span>
      </div>
    </section>

    <section class="block">
      <div class="block__head">
        <h2 class="block__title">忌口红线</h2>
        <span class="block__hint">命中即一票否决</span>
      </div>
      <ul ref="vetoRef" class="vetoes">
        <li v-for="tag in vetoTags" :key="tag" class="veto">
          <span>{{ tag }}</span>
          <button type="button" :aria-label="`移除忌口 ${tag}`" :disabled="saving === 'veto'" @click="removeVeto(tag)">×</button>
        </li>
        <li class="veto veto--ghost">共 {{ vetoTags.length }} 项</li>
      </ul>
      <div class="veto-add">
        <input v-model="newVeto" type="text" placeholder="加一个忌口，回车确认" @keyup.enter="addVeto()" />
        <button type="button" :disabled="saving === 'veto'" @click="addVeto()">加入</button>
      </div>
      <div class="presets">
        <button v-for="tag in VETO_PRESETS" :key="tag" type="button" :disabled="vetoTags.includes(tag)" @click="addVeto(tag)">
          {{ tag }}
        </button>
      </div>
    </section>

    <!-- 3. 红黑榜 -->
    <section class="block">
      <div class="block__head">
        <h2 class="block__title">美食红黑榜</h2>
        <span class="block__hint">红榜享 1.15x 提权</span>
      </div>

      <div class="tabs" role="tablist">
        <button
          v-for="item in tabs"
          :key="item.key"
          type="button"
          role="tab"
          class="tab"
          :data-active="tab === item.key"
          :aria-selected="tab === item.key"
          @click="tab = item.key"
        >
          {{ item.name }}<span class="tab__count tabular">{{ item.count }}</span>
        </button>
      </div>

      <p v-if="!activeRows.length" class="empty">
        <template v-if="tab === 'fav'">还没有收藏。划卡时点「就吃这个」或卡片上的「加入红榜」。</template>
        <template v-else-if="tab === 'blackdish'">没有拉黑的菜品。拉黑后该菜永久一票否决。</template>
        <template v-else>没有拉黑的门店。拉黑后该店全部菜品不再推荐。</template>
      </p>

      <ul v-else ref="boardRef" class="board">
        <li v-for="row in activeRows" :key="row.id" class="board__row">
          <span class="board__text">
            <b>{{ row.name }}</b>
            <small v-if="row.meta">{{ row.meta }}</small>
            <small v-else class="board__warn">目录里查不到，可能已被删除</small>
          </span>
          <button
            class="board__out"
            type="button"
            :disabled="saving === `board-${row.id}`"
            @click="removeFromBoard(row)"
          >
            移出
          </button>
        </li>
      </ul>
    </section>

    <!-- 4. 战绩 -->
    <section class="block">
      <div class="block__head">
        <h2 class="block__title">干饭战绩</h2>
        <span class="block__hint">帮你少纠结 {{ achievements.meals_logged ?? 0 }} 次</span>
      </div>

      <div class="feats">
        <div class="feat glass-card">
          <span class="feat__label">累计解决吃什么</span>
          <span class="feat__num tabular">{{ achievements.meals_logged ?? 0 }}<small>次</small></span>
        </div>
        <div class="feat glass-card">
          <span class="feat__label">累计花费</span>
          <span class="feat__num tabular">{{ Number(achievements.total_spent ?? 0).toFixed(0) }}<small>元</small></span>
        </div>
        <div class="feat glass-card">
          <span class="feat__label">多人干饭</span>
          <span class="feat__num tabular">{{ achievements.group_rooms_joined ?? 0 }}<small>次</small></span>
        </div>
      </div>

      <div class="split">
        <div class="split__bar" role="img" :aria-label="`外食 ${spend.outPct}%，下厨 ${spend.homePct}%`">
          <span class="split__out" :style="{ width: `${spend.total > 0 ? spend.outPct : 50}%` }" />
        </div>
        <div class="split__legend">
          <span>外卖 <b class="tabular">¥{{ spend.out.toFixed(0) }}</b></span>
          <span>下厨 <b class="tabular">¥{{ spend.home.toFixed(0) }}</b></span>
        </div>
      </div>
    </section>

    <section class="block">
      <div class="block__head"><h2 class="block__title">外观</h2><span class="block__hint">本机</span></div>
      <div class="bg-modes"><button type="button" :class="{ 'is-active': bgMode === 'default' }" @click="bgMode = 'default'">默认水彩</button><button type="button" :class="{ 'is-active': bgMode === 'image' }" @click="bgMode = 'image'">使用图片</button></div>
      <template v-if="bgMode === 'image'">
        <label class="bg-upload">选择背景图<input type="file" accept="image/*" hidden @change="pickBackground" /></label>
        <div v-if="bgUrl" class="bg-preview"><img :src="bgUrl" alt="背景预览" /><span>{{ bgName || '已选背景图' }}</span></div>
        <div class="bg-slider"><span>遮罩</span><input v-model.number="bgOverlay" type="range" min="0" max="80" step="1" /><b>{{ bgOverlay }}%</b></div>
        <div class="bg-text-modes"><button v-for="item in [{ k: 'auto', t: '自动' }, { k: 'light', t: '浅色' }, { k: 'dark', t: '深色' }]" :key="item.k" type="button" :class="{ 'is-active': bgTextMode === item.k }" @click="bgTextMode = item.k">{{ item.t }}</button></div>
      </template>
      <button class="bg-save" type="button" @click="saveBackground">保存背景</button>
    </section>

    <p v-if="notice" class="toast" role="status">{{ notice }}</p>

    <!-- 饮食基因编辑（冷启动） -->
    <div v-if="geneEditing" class="pf-edit" @click.self="geneEditing = false">
      <div class="pf-edit__panel pf-edit__panel--gene">
        <h3 class="pf-edit__title">设置饮食基因</h3>
        <p class="pf-edit__hint">0 = 完全不喜欢，1 = 非常喜欢。保存后会立即影响推荐，并同步到后台用户画像。</p>
        <label v-for="gene in GENES" :key="gene.key" class="gene-row">
          <span class="gene-row__label">{{ gene.name }}</span>
          <input v-model.number="geneDraft[gene.key]" type="range" min="0" max="1" step="0.05" :aria-label="gene.name">
          <b class="tabular">{{ Math.round(Number(geneDraft[gene.key] ?? 0) * 100) }}</b>
        </label>
        <div class="pf-edit__actions">
          <button type="button" @click="geneEditing = false">取消</button>
          <button type="button" class="is-primary" :disabled="geneSaving" @click="saveGenes">{{ geneSaving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 资料编辑 -->
    <div v-if="editing" class="pf-edit" @click.self="editing = false">
      <div class="pf-edit__panel">
        <h3 class="pf-edit__title">编辑资料</h3>
        <label class="pf-edit__field">
          <span>昵称</span>
          <input v-model="editDraft.nickname" type="text" maxlength="32" placeholder="最多 32 个字符">
        </label>
        <div class="pf-edit__field">
          <span>头像</span>
          <div class="pf-edit__avatar">
            <img v-if="isImageAvatar(editDraft.avatar)" :src="editDraft.avatar" alt="头像预览">
            <span v-else>{{ editDraft.avatar || '🍚' }}</span>
          </div>
          <label class="pf-edit__upload">
            <input type="file" accept="image/jpeg,image/png,image/webp" @change="pickAvatar">
            {{ avatarUploading ? '上传中…' : '上传图片' }}
          </label>
          <input v-if="!isImageAvatar(editDraft.avatar)" v-model="editDraft.avatar" type="text" maxlength="4" placeholder="或填一个 emoji / 首字">
          <button v-else class="pf-edit__remove" type="button" @click="editDraft.avatar = ''">移除图片，改回文字头像</button>
        </div>
        <p class="pf-edit__hint">预算与忌口在下方「饮食基因」里改，两者分开保存。</p>
        <div class="pf-edit__actions">
          <button type="button" @click="editing = false">取消</button>
          <button type="button" class="is-primary" :disabled="editSaving" @click="saveProfile">{{ editSaving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pf {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 12px;
}

.pf__error {
  margin: 0;
  border-radius: 1rem;
  padding: 11px 13px;
  font-size: 12px;
  color: var(--on-glass);
  background: rgb(var(--rgb-white) / 0.12);
}

/* 人设卡 */
.persona {
  border-radius: 1.25rem;
  padding: 14px;
}

.entry {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 12px 14px;
  border-radius: 1.125rem;
  color: var(--on-glass);
  text-decoration: none;
}

.entry__icon {
  font-size: 20px;
  line-height: 1;
}

.entry__text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.entry__text b {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--on-glass);
}

.entry__text small {
  font-size: 11px;
  color: var(--on-glass-soft);
}

.entry__arrow {
  flex: 0 0 auto;
  font-size: 18px;
  color: var(--on-glass-dim);
}

.persona__main {
  display: flex;
  align-items: center;
  gap: 11px;
}

.persona__avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  font-size: 24px;
  background: rgb(var(--rgb-white) / 0.12);
}

.persona__text {
  flex: 1 1 auto;
  min-width: 0;
}

.persona__name {
  margin: 0;
  font-size: 17px;
  font-weight: 720;
  color: var(--on-glass);
}

.persona__title {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--on-glass-soft);
}

.persona__switch {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 10.5px;
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.9);
}

.roster {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.roster__row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  border-radius: 0.9rem;
  padding: 9px 10px;
  text-align: left;
  background: rgb(var(--rgb-white) / 0.08);
}

.roster__row[data-active='true'] {
  background: rgb(var(--rgb-white) / 0.16);
}

.roster__avatar {
  font-size: 20px;
}

.roster__text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.roster__text b {
  font-size: 12.5px;
  color: var(--on-glass);
}

.roster__text small {
  font-size: 10px;
  color: var(--on-glass-dim);
}

.roster__mark {
  font-size: 10px;
  color: var(--on-glass-soft);
}

/* 区块骨架 */
.block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.block__title {
  margin: 0;
  font-size: 14px;
  font-weight: 680;
  color: var(--on-glass);
}

.block__hint {
  font-size: 10.5px;
  color: var(--on-glass-dim);
}

/* 八维基因 */
.genes {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 1.125rem;
  padding: 13px 14px;
  background: rgb(var(--rgb-white) / 0.07);
}

.gene {
  display: grid;
  grid-template-columns: 62px 1fr 26px;
  align-items: center;
  gap: 9px;
}

.gene__name {
  font-size: 11px;
  color: var(--on-glass-soft);
}

.gene__track {
  position: relative;
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
}

.gene__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.82);
}

.gene__val {
  font-size: 10px;
  text-align: right;
  color: var(--on-glass-dim);
}

/* 预算 */
.budget {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 1.125rem;
  padding: 12px 14px;
  background: rgb(var(--rgb-white) / 0.07);
}

.budget .slider-ink {
  flex: 1 1 auto;
  min-width: 0;
}

.budget__val {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--on-glass);
}

/* 忌口 */
.vetoes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.veto {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  padding: 4px 6px 4px 10px;
  font-size: 11.5px;
  color: var(--on-glass);
  background: rgb(var(--rgb-white) / 0.14);
}

.veto button {
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 12px;
  line-height: 1;
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.75);
}

.veto--ghost {
  padding: 4px 10px;
  font-size: 10.5px;
  color: var(--on-glass-dim);
  background: transparent;
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.16);
}

.veto-add {
  display: flex;
  gap: 8px;
}

.veto-add input {
  flex: 1 1 auto;
  min-width: 0;
  border-radius: 0.8rem;
  padding: 8px 11px;
  font-size: 12px;
  color: var(--on-glass);
  background: rgb(var(--rgb-white) / 0.08);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.14);
}

.veto-add input::placeholder {
  color: var(--on-glass-dim);
}

.veto-add button {
  flex: 0 0 auto;
  border-radius: 0.8rem;
  padding: 0 12px;
  font-size: 11.5px;
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.86);
}

.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.presets button {
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 10.5px;
  color: var(--on-glass-soft);
  box-shadow: inset 0 0 0 1px rgb(var(--rgb-white) / 0.16);
}

.presets button:disabled {
  opacity: 0.32;
}

/* 红黑榜 */
.tabs {
  display: flex;
  gap: 6px;
}

.tab {
  flex: 1 1 0;
  border-radius: 999px;
  padding: 6px 4px;
  font-size: 11px;
  color: var(--on-glass-soft);
  background: rgb(var(--rgb-white) / 0.07);
}

.tab[data-active='true'] {
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.9);
}

.tab__count {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.72;
}

.empty {
  margin: 0;
  border-radius: 1.125rem;
  padding: 16px 14px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--on-glass-soft);
  background: rgb(var(--rgb-white) / 0.07);
}

.board {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.board__row {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 1rem;
  padding: 9px 11px;
  background: rgb(var(--rgb-white) / 0.08);
}

.board__text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.board__text b {
  font-size: 12.5px;
  color: var(--on-glass);
}

.board__text small {
  font-size: 10px;
  color: var(--on-glass-dim);
}

.board__warn {
  color: rgb(var(--rgb-white) / 0.45);
}

.board__out {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 5px 11px;
  font-size: 10.5px;
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.86);
}

.board__out:disabled {
  opacity: 0.5;
}

/* 战绩 */
.feats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.feat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 1.125rem;
  padding: 11px 12px;
}

.feat__label {
  font-size: 10px;
  color: var(--on-glass-soft);
}

.feat__num {
  font-size: 19px;
  font-weight: 700;
  color: var(--on-glass);
}

.feat__num small {
  margin-left: 2px;
  font-size: 10px;
  font-weight: 500;
  color: var(--on-glass-dim);
}

.split {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-radius: 1.125rem;
  padding: 12px 14px;
  background: rgb(var(--rgb-white) / 0.07);
}

.split__bar {
  position: relative;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.16);
}

.split__out {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.88);
}

.split__legend {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--on-glass-soft);
}

.split__legend b {
  color: var(--on-glass);
}

.toast {
  position: fixed;
  left: 50%;
  bottom: calc(78px + env(safe-area-inset-bottom, 0px));
  z-index: 20;
  transform: translateX(-50%);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 11.5px;
  white-space: nowrap;
  color: var(--color-ink);
  background: rgb(var(--rgb-white) / 0.92);
  box-shadow: 0 10px 24px rgb(var(--rgb-black) / 0.32);
}

.bg-modes { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; padding: 3px; border-radius: 12px; background: rgb(var(--rgb-v5-ink) / .06); }
.bg-modes button { height: 32px; border-radius: 9px; font-size: 10.5px; color: var(--on-glass-soft); }
.bg-modes button.is-active { background: rgb(var(--rgb-v5-paper-strong) / .82); color: var(--v5-ink); }
.bg-upload { display: flex; align-items: center; justify-content: center; height: 36px; margin-top: 10px; border-radius: 10px; border: 1px dashed rgb(var(--rgb-v5-ink) / .22); font-size: 10px; color: var(--on-glass-soft); cursor: pointer; }
.bg-preview { display: flex; align-items: center; gap: 9px; margin-top: 9px; font-size: 9px; color: var(--on-glass-soft); }
.bg-preview img { width: 44px; height: 44px; border-radius: 9px; object-fit: cover; }
.bg-slider { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: 9px; color: var(--on-glass-soft); }
.bg-slider input { flex: 1; accent-color: var(--v5-ink); }
.bg-text-modes { display: flex; gap: 5px; margin-top: 9px; }
.bg-text-modes button { padding: 5px 8px; border-radius: 8px; border: 1px solid rgb(var(--rgb-v5-ink) / .14); font-size: 8.5px; color: var(--on-glass-soft); }
.bg-text-modes button.is-active { background: var(--v5-ink); color: var(--v5-paper-strong); }
.bg-save { width: 100%; height: 40px; margin-top: 12px; border-radius: 12px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 11px; font-weight: 600; }


.pf--v5 { gap: 14px; }
.pf-head h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -.04em; color: var(--on-glass); }
.pf-head p { margin: 6px 0 0; font-size: 10px; color: var(--on-glass-soft); }
.pf--v5 .persona { padding: 14px; border-radius: 20px; background: rgb(var(--rgb-v5-paper-strong) / .58); border: 1px solid rgb(var(--rgb-white) / .82); box-shadow: 0 10px 28px rgb(var(--rgb-v5-shadow) / .06); }
.pf--v5 .persona__avatar { width: 58px; height: 58px; font-size: 20px; }
.pf--v5 .persona__name { font-size: 17px; font-weight: 600; }
.persona__chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.persona__chips span { padding: 3px 6px; border-radius: 6px; background: rgb(var(--rgb-v5-ink) / .055); font-size: 8.5px; color: var(--on-glass-soft); }
.gene-v5 { display: grid; grid-template-columns: 1fr 128px; gap: 8px; align-items: center; }
.gene-v5__radar { width: 100%; height: 176px; display: flex; align-items: center; justify-content: center; }
.gene-v5__radar > * { width: 176px; height: 176px; }
.gene-v5__side { display: flex; flex-direction: column; gap: 9px; }
.gene-v5__side div { display: flex; flex-direction: column; gap: 2px; }
.gene-v5__side span { font-size: 8.5px; color: var(--on-glass-dim); }
.gene-v5__side b { font-size: 11px; font-weight: 600; color: var(--on-glass); }
.gene-v5__side small { font-size: 8px; font-weight: 400; color: var(--on-glass-soft); }


.account-block { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 14px; background: rgb(var(--rgb-v5-paper-strong) / .5); border: 1px solid rgb(var(--rgb-white) / .78); font-size: 9.5px; color: var(--on-glass-soft); }
.account-block div { display: flex; flex-direction: column; gap: 2px; }
.account-block b { font-size: 10.5px; font-weight: 600; color: var(--on-glass); }
.account-block button, .account-block a { padding: 5px 9px; border-radius: 8px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 9px; text-decoration: none; }
/* 必须带 .account-block 前缀：上面 `.account-block div` 的特异性更高，会把它压回竖排 */
.account-block .account-block__ops { display: flex; flex-direction: row; align-items: center; gap: 6px; }


/* 资料编辑弹层：必须写在本组件的 scoped 样式里。
   v5-home-exact.css 只被 HomeV5Exact 以 scoped 引入，Profile 拿不到那份样式，
   之前写在那边导致弹层没有 fixed 定位、直接摊在页面流里。 */
.gene-edit-btn {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .18);
  background: transparent;
  color: var(--v5-ink);
  font-size: 9.5px;
}
.gene-edit-hint {
  margin: 8px 0 0;
  font-size: 9px;
  line-height: 1.6;
  color: var(--v5-muted);
}
.pf-edit__panel--gene { max-height: 82vh; overflow-y: auto; }
.gene-row {
  display: grid;
  grid-template-columns: 62px 1fr 30px;
  gap: 8px;
  align-items: center;
  margin-bottom: 9px;
  font-size: 10px;
  color: var(--v5-muted);
}
.gene-row input { width: 100%; accent-color: var(--v5-ink); }
.gene-row b { text-align: right; font-weight: 500; color: var(--v5-ink); }

.pf-edit {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(var(--rgb-v5-shadow) / .38);
  backdrop-filter: blur(6px);
}
.pf-edit__panel {
  width: 100%;
  max-width: 320px;
  padding: 18px 18px 14px;
  border-radius: 18px;
  background: var(--v5-paper-strong);
  box-shadow: 0 24px 60px rgb(var(--rgb-v5-shadow) / .22);
}
.pf-edit__title { margin: 0 0 12px; font-size: 15px; font-weight: 600; color: var(--v5-ink); }
.pf-edit__field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; font-size: 10px; color: var(--v5-muted); }
.pf-edit__field input {
  height: 36px;
  padding: 0 10px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .14);
  border-radius: 9px;
  background: var(--color-white);
  color: var(--v5-ink);
  font: inherit;
  font-size: 12px;
  outline: none;
}
.pf-edit__hint { margin: 0 0 12px; font-size: 9.5px; color: var(--v5-faint); line-height: 1.6; }
.pf-edit__actions { display: flex; gap: 8px; }
.pf-edit__actions button {
  flex: 1;
  height: 38px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .14);
  border-radius: 11px;
  background: var(--color-white);
  color: var(--v5-ink);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.pf-edit__actions .is-primary { background: var(--v5-ink); color: var(--v5-paper-strong); border-color: var(--v5-ink); font-weight: 600; }
.persona__edit {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 9px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .18);
  border-radius: 999px;
  background: rgb(var(--rgb-v5-paper-strong) / .7);
  color: var(--v5-muted);
  font: inherit;
  font-size: 9.5px;
  cursor: pointer;
}
.persona__edit:hover { border-color: rgb(var(--rgb-v5-ink) / .4); color: var(--v5-ink); }

/* 头像支持图片：与 emoji 共用同一个圆形容器 */
.persona__avatar--img {
  object-fit: cover;
  background: rgb(var(--rgb-v5-ink) / .06);
}

.pf-edit__avatar {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  margin-bottom: 8px;
  border-radius: 50%;
  background: rgb(var(--rgb-v5-ink) / .06);
  font-size: 24px;
  overflow: hidden;
}
.pf-edit__avatar img { width: 100%; height: 100%; object-fit: cover; }

.pf-edit__upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  margin-bottom: 8px;
  padding: 0 12px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .18);
  border-radius: 9px;
  background: var(--color-white);
  color: var(--v5-ink);
  font-size: 11px;
  cursor: pointer;
}
.pf-edit__upload:hover { border-color: rgb(var(--rgb-v5-ink) / .4); }
.pf-edit__upload input { display: none; }

/* 头像支持图片：与 emoji 共用同一个圆形容器 */
.persona__avatar--img {
  object-fit: cover;
  background: rgb(var(--rgb-v5-ink) / .06);
}

.pf-edit__avatar {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  margin-bottom: 8px;
  border-radius: 50%;
  background: rgb(var(--rgb-v5-ink) / .06);
  font-size: 24px;
  overflow: hidden;
}
.pf-edit__avatar img { width: 100%; height: 100%; object-fit: cover; }

.pf-edit__upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  margin-bottom: 8px;
  padding: 0 12px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .18);
  border-radius: 9px;
  background: var(--color-white);
  color: var(--v5-ink);
  font-size: 11px;
  cursor: pointer;
}
.pf-edit__upload:hover { border-color: rgb(var(--rgb-v5-ink) / .4); }
.pf-edit__upload input { display: none; }

.pf-edit__remove {
  align-self: flex-start;
  margin-bottom: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--v5-faint);
  font: inherit;
  font-size: 9.5px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.pf-edit__remove {
  align-self: flex-start;
  margin-bottom: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--v5-faint);
  font: inherit;
  font-size: 9.5px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
</style>
