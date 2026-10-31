<script setup>
/**
 * 多人干饭房间（批次 3 后半）。
 *
 * 协议见 MASTER_SPEC.md 第五章「多人房间 WebSocket 实时协议」：
 *   ws://{host}/ws/room/{room_code}/{user_id}
 *   前置：必须先 POST /rooms/{code}/join，否则默认握手直接 HTTP 403
 *   （v2.3.2 契约，审查 F11 之后才改成 403；旧实现是 accept 后 1008 关闭）
 *   上行：START_SWIPING（仅房主）、SUBMIT_VOTE
 *   下行：ROOM_STATE（连上先发，用于刷新/断线恢复现场）/ MEMBER_SYNC /
 *         START_SWIPING / PROGRESS_UPDATE / CONSENSUS_REVEAL
 *
 * 状态只有 WAITING / SWIPING / FINISHED（规格第 200 行）。倒计时以服务端
 * 下发的 deadline_at 为准，本地只做展示，免得两边各算一套。
 *
 * 交互取舍：15 秒是**一局**的倒计时（规格原文），不是每张卡 15 秒。
 * 到点没划的卡按 TIMEOUT 计票（后端共识算法里 TIMEOUT = 60 分），
 * 所以倒计时结束不会卡住，也不会把没表态当成反对。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import confetti from 'canvas-confetti'
import { gsap } from 'gsap'
import QRCode from 'qrcode'
import { createRoom, joinRoom, fetchRoom, roomSocketUrl } from '../../api'
import { usePersonaStore } from '../../stores/persona'
import { useModeStore } from '../../stores/mode'
import { useAlgoStore } from '../../stores/algo'
import { tokens } from '../../utils/theme'
import SwipeCardDeck from '../../components/SwipeCardDeck.vue'
import V5Radar from '../../components/V5Radar.vue'
import LottieIcon from '../../components/LottieIcon.vue'

const route = useRoute()
const router = useRouter()
const persona = usePersonaStore()
const mode = useModeStore()
const algo = useAlgoStore()

const MATCH_AXES = [
  { key: 'taste', label: '口味' },
  { key: 'weather', label: '天气' },
  { key: 'budget', label: '预算' },
  { key: 'freshness', label: '新鲜' },
  { key: 'status', label: '状态' },
]

const VOTE_BUTTONS = [
  { type: 'SUPER_LIKE', label: '超想吃', hint: '上划' },
  { type: 'LIKE', label: '想吃', hint: '右划' },
  { type: 'PASS', label: '都行', hint: '左划' },
  { type: 'VETO', label: '不吃', hint: '下划' },
]

const stage = ref('landing') // landing | lobby | swiping | revealed
const error = ref('')
const busy = ref(false)

const createMode = ref('OUT_DINING')
const joinCode = ref('')

const room = ref(null)
const members = ref([])
const candidates = ref([])
const votes = ref({})
const deckRef = ref(null)
const myProgress = computed(
  () => candidates.value.filter((d) => d.dish_id in votes.value).length,
)
const total = computed(() => candidates.value.length)
/* 已投过的卡不再回到卡组：重连/刷新后也从 my_votes 还原，不会重复投 */
const deckCards = computed(() =>
  candidates.value.filter((d) => !(d.dish_id in votes.value)),
)
const current = computed(() => deckCards.value[0] || null)

const seconds = ref(0)
const swipeTotal = ref(15)
const reveal = ref(null)
const socket = ref(null)
const socketState = ref('closed')

const inviteLink = ref('')
const qrDataUrl = ref('')
const inviteWarning = ref('')
const copied = ref(false)

let countdown = null
let revealTl = null
let copiedTimer = null
let reconnectTimer = null
const reconnectAttempts = ref(0)
let closingByUs = false
let revealedPlayed = false

const isHost = computed(() => room.value && room.value.host_user_id === persona.userId)

/**
 * 群组满意度经常落在 100 分上线附近，直接拿分数当百分比会五条全满。
 * 这里把 2~5 名的分数映射到「最低分 38%」~「最高分 100%」，让差距看得出来；
 * 分数完全相同时统一 100%，不制造假差异。
 */
const winnerRow = computed(() => {
  const dishes = reveal.value?.report?.dishes ?? []
  const id = reveal.value?.winner?.dish_id
  return dishes.find((row) => row.dish_id === id) ?? dishes[0] ?? null
})
const vetoedCount = computed(() => (reveal.value?.report?.dishes ?? []).filter((row) => row.masked_by_veto).length)
function memberName(userId) {
  return members.value.find((m) => m.user_id === userId)?.nickname || `成员 ${userId}`
}

function barWidth(row) {
  const list = reveal.value?.report?.dishes?.slice(0, 5) || []
  const scores = list.map((item) => Number(item.group_score) || 0)
  const top = Math.max(...scores, 0)
  const bottom = Math.min(...scores, top)
  const span = top - bottom
  if (span <= 0) return '100%'
  const ratio = (Number(row.group_score) - bottom) / span
  return `${Math.round(38 + ratio * 62)}%`
}
const roomCode = computed(() => room.value?.room_code || '')

function resetRound() {
  candidates.value = []
  votes.value = {}
  reveal.value = null
  revealedPlayed = false
  seconds.value = 0
  swipeTotal.value = 15
  inviteLink.value = ''
  qrDataUrl.value = ''
  inviteWarning.value = ''
  if (countdown) {
    clearInterval(countdown)
    countdown = null
  }
}

