<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AdminShell from '../../components/admin/AdminShell.vue'
import { fetchAlgoSettings, saveAlgoSettings } from '../../api/admin'
import { errorText } from '../../utils/errorText'

/**
 * 算法参数配置。
 * 保存后后端写 system_settings 并热加载运行期缓存，推荐接口立刻按新参数打分——
 * 不是「存起来给人看」的假配置。
 */
const form = reactive({})
const fields = ref([])
const defaults = ref({})
const overridden = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

// dirty 必须与「最近一次已保存的值」比较，而不是与出厂默认值比较。
// 否则把参数调离默认值后保存成功，状态栏仍会显示"有未保存的改动"，自相矛盾。
const saved = ref({})
const dirty = computed(() =>
  fields.value.some(
    (field) =>
      Number(form[field.key]) !==
      Number(saved.value[field.key] ?? defaults.value[field.key]),
  ),
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const body = await fetchAlgoSettings()
    fields.value = body.fields || []
    defaults.value = body.defaults || {}
    saved.value = { ...(body.current || {}) }
    overridden.value = Boolean(body.overridden)
    Object.entries(body.current || {}).forEach(([key, value]) => {
      form[key] = value
    })
  } catch (err) {
    error.value = errorText(err) || '参数读取失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const body = await saveAlgoSettings({ ...form })
    Object.entries(body.current || {}).forEach(([key, value]) => {
      form[key] = value
    })
    saved.value = { ...(body.current || {}) }
    overridden.value = true
    notice.value = '已保存并立即生效：下一次推荐请求就会用新参数打分'
  } catch (err) {
    error.value = errorText(err) || '保存失败'
  } finally {
    saving.value = false
  }
}

function resetDefaults() {
  Object.entries(defaults.value).forEach(([key, value]) => {
    form[key] = value
  })
  notice.value = '已填回默认值，点「保存参数」才会写入'
}

onMounted(load)
</script>

<template>
  <AdminShell title="算法参数" subtitle="改完保存立即生效，无需重启服务；每次修改都会写入审计日志">
    <p v-if="loading" class="admin-empty">正在读取参数…</p>

    <template v-else>
      <section class="algo-grid">
        <label v-for="field in fields" :key="field.key" class="algo-field">
          <span class="algo-field__label">{{ field.label }}</span>
          <span class="algo-field__key">{{ field.key }}</span>
          <input v-model.number="form[field.key]" type="range" min="0" max="1" step="0.05">
          <output>{{ Number(form[field.key] ?? 0).toFixed(2) }}</output>
        </label>
      </section>

      <p v-if="notice" class="admin-notice" role="status">{{ notice }}</p>
      <p v-if="error" class="admin-form-error" role="alert">{{ error }}</p>

      <footer class="algo-actions">
        <span class="algo-hint">
          {{ overridden ? '当前参数已被后台覆盖（非默认值）' : '当前使用默认参数' }}
          <template v-if="dirty"> · 有未保存的改动</template>
        </span>
        <button class="admin-button" type="button" @click="resetDefaults">填回默认</button>
        <button class="admin-button admin-button--primary" type="button" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存参数' }}
        </button>
      </footer>
    </template>
  </AdminShell>
</template>

<style scoped>
.algo-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.algo-field {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 10px;
  padding: 14px 16px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.09);
  border-radius: 12px;
  background: var(--admin-surface);
}
.algo-field__label { color: var(--admin-ink); font-size: 12.5px; font-weight: 500; }
.algo-field__key { color: var(--admin-faint); font-family: "Cascadia Mono", Consolas, monospace; font-size: 10px; }
.algo-field input[type="range"] { grid-column: 1 / 2; width: 100%; accent-color: var(--admin-accent); }
.algo-field output {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
  align-self: center;
  color: var(--admin-ink);
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.algo-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
}
.algo-hint { margin-right: auto; color: var(--admin-faint); font-size: 11px; }
</style>
