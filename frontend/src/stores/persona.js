import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchDemoUsers, fetchProfile, savePreferences, updateRedBlackList } from '../api'
import { getUserId, setUserId } from '../api/client'

/**
 * 演示角色（答辩一键切换）+ 当前用户资料。
 * v2.3.1 已删除 /auth/login，身份就是 X-User-Id 请求头。
 */
export const usePersonaStore = defineStore('persona', () => {
  const userId = ref(getUserId())
  const demoUsers = ref([])
  const profile = ref(null)
  const loading = ref(false)
  const error = ref('')
  // 角色切换时递增；晚到的旧请求结果不得覆盖新角色数据
  let profileToken = 0

  const nickname = computed(
    () => profile.value?.nickname ?? demoUsers.value.find((u) => u.id === userId.value)?.nickname ?? '演示用户',
  )
  const avatar = computed(
    () => profile.value?.avatar ?? demoUsers.value.find((u) => u.id === userId.value)?.avatar ?? '🍚',
  )

  async function loadDemoUsers() {
    try {
      const data = await fetchDemoUsers()
      // demo-list 是公开的全局角色列表，与当前身份无关
      demoUsers.value = Array.isArray(data) ? data : (data?.users ?? [])
    } catch (err) {
      error.value = err.message
    }
  }

  async function loadProfile() {
    const token = ++profileToken
    const targetId = userId.value
    loading.value = true
    try {
      const data = await fetchProfile(targetId)
      if (token !== profileToken || targetId !== userId.value) return
      profile.value = data
      error.value = ''
    } catch (err) {
      if (token !== profileToken || targetId !== userId.value) return
      error.value = err.message
    } finally {
      if (token === profileToken) loading.value = false
    }
  }

  async function switchUser(id) {
    const next = Number(id)
    if (!Number.isInteger(next) || next <= 0) {
      throw new Error(`非法用户身份：${id}`)
    }
    if (next === userId.value) return
    setUserId(next)
    userId.value = next
    profile.value = null
    error.value = ''
    profileToken += 1
    await loadProfile()
  }

  async function persistPreferences(patch) {
    const targetId = userId.value
    const data = await savePreferences(targetId, patch)
    if (targetId === userId.value) {
      profile.value = { ...(profile.value ?? {}), ...(data ?? {}) }
    }
    return data
  }

  async function toggleRedBlack(payload) {
    const targetId = userId.value
    const data = await updateRedBlackList(targetId, payload)
    if (targetId === userId.value) {
      profile.value = { ...(profile.value ?? {}), ...(data ?? {}) }
    }
    return data
  }

  return {
    userId,
    demoUsers,
    profile,
    loading,
    error,
    nickname,
    avatar,
    loadDemoUsers,
    loadProfile,
    switchUser,
    persistPreferences,
    toggleRedBlack,
  }
})
