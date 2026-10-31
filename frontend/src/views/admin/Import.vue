<script setup>
import { computed, reactive, ref } from 'vue'
import AdminShell from '../../components/admin/AdminShell.vue'
import { commitImport, previewImport } from '../../api/admin'
import { errorText } from '../../utils/errorText'

/**
 * 数据导入（CSV / XLSX → 菜品）。
 *
 * 两步式：先预览拿列名与前 8 行，人工确认字段映射后再提交。
 * 不直接「上传即入库」——字段错位写进去比不写更难收拾。
 * 只导入菜品：门店涉及校区归属与坐标校验，口径未定前不做半成品。
 */
const file = ref(null)
const preview = ref(null)
const mapping = reactive({})
const busy = ref(false)
const error = ref('')
const result = ref(null)

const columns = computed(() => preview.value?.columns || [])
const targetFields = computed(() => preview.value?.target_fields || [])
const canCommit = computed(() => Boolean(mapping.name && preview.value?.total_rows))

async function onFile(event) {
  const picked = event.target.files?.[0]
  if (!picked) return
  file.value = picked
  preview.value = null
  result.value = null
  error.value = ''
  busy.value = true
  try {
    const body = await previewImport(picked)
    preview.value = body
    Object.keys(mapping).forEach((key) => delete mapping[key])
    // 列名与字段名一致的自动映射，减少手工点击
    body.target_fields.forEach((field) => {
      const hit = body.columns.find((column) => column.toLowerCase() === field.key.toLowerCase())
      if (hit) mapping[field.key] = hit
    })
  } catch (err) {
    error.value = errorText(err) || '文件解析失败'
  } finally {
    busy.value = false
  }
}

async function submit() {
  if (!canCommit.value) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await commitImport({
      mapping: { ...mapping },
      rows: preview.value.rows,
      filename: preview.value.filename,
    })
  } catch (err) {
    error.value = errorText(err) || '导入失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AdminShell title="数据导入" subtitle="CSV / XLSX → 菜品；先预览确认字段映射，再写入数据库">
    <section class="import-upload">
      <label class="import-drop">
        <input type="file" accept=".csv,.xlsx,.xlsm" @change="onFile">
        <b>{{ busy ? '解析中…' : '选择 CSV 或 XLSX 文件' }}</b>
        <small>首行为表头；单文件不超过 8MB；导入的菜品会标记为合成数据（is_synthetic=1）</small>
      </label>
    </section>

    <p v-if="error" class="admin-form-error" role="alert">{{ error }}</p>

    <template v-if="preview">
      <section class="import-map">
        <h2 class="import-map__title">字段映射</h2>
        <div class="import-map__grid">
          <label v-for="field in targetFields" :key="field.key" class="import-map__item">
            <span>{{ field.label }}<em v-if="field.required">必填</em></span>
            <select v-model="mapping[field.key]">
              <option value="">不导入</option>
              <option v-for="column in columns" :key="column" :value="column">{{ column }}</option>
            </select>
          </label>
        </div>
      </section>

      <section class="import-preview">
        <header class="import-preview__head">
          <b>{{ preview.filename }}</b>
          <span>共 {{ preview.total_rows }} 行 · 预览前 {{ preview.preview_rows?.length || 0 }} 行</span>
        </header>
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th v-for="column in columns" :key="column">{{ column }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in preview.preview_rows || []" :key="index">
                <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer class="import-actions">
        <span class="import-hint">
          同名菜品会被跳过（按 name 去重）；导入后可在「数据管理」里逐条打标
        </span>
        <button class="admin-button admin-button--primary" type="button" :disabled="!canCommit || busy" @click="submit">
          {{ busy ? '写入中…' : `确认导入 ${preview.total_rows} 行` }}
        </button>
      </footer>
    </template>

    <p v-if="result" class="admin-notice" role="status">
      导入完成：新增 {{ result.created }} 条，跳过 {{ result.skipped }} 条
    </p>
  </AdminShell>
</template>

<style scoped>
.import-upload { margin-bottom: 16px; }
.import-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 20px;
  border: 1px dashed rgb(var(--rgb-admin-ink) / 0.2);
  border-radius: 14px;
  background: var(--admin-surface);
  cursor: pointer;
  text-align: center;
}
.import-drop:hover { border-color: rgb(var(--rgb-admin-accent) / 0.5); }
.import-drop input { display: none; }
.import-drop b { color: var(--admin-ink); font-size: 13px; font-weight: 500; }
.import-drop small { color: var(--admin-faint); font-size: 10.5px; }

.import-map { margin-bottom: 16px; }
.import-map__title { margin: 0 0 10px; color: var(--admin-ink); font-size: 13px; font-weight: 600; }
.import-map__grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.import-map__item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.09);
  border-radius: 10px;
  background: var(--admin-surface);
  font-size: 11px;
  color: var(--admin-muted);
}
.import-map__item em { margin-left: 5px; color: var(--admin-bad); font-style: normal; font-size: 9px; }
.import-map__item select {
  height: 30px;
  padding: 0 8px;
  border: 1px solid rgb(var(--rgb-admin-ink) / 0.12);
  border-radius: 7px;
  background: var(--admin-surface-2);
  color: var(--admin-ink);
  font: inherit;
  font-size: 11.5px;
}

.import-preview__head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--admin-muted);
  font-size: 11px;
}
.import-preview__head b { color: var(--admin-ink); font-size: 12.5px; }

.import-actions { display: flex; align-items: center; gap: 10px; margin-top: 16px; }
.import-hint { margin-right: auto; color: var(--admin-faint); font-size: 11px; }
</style>