/**
 * 倒计时只做展示：真正的截止时间在服务端（deadline_at），
 * 这里用 remaining_ms 起算，再按本地时钟走，避免"两边各算一套"。
 */
function startCountdown(remainingMs, totalSeconds = 15) {
  const deadline = Date.now() + Math.max(0, Number(remainingMs) || 0)
  swipeTotal.value = Math.max(1, Number(totalSeconds) || 15)
  if (countdown) clearInterval(countdown)
  const tick = () => {
    seconds.value = Math.max(0, Math.round((deadline - Date.now()) / 1000))
    if (seconds.value <= 0 && countdown) {
      clearInterval(countdown)
      countdown = null
    }
  }
  tick()
  countdown = setInterval(tick, 250)
}

/** 建房预算：用当前模式拿到的预算，没设就传 null（后端不限） */
function budgetForRoom() {
  const value = Number(mode.budget)
  return Number.isFinite(value) && value > 0 ? value : null
}

function stopCountdown() {
  if (countdown) {
    clearInterval(countdown)
    countdown = null
  }
}

function closeSocket() {
  closingByUs = true
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket.value) {
    try {
      socket.value.close()
    } catch {
      /* 已经断开就算了 */
    }
    socket.value = null
  }
  socketState.value = 'closed'
  nextTick(() => {
    closingByUs = false
  })
}

/**
 * 把快照铺到页面上。刷新、断线重连、第二个人进房都走这里，
 * 所以三阶段（WAITING / SWIPING / FINISHED）都必须能从快照恢复。
 */
function applySnapshot(snapshot) {
  if (!snapshot) return
  room.value = { ...(room.value || {}), ...snapshot }
  members.value = snapshot.members || members.value
  if (Array.isArray(snapshot.candidates)) candidates.value = snapshot.candidates
  if (snapshot.my_votes && typeof snapshot.my_votes === 'object') {
    votes.value = Object.fromEntries(
      Object.entries(snapshot.my_votes).map(([dishId, vote]) => [Number(dishId), vote]),
    )
  }
  if (snapshot.status === 'WAITING') {
    stage.value = 'lobby'
    return
  }
  if (snapshot.status === 'SWIPING') {
    stage.value = 'swiping'
    startCountdown(snapshot.remaining_ms, snapshot.swipe_seconds)
    return
  }
  if (snapshot.status === 'FINISHED') {
    showReveal({
      winner: snapshot.winner_dish,
      winner_dish_id: snapshot.winner_dish_id,
      report: snapshot.consensus_report,
      has_consensus: snapshot.has_consensus,
    })
  }
}

function showReveal(payload) {
  reveal.value = payload
  stage.value = 'revealed'
  stopCountdown()
  if (!revealedPlayed) {
    revealedPlayed = true
    playReveal()
  }
}

function handleMessage(message) {
  const type = message.type
  if (type === 'ROOM_STATE') {
    applySnapshot(message.snapshot)
    return
  }
  if (type === 'MEMBER_SYNC') {
    members.value = message.members || []
    if (message.status === 'WAITING') stage.value = 'lobby'
    if (message.status === 'SWIPING' && stage.value !== 'swiping') stage.value = 'swiping'
    return
  }
  if (type === 'START_SWIPING') {
    // 重连时服务端会重发 START_SWIPING；此时 ROOM_STATE 已带回本人票，
    // 不能清空 votes，否则已投的卡会重新出现、进度也会倒退。
    if (Array.isArray(message.candidates) && message.candidates.length) {
      const previous = new Map(candidates.value.map((item) => [item.dish_id, item]))
      candidates.value = message.candidates.map((item) => ({
        ...item,
        my_match: item.my_match || previous.get(item.dish_id)?.my_match,
      }))
    }
    stage.value = 'swiping'
    revealedPlayed = false
    const remaining = message.remaining_ms ?? (message.swipe_seconds || 15) * 1000
    startCountdown(remaining, message.swipe_seconds)
    return
  }
  if (type === 'PROGRESS_UPDATE') {
    members.value = members.value.map((m) =>
      m.user_id === message.user_id ? { ...m, progress: message.progress?.[m.user_id] ?? m.progress } : m,
    )
    return
  }
  if (type === 'CONSENSUS_REVEAL') {
    showReveal(message)
    return
  }
  if (type === 'ERROR') {
    error.value = message.detail || '服务端说这条指令不合法'
    // 投票被拒时回滚乐观更新：onVote 已经把票写进 votes 并让卡片飞走，
    // 不回滚会出现"界面显示投了、服务端按超时计"的错位，且无法重投。
    // 后端 ERROR 现在带 dish_id / rejected（group_room.py 同步改）。
    if (message.rejected && typeof message.dish_id === 'number') {
      const next = { ...votes.value }
      delete next[message.dish_id]
      votes.value = next
      nextTick(() => deckRef.value?.reset())
    }
  }
}

/** 断线后按 0.5s → 4s 退避重连；服务端连上即推 ROOM_STATE。 */
function scheduleReconnect() {
  if (reconnectTimer || reconnectAttempts.value >= 10) return
  const delay = Math.min(5000, 500 * 2 ** reconnectAttempts.value)
  reconnectAttempts.value += 1
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    if (!room.value || stage.value === 'landing') return
    connect()
  }, delay)
}

