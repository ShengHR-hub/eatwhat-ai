<script setup>
import { errorText } from '../utils/errorText'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { fetchMe, loginAccount, registerAccount } from '../api'
import { getToken, setToken, setUserId } from '../api/client'

const router = useRouter()
const mode = ref('login')
const username = ref('')
const password = ref('')
const nickname = ref('')
const busy = ref(false)
const error = ref('')
const hasToken = ref(Boolean(getToken()))
const role = ref('')

const isAdmin = () => role.value === 'ADMIN'

/**
 * 演示账号快捷填充。
 * 登录后身份就锁定了，演示时靠这里一键切换（而不是在「我的」页面里切 X-User-Id，
 * 那样等于登录了还能看别人的数据，身份体系自相矛盾）。
 * 只填用户名、不填密码：口令一旦写进源码就会随构建产物一起分发，任何人解包
 * dist/APK 都能搜到管理员口令（独立审查 2026-10-31 P0）。密码由使用者手动输入。
 */
const DEMO_ACCOUNTS = [
  { username: 'testuser', label: '管理员', tag: 'ADMIN' },
  { username: 'chuan_yu', label: '四川小熊猫', tag: '麻辣' },
  { username: 'yue_cai', label: '广州双马尾', tag: '清淡' },
  { username: 'chi_tu', label: '山西老醋坛', tag: '面食' },
  { username: 'jian_shen', label: '河北热露露', tag: '咸香' },
]

function fillDemo(account) {
  mode.value = 'login'
  username.value = account.username
  password.value = ''
  error.value = ''
}

onMounted(async () => {
  if (!hasToken.value) return
  try {
    const user = await fetchMe()
    role.value = String(user?.role || '').toUpperCase()
  } catch {
    role.value = ''
  }
})

async function submit() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  if (mode.value === 'register' && password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  busy.value = true
  try {
    const payload = mode.value === 'register'
      ? { username: username.value.trim(), password: password.value, nickname: nickname.value.trim() }
      : { username: username.value.trim(), password: password.value }
    const result = mode.value === 'register' ? await registerAccount(payload) : await loginAccount(payload)
    setToken(result.token)
    setUserId(result.user.user_id)
    // 管理员直接落到后台，普通用户回移动端；权限本身仍由后端 require_admin 判定
    const admin = String(result.user?.role || '').toUpperCase() === 'ADMIN'
    window.location.assign(admin ? '/admin/data' : '/m/home')
  } catch (err) {
    error.value = errorText(err) || '登录失败'
  } finally {
    busy.value = false
  }
}

function goHome() {
  router.push(isAdmin() ? '/admin/data' : '/m/home')
}
</script>

<template>
  <main class="login-stage">
    <section class="login-card">
      <p class="login-eyebrow">EATWHAT · ACCOUNT</p>
      <h1>食刻</h1>
      <p class="login-sub">{{ mode === 'login' ? '登录后保存你的饮食记录' : '创建一个新账号' }}</p>

      <div v-if="hasToken" class="login-done">
        <p>{{ isAdmin() ? '你已经以管理员身份登录。' : '你已经登录。' }}</p>
        <button type="button" @click="goHome">{{ isAdmin() ? '进入管理后台' : '回到首页' }}</button>
      </div>

      <template v-else>
        <div class="login-tabs">
          <button type="button" :class="{ 'is-active': mode === 'login' }" @click="mode = 'login'; error = ''">登录</button>
          <button type="button" :class="{ 'is-active': mode === 'register' }" @click="mode = 'register'; error = ''">注册</button>
        </div>

        <form class="login-form" @submit.prevent="submit">
          <label><span>用户名</span><input v-model="username" type="text" autocomplete="username" maxlength="32" placeholder="3–32 个字符" /></label>
          <label v-if="mode === 'register'"><span>昵称</span><input v-model="nickname" type="text" autocomplete="nickname" maxlength="32" placeholder="可选" /></label>
          <label><span>密码</span><input v-model="password" type="password" autocomplete="current-password" maxlength="72" placeholder="至少 6 位" /></label>
          <p v-if="error" class="login-error">{{ error }}</p>
          <button class="login-submit" type="submit" :disabled="busy">{{ busy ? '请稍候…' : mode === 'login' ? '登录' : '注册并登录' }}</button>
        </form>

        <div class="login-demo">
          <p class="login-demo__title">演示账号 · 点一下自动填用户名</p>
          <div class="login-demo__list">
            <button v-for="account in DEMO_ACCOUNTS" :key="account.username" type="button" @click="fillDemo(account)">
              <b>{{ account.label }}</b>
              <small>{{ account.tag }}</small>
            </button>
          </div>
          <p class="login-demo__hint">密码请手动输入（口令不写进源码，避免随产物泄露）</p>
        </div>

        <p class="login-note">不接手机号和微信，仅用户名 + 密码。未登录仍可使用演示身份。</p>
      </template>
    </section>
  </main>
</template>

<style scoped>
.login-stage {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--v5-bg);
  color: var(--v5-ink);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.login-card {
  width: 100%;
  max-width: 340px;
  padding: 24px;
  border-radius: 26px;
  background: rgb(var(--rgb-v5-paper-strong) / .78);
  border: 1px solid rgb(var(--rgb-white) / .9);
  box-shadow: 0 24px 70px rgb(var(--rgb-v5-shadow) / .14);
}
.login-eyebrow { margin: 0 0 6px; font-size: 9px; letter-spacing: .16em; color: var(--v5-faint); }
.login-card h1 { margin: 0; font-size: 28px; font-weight: 600; letter-spacing: -.04em; }
.login-sub { margin: 6px 0 18px; font-size: 10.5px; color: var(--v5-muted); }
.login-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; padding: 3px; border-radius: 12px; background: rgb(var(--rgb-v5-ink) / .06); }
.login-tabs button { height: 32px; border-radius: 9px; font-size: 10.5px; color: var(--v5-muted); }
.login-tabs button.is-active { background: var(--v5-paper-strong); color: var(--v5-ink); box-shadow: 0 1px 3px rgb(var(--rgb-v5-shadow) / .08); }
.login-form { display: flex; flex-direction: column; gap: 11px; margin-top: 16px; }
.login-form label { display: flex; flex-direction: column; gap: 5px; font-size: 9px; color: var(--v5-muted); }
.login-form input { height: 38px; padding: 0 11px; border-radius: 10px; border: 1px solid rgb(var(--rgb-v5-ink) / .14); background: rgb(var(--rgb-white) / .55); font-size: 12px; color: var(--v5-ink); outline: none; }
.login-form input:focus { border-color: rgb(var(--rgb-v5-ink) / .45); }
.login-error { margin: 0; font-size: 9.5px; color: var(--v5-danger); }
.login-submit { height: 42px; margin-top: 3px; border-radius: 12px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 12px; font-weight: 600; }
.login-submit:disabled { opacity: .55; }
.login-demo { margin-top: 16px; padding-top: 13px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .08); }
.login-demo__title { margin: 0 0 8px; font-size: 9px; letter-spacing: .1em; color: var(--v5-faint); }
.login-demo__hint { margin: 8px 0 0; font-size: 9px; line-height: 1.5; color: var(--v5-faint); }
.login-demo__list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.login-demo__list button {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 7px 8px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .1);
  border-radius: 9px;
  background: rgb(var(--rgb-white) / .5);
  text-align: left;
  cursor: pointer;
}
.login-demo__list button:hover { border-color: rgb(var(--rgb-v5-ink) / .28); background: rgb(var(--rgb-white) / .8); }
.login-demo__list b { font-size: 10.5px; font-weight: 600; color: var(--v5-ink); }
.login-demo__list small { font-size: 8.5px; color: var(--v5-faint); }

.login-demo { margin-top: 16px; padding-top: 13px; border-top: 1px solid rgb(var(--rgb-v5-ink) / .08); }
.login-demo__title { margin: 0 0 8px; font-size: 9px; letter-spacing: .1em; color: var(--v5-faint); }
.login-demo__list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.login-demo__list button {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 7px 8px;
  border: 1px solid rgb(var(--rgb-v5-ink) / .1);
  border-radius: 9px;
  background: rgb(var(--rgb-white) / .5);
  text-align: left;
  cursor: pointer;
}
.login-demo__list button:hover { border-color: rgb(var(--rgb-v5-ink) / .28); background: rgb(var(--rgb-white) / .8); }
.login-demo__list b { font-size: 10.5px; font-weight: 600; color: var(--v5-ink); }
.login-demo__list small { font-size: 8.5px; color: var(--v5-faint); }

.login-note { margin: 14px 0 0; font-size: 8.5px; line-height: 1.55; color: var(--v5-faint); }
.login-done { padding: 14px 0; font-size: 11px; color: var(--v5-muted); }
.login-done button { margin-top: 10px; height: 36px; padding: 0 14px; border-radius: 10px; background: var(--v5-ink); color: var(--v5-paper-strong); font-size: 10px; }
</style>