function connect() {
  if (!roomCode.value) return
  closeSocket()
  const url = roomSocketUrl(roomCode.value, persona.userId)
  const ws = new WebSocket(url)
  socket.value = ws
  socketState.value = 'connecting'
  ws.onopen = () => {
    socketState.value = 'open'
    reconnectAttempts.value = 0
    if (error.value === '实时连接断了，正在重连…') error.value = ''
  }
  ws.onmessage = (event) => {
    try {
      handleMessage(JSON.parse(event.data))
    } catch {
      /* 非 JSON 一律忽略 */
    }
  }
  ws.onclose = () => {
    if (socket.value !== ws) return
    socketState.value = 'closed'
    socket.value = null
    if (!closingByUs && room.value && stage.value !== 'landing') {
      error.value = '实时连接断了，正在重连…'
      scheduleReconnect()
    }
  }
  ws.onerror = () => {
    socketState.value = 'error'
  }
}

function send(payload) {
  if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return false
  socket.value.send(JSON.stringify(payload))
  return true
}

/** 进入房间：快照 + 邀请入口 + 实时连接，三阶段共用。 */
function enterRoom(snapshot) {
  error.value = ''
  room.value = snapshot
  members.value = snapshot?.members || []
  candidates.value = snapshot?.candidates || []
  votes.value = Object.fromEntries(
    Object.entries(snapshot?.my_votes || {}).map(([dishId, vote]) => [Number(dishId), vote]),
  )
  applySnapshot(snapshot)
  rememberCode(snapshot?.room_code)
  prepareInvite(snapshot?.room_code)
  connect()
}

async function doCreate() {
  busy.value = true
  error.value = ''
  try {
    // F10：把沙盒调过的参数随建房快照下去，结算用快照，不是读 DB
    const snapshot = await createRoom(
      createMode.value,
      budgetForRoom(),
      algo.dirty ? { ...algo.overrides } : null,
      mode.campus,
    )
    enterRoom(snapshot)
    stage.value = 'lobby'
  } catch (err) {
    error.value = err?.message || '房间没建成'
  } finally {
    busy.value = false
  }
}

async function doJoin(codeArg) {
  const code = String(codeArg ?? joinCode.value).trim()
  if (!/^\d{6}$/.test(code)) {
    error.value = '房间码是 6 位数字，看看是不是抄错了一位'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const snapshot = await joinRoom(code, mode.campus)
    enterRoom(snapshot)
    stage.value = 'lobby'
  } catch (err) {
    // join 只允许 WAITING：SWIPING/FINISHED 的恢复读取改走 GET + ROOM_STATE
    const recovered = await restore(code, { silent: true, allowJoin: false })
    if (!recovered) error.value = err?.message || '进不去这个房间'
  } finally {
    busy.value = false
  }
}

/**
 * 刷新 / 重进 / 断线的恢复入口：先用 GET 读快照（仅成员可读）。
 * 403 = 还没加入：房间仍 WAITING 时走 join；已开局则明确拒绝，不伪装成功。
 */
async function restore(code, { silent = false, allowJoin = true } = {}) {
  if (!code) return null
  try {
    const snapshot = await fetchRoom(code)
    joinCode.value = code
    enterRoom(snapshot)
    return snapshot
  } catch (err) {
    if (err?.status === 403 && allowJoin) {
      try {
        const snapshot = await joinRoom(code, mode.campus)
        joinCode.value = code
        enterRoom(snapshot)
        stage.value = 'lobby'
        return snapshot
      } catch (joinErr) {
        if (!silent) {
          error.value =
            joinErr?.status === 409
              ? joinErr.message || '这个房间是另一个校区的'
              : joinErr?.message || '这一局已经开始，等下一局吧'
        }
        return null
      }
    }
    if (!silent) {
      error.value = err?.status === 404 ? '房间不存在或已经结束' : err?.message || '读取房间失败'
    }
    return null
  }
}

/** 把房间码写进地址栏：刷新/重进直接回到这一局（F05 的前端那一半） */
function rememberCode(code) {
  if (!code) return
  if (route.query.code !== code) router.replace({ query: { ...route.query, code } })
}

function isLoopbackHost() {
  return ['localhost', '127.0.0.1', '::1'].includes(location.hostname)
}

/**
 * 邀请链接必须指向另一台设备能打开的地址。
 * 本机用 localhost 打开时，向 dev server 的 /__lan 要局域网地址；
 * 拿不到就明确提示"只有本机能访问"，不把 localhost 二维码当成可用邀请。
 */
async function lanBase() {
  if (!isLoopbackHost()) return { base: location.origin, lan: true }
  try {
    const response = await fetch('/__lan', { headers: { Accept: 'application/json' } })
    if (response.ok) {
      const data = await response.json()
      const addresses = Array.isArray(data?.addresses) ? data.addresses : []
      const preferred = addresses.find((address) =>
        /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(String(address)),
      )
      if (preferred) return { base: `http://${preferred}:${location.port}`, lan: true }
    }
  } catch {
    /* 生产构建没有 dev helper，退回本机地址并给出提示 */
  }
  return { base: location.origin, lan: false }
}

async function prepareInvite(code) {
  inviteWarning.value = ''
  qrDataUrl.value = ''
  if (!code) return
  const { base, lan } = await lanBase()
  inviteLink.value = `${base}/m/room?code=${code}`
  const palette = tokens()
  try {
    qrDataUrl.value = await QRCode.toDataURL(inviteLink.value, {
      margin: 1,
      width: 240,
      errorCorrectionLevel: 'M',
      color: { dark: palette.ink, light: palette.white },
    })
  } catch {
    inviteWarning.value = '二维码生成失败，可以直接复制邀请链接'
  }
  if (!lan) {
    inviteWarning.value = '当前是 localhost，二维码只有本机能打开；换局域网地址打开本页后再让室友扫'
  }
}

async function copyInvite() {
  if (!inviteLink.value) return
  try {
    await navigator.clipboard.writeText(inviteLink.value)
  } catch {
    return
  }
  copied.value = true
  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copied.value = false
  }, 1600)
}

function startSwiping() {
  if (!send({ type: 'START_SWIPING' })) error.value = '连接还没就绪'
}

/** 按钮与拖拽共用同一套飞出/上报逻辑，避免两条路径口径不一。 */
function cast(voteType) {
  if (stage.value !== 'swiping') {
    error.value = '这一局已经结束了，不能再改票'
    return
  }
  if (!current.value) return
  if (seconds.value <= 0) {
    error.value = '15 秒已经到点了，这局不能再投票'
    return
  }
  onVote({ dish: current.value, voteType })
}

function onVote({ dish, voteType }) {
  if (stage.value !== 'swiping') {
    error.value = '这一局已经结束了，不能再改票'
    nextTick(() => deckRef.value?.reset())
    return
  }
  const sent = send({
    type: 'SUBMIT_VOTE',
    dish_id: dish.dish_id,
    vote_type: voteType,
  })
  if (!sent) {
    error.value = '实时连接断开，这一票没发出去'
    nextTick(() => deckRef.value?.reset())
    connect()
    return
  }
  error.value = ''
  votes.value = { ...votes.value, [dish.dish_id]: voteType }
}

/** 后台切回：服务端截止/结算可能已经推进，先取快照再确保连接。 */
async function onVisibility() {
  if (document.visibilityState !== 'visible') return
  if (!room.value || stage.value === 'landing') return
  if (!socket.value || socket.value.readyState > WebSocket.OPEN) {
    connect()
    return
  }
  try {
    const snapshot = await fetchRoom(roomCode.value)
    applySnapshot(snapshot)
  } catch {
    /* 网络仍不稳就等 ws 重连推快照 */
  }
}

/**
 * 揭晓动效只动位移，不用 opacity:0 起手。
 * 原因：后台标签页里 Chrome 会节流 rAF，gsap 的 from 补间可能一直停在起始值，
 * 于是整张卡停在 transparent，用户什么都看不到（实测发生过）。
 * 只补位移，动画没跑也照样可见。
 */
function playReveal() {
  requestAnimationFrame(() => {
    const shell = document.querySelector('.reveal__card')
    const rows = document.querySelectorAll('.reveal__row')
    if (revealTl) revealTl.kill()
    revealTl = gsap.timeline({ defaults: { ease: 'power3.out' } })
    if (shell) {
      revealTl.fromTo(shell, { y: 14, scale: 0.97 }, { y: 0, scale: 1, duration: 0.55 }, 0)
    }
    if (rows.length) {
      revealTl.fromTo(rows, { y: 12 }, { y: 0, duration: 0.4, stagger: 0.05 }, 0.28)
    }

  })
}

function backToLanding() {
  closeSocket()
  resetRound()
  room.value = null
  members.value = []
  stage.value = 'landing'
}

onMounted(async () => {
  // 房间页用当前模式做默认建房模式，省一次选择
  createMode.value = mode.modeType === 'HOME_COOKING' ? 'HOME_COOKING' : 'OUT_DINING'
  document.addEventListener('visibilitychange', onVisibility)
  // 地址栏带 ?code= 说明是刷新/重进：先 GET 快照恢复，开局后 join 会被拒
  const code = String(route.query.code || '').trim()
  if (/^\d{6}$/.test(code)) {
    joinCode.value = code
    await restore(code)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  closeSocket()
  stopCountdown()
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (copiedTimer) clearTimeout(copiedTimer)
  if (revealTl) revealTl.kill()
})
</script>

<template>
  <div
    class="room"
    :data-stage="stage"
    :data-room-code="roomCode"
    :data-socket="socketState"
    :data-reconnect-attempts="reconnectAttempts"
  >
    <header v-if="stage !== 'revealed'" class="room__head">
      <p class="room__eyebrow">多人干饭房间</p>
      <h1 class="room__title">一起决定吃什么</h1>
      <p class="room__sub">
        <template v-if="stage === 'landing'">建房等室友进来，或输入房间码加入</template>
        <template v-else-if="stage === 'lobby'">把房间码发给室友，人齐了由房主开团</template>
        <template v-else-if="stage === 'swiping'">15 秒内把想吃的划出来，没划的算「都行」</template>
        <template v-else>大家的口味已经算完了，看结果</template>
      </p>
    </header>

    <p v-if="error" class="hint hint--warn">{{ error }}</p>

    <!-- 落地：建房 / 加入 -->
    <section v-if="stage === 'landing'" class="landing">
      <div class="glass-card landing__card">
        <h2 class="landing__title">开一间新房</h2>
        <div class="seg">
          <button
            v-for="opt in [{ k: 'OUT_DINING', t: '外食' }, { k: 'HOME_COOKING', t: '下厨' }]"
            :key="opt.k"
            type="button"
            class="seg__item"
            :data-active="createMode === opt.k"
            @click="createMode = opt.k"
          >
            {{ opt.t }}
          </button>
        </div>
        <button type="button" class="btn-ink" :disabled="busy" @click="doCreate">
          {{ busy ? '正在开房…' : '创建房间' }}
        </button>
      </div>

      <div class="glass-card landing__card">
        <h2 class="landing__title">加入室友的房间</h2>
        <input
          v-model="joinCode"
          class="field"
          type="text"
          maxlength="6"
          placeholder="输入 6 位房间码"
          @keyup.enter="doJoin"
        />
        <button type="button" class="btn-ghost-ink" :disabled="busy" @click="doJoin">加入</button>
      </div>
    </section>

    <!-- 等待厅 -->
    <section v-else-if="stage === 'lobby'" class="lobby" data-stage="lobby">
      <div class="glass-card lobby__code">
        <span class="lobby__label">房间码</span>
        <b class="lobby__digits tabular" data-room-code>{{ roomCode }}</b>
        <span class="lobby__mode">{{ room?.mode_type === 'OUT_DINING' ? '外食' : '下厨' }}</span>
      </div>

      <div class="glass-card invite">
        <div class="invite__head">
          <h2 class="invite__title">邀请室友</h2>
          <span class="invite__hint">扫码或打开链接进房</span>
        </div>
        <div class="invite__body">
          <img
            v-if="qrDataUrl"
            class="invite__qr"
            :src="qrDataUrl"
            :data-qr-payload="inviteLink"
            alt="房间邀请二维码"
          />
          <div v-else class="invite__qr invite__qr--empty">二维码生成中</div>
          <div class="invite__side">
            <p class="invite__link" :title="inviteLink" data-invite-link>{{ inviteLink }}</p>
            <button type="button" class="btn-ghost-ink" @click="copyInvite">
              {{ copied ? '已复制' : '复制邀请链接' }}
            </button>
          </div>
        </div>
        <p v-if="inviteWarning" class="hint hint--warn" data-invite-warning>{{ inviteWarning }}</p>
      </div>

      <ul class="members">
        <li v-for="m in members" :key="m.user_id" class="member glass-card--matte" :data-member-id="m.user_id">
          <span class="member__avatar">{{ m.avatar }}</span>
          <span class="member__name">
            {{ m.nickname }}
            <b v-if="m.is_host" class="member__host">房主</b>
          </span>
          <span class="member__state">{{ m.user_id === persona.userId ? '你' : '已就位' }}</span>
        </li>
      </ul>

      <button v-if="isHost" type="button" class="btn-ink" data-action="start-swiping" @click="startSwiping">
        开始划卡
      </button>
      <p v-else class="hint" data-action="wait-host">等房主开团…</p>
    </section>

    <!-- 划卡 -->
    <section v-else-if="stage === 'swiping'" class="swiping" data-stage="swiping">
      <div class="timer glass-card">
        <div class="timer__bar">
          <span
            class="timer__fill"
            :style="{ width: `${Math.max(0, Math.min(100, (seconds / swipeTotal) * 100))}%` }"
          />
        </div>
        <div class="timer__meta">
          <span class="tabular" data-seconds>{{ Math.max(0, seconds) }}s</span>
          <span class="tabular" data-progress>{{ myProgress }}/{{ total }}</span>
        </div>
      </div>

      <article v-if="current" class="room-card" :data-dish-id="current.dish_id">
        <div class="room-card__head"><span>DISH · 15s</span><span>{{ current.cuisine_type || '家常菜' }}</span></div>
        <div class="room-card__radar"><V5Radar :vector="current.feature_vector" /></div>
        <h2 class="room-card__name">{{ current.name }}</h2>
        <p class="room-card__meta"><span v-if="current.restaurant_name">{{ current.restaurant_name }} · </span>¥{{ current.price }}</p>
        <div v-if="current.my_match" class="my-match">
          <div class="my-match__head"><span>你的匹配</span><span>五维</span></div>
          <div v-for="axis in MATCH_AXES" :key="axis.key" class="my-match__row">
            <span>{{ axis.label }}</span>
            <span class="my-match__track"><i :style="{ width: `${Math.max(2, Math.min(100, current.my_match[axis.key]))}%` }" /></span>
            <b>{{ Math.round(current.my_match[axis.key]) }}</b>
          </div>
        </div>
      </article>
      <p v-if="!current" class="hint">这一局你已经划完了，等别人…</p>

      <div class="votes">
        <button
          v-for="btn in VOTE_BUTTONS"
          :key="btn.type"
          type="button"
          class="vote"
          :class="`vote--${btn.type.toLowerCase()}`"
          :data-vote="btn.type"
          :disabled="!current || seconds <= 0"
          @click="cast(btn.type)"
        >
          <b>{{ btn.label }}</b>
          <small>{{ btn.hint }}</small>
        </button>
      </div>

      <ul class="progress">
        <li v-for="m in members" :key="m.user_id" class="progress__row">
          <span class="progress__name">{{ m.avatar }} {{ m.nickname }}</span>
          <span class="progress__val tabular" :data-member-progress="m.user_id">{{ m.progress ?? 0 }}/{{ total }}</span>
        </li>
      </ul>
    </section>

    <!-- 揭晓 -->
    <section v-else class="reveal" data-stage="revealed" :data-has-consensus="String(reveal?.has_consensus !== false)">
      <header class="rv-head"><p class="rv-eyebrow">CONSENSUS</p><h1>大家最终选了这碗</h1><p class="rv-sub">{{ reveal?.has_consensus === false ? '这局没有形成共识' : '投票结束 · 结果如下' }}</p></header>

      <article class="reveal__card rv-winner">
        <div class="rv-radar"><V5Radar :vector="reveal?.winner?.feature_vector" /></div>
        <div class="rv-winner__copy">
          <p class="rv-label">{{ reveal?.has_consensus === false ? 'NO RESULT' : 'WINNER' }}</p>
          <h2 class="reveal__name" data-winner-dish-id>{{ reveal?.winner?.name || '没有可推荐的菜' }}</h2>
          <p v-if="reveal?.winner" class="rv-meta">{{ reveal.winner.restaurant_name || '家常菜' }} · ¥{{ reveal.winner.price }}</p>
          <span class="rv-score">{{ reveal?.report?.winner_group_score ?? 0 }}<small>群组满意度</small></span>
        </div>
      </article>

      <div v-if="reveal?.has_consensus !== false" class="rv-metrics">
        <div><b>{{ winnerRow?.mean_satisfaction?.toFixed(0) ?? '—' }}</b><span>平均满意度</span></div>
        <div><b>{{ winnerRow?.least_misery?.toFixed(0) ?? '—' }}</b><span>最低成员</span></div>
        <div><b>{{ vetoedCount }}</b><span>被否决候选</span></div>
      </div>

      <section v-if="winnerRow?.members?.length" class="rv-section">
        <div class="rv-section__head"><h3>每个人接受吗</h3><span>满意度 / 100</span></div>
        <div class="rv-members">
          <div v-for="m in winnerRow.members" :key="m.user_id" class="rv-member" :class="{ 'is-low': m.satisfaction < 70 }">
            <span class="rv-avatar">{{ memberName(m.user_id).slice(0, 1) }}</span>
            <span class="rv-name">{{ memberName(m.user_id) }}</span>
            <span class="rv-track"><i :style="{ width: `${Math.max(2, Math.min(100, m.satisfaction))}%` }" /></span>
            <b>{{ m.satisfaction.toFixed(0) }}</b>
          </div>
        </div>
      </section>

      <section class="rv-section">
        <div class="rv-section__head"><h3>为什么是它</h3><span>{{ reveal?.has_consensus === false ? '没有共识' : '不是最高平均分' }}</span></div>
        <p class="rv-why">{{ reveal?.has_consensus === false ? '每个候选都至少被一个人否决，这局按“没有共识”结算。' : '它不是平均分最高的候选，但最低成员满意度最高。混合策略没有为了多数人牺牲少数人，所以最终胜出。' }}</p>
        <div v-if="vetoedCount" class="rv-veto"><span>×</span><p>有 {{ vetoedCount }} 个候选被成员否决，已从共识计算中排除。</p></div>
      </section>

      <div class="rv-actions">
        <button type="button" class="rv-primary" @click="backToLanding">就吃这个 <span>→</span></button>
        <button type="button" class="rv-secondary" @click="backToLanding">再开一局</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.room {
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: var(--on-glass);
}

.room__eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--on-glass-dim);
}

.room__title {
  margin: 0;
  font-size: 25px;
  font-weight: 700;
  line-height: 1.3;
}

.room__sub {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--on-glass-soft);
}

.landing {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.landing__card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 1.125rem;
}

.landing__title {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}

.seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 3px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.08);
}

.seg__item {
  height: 34px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 13px;
  cursor: pointer;
}

.seg__item[data-active='true'] {
  background: rgb(var(--rgb-ink) / 0.92);
  color: var(--color-white);
  font-weight: 650;
}

.field {
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 0.85rem;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: rgb(var(--rgb-white) / 0.08);
  color: var(--on-glass);
  font-size: 13px;
  letter-spacing: 0.18em;
  text-align: center;
}

.field::placeholder {
  letter-spacing: normal;
  color: var(--on-glass-dim);
}

.lobby {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.invite {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 1.125rem;
}

.invite__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.invite__title {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}

.invite__hint {
  font-size: 10.5px;
  color: var(--on-glass-dim);
}

.invite__body {
  display: flex;
  align-items: center;
  gap: 12px;
}

.invite__qr {
  flex: 0 0 auto;
  width: 120px;
  height: 120px;
  padding: 4px;
  border-radius: 0.75rem;
  background: var(--color-white);
}

.invite__qr--empty {
  display: grid;
  place-items: center;
  font-size: 10.5px;
  color: var(--color-ink);
}

.invite__side {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.invite__link {
  margin: 0;
  font-size: 10.5px;
  line-height: 1.4;
  color: var(--on-glass-soft);
  word-break: break-all;
}

.room-deck {
  flex: 0 0 auto;
  height: 300px;
}

.room-deck :deep(.deck) {
  height: 100%;
  max-height: none;
}

.room-deck :deep(.deck__top) > .card {
  height: 100%;
}

.lobby__code {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 1.125rem;
}

.lobby__label {
  font-size: 11px;
  color: var(--on-glass-dim);
}

.lobby__digits {
  font-size: 24px;
  letter-spacing: 0.22em;
  font-weight: 700;
}

.lobby__mode {
  margin-left: auto;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
  font-size: 10.5px;
  color: var(--on-glass-soft);
}

.members {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.member {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 12px;
  border-radius: 0.95rem;
}

.member__avatar {
  font-size: 17px;
}

.member__name {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.member__host {
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--on-glass);
  color: var(--color-ink);
  font-size: 9.5px;
}

.member__state {
  font-size: 10.5px;
  color: var(--on-glass-dim);
}

.swiping {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timer {
  padding: 9px 12px;
  border-radius: 0.95rem;
}

.timer__bar {
  height: 4px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.16);
  overflow: hidden;
}

.timer__fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--on-glass);
  transition: width 0.9s linear;
}

.timer__meta {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 11px;
  color: var(--on-glass-soft);
}

.card {
  overflow: hidden;
  border-radius: 1.25rem;
}

.card__shot {
  position: relative;
  height: 148px;
  background: rgb(var(--rgb-white) / 0.06);
}

.card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card__placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 11.5px;
  color: var(--on-glass-dim);
}

.card__body {
  padding: 12px 14px 14px;
}

.card__name {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
}

.card__meta {
  margin: 5px 0 0;
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

.card__sep {
  margin: 0 5px;
  color: var(--on-glass-dim);
}

.votes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.vote {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 2px;
  border-radius: 0.85rem;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: transparent;
  color: var(--on-glass-soft);
  cursor: pointer;
}

.vote b {
  font-size: 12.5px;
  font-weight: 650;
}

.vote small {
  font-size: 9px;
  color: var(--on-glass-dim);
}

.vote--super_like {
  background: var(--on-glass);
  border-color: transparent;
  color: var(--color-ink);
}

.vote--super_like small {
  color: rgb(var(--rgb-ink) / 0.6);
}

.vote--veto {
  border-style: dashed;
}

.vote:disabled {
  opacity: 0.5;
  cursor: default;
}

.progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}

.progress__row {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

.reveal {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.reveal__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px;
  border-radius: 1.35rem;
  text-align: center;
}

.reveal__art {
  margin-bottom: 2px;
}

.reveal__label {
  margin: 0;
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--on-glass-dim);
}

.reveal__name {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.reveal__meta {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: var(--on-glass-soft);
}

.reveal__score {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--on-glass-soft);
}

.reveal__list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.reveal__row {
  display: grid;
  grid-template-columns: 52px 1fr 46px;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--on-glass-soft);
}

.reveal__bar {
  height: 5px;
  border-radius: 999px;
  background: rgb(var(--rgb-white) / 0.14);
  overflow: hidden;
}

.reveal__fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--on-glass);
}

.reveal__val {
  text-align: right;
}

.reveal__actions {
  padding-bottom: 4px;
}

.btn-ink {
  min-height: 42px;
  border: 0;
  border-radius: 999px;
  background: var(--on-glass);
  color: var(--color-ink);
  font-size: 13.5px;
  font-weight: 650;
  cursor: pointer;
}

.btn-ink:disabled {
  opacity: 0.55;
  cursor: default;
}

.btn-ghost-ink {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--on-glass-line, rgb(var(--rgb-white) / 0.22));
  background: transparent;
  color: var(--on-glass-soft);
  font-size: 12.5px;
  cursor: pointer;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--on-glass-soft);
}

.hint--warn {
  color: var(--on-glass);
}

.my-match { margin-top: 9px; padding-top: 8px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .1); }
.my-match__head { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 8px; color: var(--on-glass-dim); }
.my-match__row { display: grid; grid-template-columns: 28px 1fr 24px; gap: 7px; align-items: center; margin-bottom: 4px; font-size: 8px; color: var(--on-glass-soft); }
.my-match__track { height: 4px; border-radius: 2px; background: rgb(var(--rgb-v5-ink) / .1); overflow: hidden; }
.my-match__track i { display: block; height: 100%; border-radius: 2px; background: var(--v5-accent); }
.my-match__row b { text-align: right; font-size: 8px; font-weight: 500; color: var(--on-glass-soft); }

</style>

<style scoped>
.room-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 14px 14px;
  border-radius: 24px;
  background: rgb(var(--rgb-v5-paper-strong) / .58);
  border: 1px solid rgb(var(--rgb-white) / .82);
  box-shadow: 0 12px 32px rgb(var(--rgb-v5-shadow) / .07);
}
.room-card__head { display: flex; justify-content: space-between; font-size: 8.5px; letter-spacing: .12em; color: var(--on-glass-dim); }
.room-card__radar { height: 280px; display: flex; align-items: center; justify-content: center; margin: 2px -4px 0; }
.room-card__radar > * { width: 280px; height: 280px; max-width: 100%; }
.room-card__name { margin: 0 0 3px; font-size: 22px; font-weight: 600; letter-spacing: -.04em; color: var(--on-glass); }
.room-card__meta { margin: 0; font-size: 9.5px; color: var(--on-glass-soft); }
@media (max-height: 760px) {
  .room-card__radar { height: 220px; }
  .room-card__radar > * { width: 220px; height: 220px; }
}

.my-match { margin-top: 9px; padding-top: 8px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .1); }
.my-match__head { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 8px; color: var(--on-glass-dim); }
.my-match__row { display: grid; grid-template-columns: 28px 1fr 24px; gap: 7px; align-items: center; margin-bottom: 4px; font-size: 8px; color: var(--on-glass-soft); }
.my-match__track { height: 4px; border-radius: 2px; background: rgb(var(--rgb-v5-ink) / .1); overflow: hidden; }
.my-match__track i { display: block; height: 100%; border-radius: 2px; background: var(--v5-accent); }
.my-match__row b { text-align: right; font-size: 8px; font-weight: 500; color: var(--on-glass-soft); }

</style>

<style scoped>
.rv-head { padding-top: 2px; }
.rv-eyebrow { margin: 0 0 4px; font-size: 9px; letter-spacing: .16em; color: var(--on-glass-dim); }
.rv-head h1 { margin: 0; font-size: 25px; font-weight: 600; letter-spacing: -.04em; color: var(--on-glass); }
.rv-sub { margin: 6px 0 0; font-size: 10px; color: var(--on-glass-soft); }
.rv-winner { display: grid; grid-template-columns: 132px 1fr; gap: 12px; align-items: center; padding: 13px; border-radius: 22px; background: rgb(var(--rgb-v5-paper-strong) / .58); border: 1px solid rgb(var(--rgb-white) / .82); box-shadow: 0 12px 30px rgb(var(--rgb-v5-shadow) / .06); }
.rv-radar { width: 132px; height: 132px; }
.rv-radar > * { width: 132px; height: 132px; }
.rv-label { margin: 0 0 3px; font-size: 8.5px; letter-spacing: .14em; color: var(--v5-accent); }
.rv-winner .reveal__name { margin: 0 0 3px; font-size: 21px; font-weight: 600; letter-spacing: -.03em; color: var(--on-glass); }
.rv-meta { margin: 0; font-size: 9.5px; color: var(--on-glass-soft); }
.rv-score { display: inline-flex; align-items: baseline; gap: 4px; margin-top: 8px; padding: 4px 8px; border-radius: 8px; background: rgb(var(--rgb-v5-ink) / .055); font-size: 15px; font-weight: 600; color: var(--on-glass); }
.rv-score small { font-size: 8px; font-weight: 400; color: var(--on-glass-soft); }
.rv-metrics { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; padding: 11px 0; border-top: 1px solid rgb(var(--rgb-v5-ink) / .12); border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .12); }
.rv-metrics div { display: flex; flex-direction: column; gap: 2px; }
.rv-metrics b { font-size: 20px; font-weight: 600; color: var(--on-glass); }
.rv-metrics span { font-size: 8.5px; color: var(--on-glass-dim); }
.rv-section { padding: 12px 0; border-bottom: 1px solid rgb(var(--rgb-v5-ink) / .1); }
.rv-section:last-of-type { border-bottom: 0; }
.rv-section__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 9px; }
.rv-section__head h3 { margin: 0; font-size: 11px; font-weight: 600; color: var(--on-glass); }
.rv-section__head span { font-size: 8.5px; color: var(--on-glass-dim); }
.rv-members { display: flex; flex-direction: column; gap: 8px; }
.rv-member { display: grid; grid-template-columns: 24px 54px 1fr 28px; gap: 7px; align-items: center; }
.rv-avatar { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 8.5px; }
.rv-name { font-size: 9px; color: var(--on-glass-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rv-track { height: 4px; border-radius: 2px; background: rgb(var(--rgb-v5-ink) / .1); overflow: hidden; }
.rv-track i { display: block; height: 100%; border-radius: 2px; background: var(--v5-ink); }
.rv-member.is-low .rv-track i { background: var(--v5-accent); }
.rv-member b { text-align: right; font-size: 9px; font-weight: 500; color: var(--on-glass-soft); }
.rv-why { margin: 0; font-size: 10px; line-height: 1.65; color: var(--on-glass-soft); }
.rv-veto { display: flex; gap: 8px; margin-top: 8px; padding: 8px 9px; border-radius: 9px; background: rgb(var(--rgb-v5-accent) / .08); }
.rv-veto span { color: var(--v5-accent); font-size: 10px; }
.rv-veto p { margin: 0; font-size: 8.5px; line-height: 1.5; color: var(--on-glass-soft); }
.rv-actions { display: flex; flex-direction: column; gap: 7px; padding-top: 4px; }
.rv-primary { height: 44px; border-radius: 14px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; padding: 0 15px; }
.rv-primary span { font-size: 16px; opacity: .7; }
.rv-secondary { padding: 4px 0; font-size: 9.5px; color: var(--on-glass-soft); text-decoration: underline; text-underline-offset: 3px; }

.my-match { margin-top: 9px; padding-top: 8px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .1); }
.my-match__head { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 8px; color: var(--on-glass-dim); }
.my-match__row { display: grid; grid-template-columns: 28px 1fr 24px; gap: 7px; align-items: center; margin-bottom: 4px; font-size: 8px; color: var(--on-glass-soft); }
.my-match__track { height: 4px; border-radius: 2px; background: rgb(var(--rgb-v5-ink) / .1); overflow: hidden; }
.my-match__track i { display: block; height: 100%; border-radius: 2px; background: var(--v5-accent); }
.my-match__row b { text-align: right; font-size: 8px; font-weight: 500; color: var(--on-glass-soft); }

</style>
