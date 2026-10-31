<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  kind: { type: String, required: true },
  record: { type: Object, default: null },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['save', 'cancel'])
const featureKeys = [
  ['spicy_level', '辣度'],
  ['oily_level', '油腻度'],
  ['soup_level', '汤水感'],
  ['temp_fit', '适宜温度'],
  ['satiety_level', '饱腹度'],
  ['prep_speed', '出餐速度'],
  ['social_fit', '社交属性'],
  ['comfort_level', '抚慰指数'],
]
const appliances = ['炒锅', '电饭煲', '空气炸锅', '免开火凉拌', '一锅出']
const blankDish = () => ({
  name: '', mode_type: 'HOME_COOKING', restaurant_id: null, cuisine_type: '', dish_role: 'ONE_MEAL',
  price_or_cost: null, cook_minutes: 15, appliance_tag: ['炒锅'], ingredientsText: '', auxText: '',
  recipe_steps: '', image_url: '', allergenText: '', is_synthetic: null,
  feature: Object.fromEntries(featureKeys.map(([key]) => [key, ''])),
})
const blankRestaurant = () => ({
  name: '', source_type: 'AMAP_POI', category: '', avg_price: null, rating: null,
  longitude: null, latitude: null, distance_meters: null, address: '', campus: 'SIYUAN', is_synthetic: null,
})
const form = reactive(props.kind === 'dish' ? blankDish() : blankRestaurant())
const localError = ref('')

watch(() => props.record, (record) => {
  Object.assign(form, props.kind === 'dish' ? blankDish() : blankRestaurant())
  localError.value = ''
  if (!record) return
  if (props.kind === 'restaurant') {
    Object.keys(form).forEach((key) => { if (key in record) form[key] = record[key] })
  } else {
    Object.keys(form).forEach((key) => {
      if (key !== 'feature' && !['ingredientsText', 'auxText', 'allergenText'].includes(key) && key in record) form[key] = record[key]
    })
    form.ingredientsText = (record.ingredients_main || []).join('，')
    form.auxText = (record.ingredients_aux || []).join('，')
    form.allergenText = (record.allergen_tags || []).join('，')
    featureKeys.forEach(([key]) => { form.feature[key] = record.feature_vector?.[key] ?? '' })
  }
}, { immediate: true })

const optionalNumber = (value) => value === '' || value === null || value === undefined ? null : Number(value)
const listValue = (value) => value.split(/[，,]/).map((item) => item.trim()).filter(Boolean)

function submit() {
  localError.value = ''
  if (!form.name.trim()) {
    localError.value = '名称不能为空'
    return
  }
  if (props.kind === 'restaurant') {
    emit('save', {
      name: form.name.trim(), source_type: form.source_type, category: form.category || '',
      avg_price: optionalNumber(form.avg_price), rating: optionalNumber(form.rating),
      longitude: optionalNumber(form.longitude), latitude: optionalNumber(form.latitude),
      distance_meters: optionalNumber(form.distance_meters), address: form.address || '',
      campus: form.campus || null, is_synthetic: form.is_synthetic,
    })
    return
  }
  if (form.mode_type === 'OUT_DINING' && !Number(form.restaurant_id)) {
    localError.value = '外食菜品必须填写有效门店 ID'
    return
  }
  if (form.mode_type === 'HOME_COOKING') form.restaurant_id = null
  if (!form.appliance_tag.length) {
    localError.value = '至少选择一种厨具'
    return
  }
  const featureValues = featureKeys.map(([key]) => form.feature[key])
  const filled = featureValues.filter((value) => value !== '').length
  if (filled !== 0 && filled !== featureKeys.length) {
    localError.value = '八维向量必须全部填写，或全部留空表示未打标'
    return
  }
  const featureVector = filled === 0 ? null : Object.fromEntries(featureKeys.map(([key]) => [key, Number(form.feature[key])]))
  emit('save', {
    name: form.name.trim(), mode_type: form.mode_type,
    restaurant_id: form.mode_type === 'OUT_DINING' ? Number(form.restaurant_id) : null,
    cuisine_type: form.cuisine_type || '', dish_role: form.dish_role,
    price_or_cost: optionalNumber(form.price_or_cost), cook_minutes: Number(form.cook_minutes),
    appliance_tag: [...form.appliance_tag], ingredients_main: listValue(form.ingredientsText),
    ingredients_aux: listValue(form.auxText), recipe_steps: form.recipe_steps || '',
    feature_vector: featureVector, image_url: form.image_url || '',
    allergen_tags: form.allergenText.trim() ? listValue(form.allergenText) : null,
    is_synthetic: form.is_synthetic,
  })
}
</script>

<template>
  <div class="admin-modal-backdrop" @click.self="emit('cancel')">
    <section class="admin-modal" role="dialog" aria-modal="true" :aria-label="record ? '编辑记录' : '新增记录'">
      <header class="admin-modal__header">
        <div>
          <p class="admin-eyebrow">{{ kind === 'dish' ? 'DISH' : 'RESTAURANT' }}</p>
          <h2>{{ record ? `编辑 #${record.id}` : '新增记录' }}</h2>
        </div>
        <button class="admin-icon-button" type="button" aria-label="关闭" @click="emit('cancel')">×</button>
      </header>
      <form class="admin-form" @submit.prevent="submit">
        <label class="admin-field admin-field--wide"><span>名称 *</span><input v-model="form.name" maxlength="128" required></label>
        <template v-if="kind === 'restaurant'">
          <label class="admin-field"><span>来源类型</span><select v-model="form.source_type"><option value="AMAP_POI">AMAP_POI</option><option value="CANTEEN">CANTEEN</option></select></label>
          <label class="admin-field"><span>校区</span><select v-model="form.campus"><option value="SIYUAN">思源</option><option value="JIANDA_YANTA">建大雁塔</option><option value="">未归属</option></select></label>
          <label class="admin-field"><span>分类</span><input v-model="form.category" maxlength="64"></label>
          <label class="admin-field"><span>合成标记</span><select v-model="form.is_synthetic"><option :value="null">未知 / 不声明</option><option :value="true">合成</option><option :value="false">真实来源</option></select></label>
          <label class="admin-field"><span>均价（可空）</span><input v-model="form.avg_price" type="number" min="0" step="0.01"></label>
          <label class="admin-field"><span>真实评分（可空）</span><input v-model="form.rating" type="number" min="0" max="5" step="0.1"></label>
          <label class="admin-field"><span>GCJ-02 经度</span><input v-model="form.longitude" type="number" min="-180" max="180" step="any"></label>
          <label class="admin-field"><span>GCJ-02 纬度</span><input v-model="form.latitude" type="number" min="-90" max="90" step="any"></label>
          <label class="admin-field"><span>直线距离（米）</span><input v-model="form.distance_meters" type="number" min="0" step="1"></label>
          <label class="admin-field admin-field--wide"><span>地址</span><input v-model="form.address" maxlength="255"></label>
        </template>
        <template v-else>
          <label class="admin-field"><span>模式</span><select v-model="form.mode_type"><option value="OUT_DINING">外食</option><option value="HOME_COOKING">下厨</option></select></label>
          <label class="admin-field"><span>菜品角色</span><select v-model="form.dish_role"><option value="MEAT">荤菜</option><option value="VEG">素菜</option><option value="SOUP">汤</option><option value="ONE_MEAL">一餐</option></select></label>
          <label v-if="form.mode_type === 'OUT_DINING'" class="admin-field"><span>门店 ID *</span><input v-model="form.restaurant_id" type="number" min="1" step="1" required></label>
          <label class="admin-field"><span>菜系</span><input v-model="form.cuisine_type" maxlength="64"></label>
          <label class="admin-field"><span>价格 / 成本（可空）</span><input v-model="form.price_or_cost" type="number" min="0" step="0.01"></label>
          <label class="admin-field"><span>制作分钟</span><input v-model="form.cook_minutes" type="number" min="1" max="1440" step="1" required></label>
          <label class="admin-field"><span>合成标记</span><select v-model="form.is_synthetic"><option :value="null">未知 / 不声明</option><option :value="true">合成</option><option :value="false">真实来源</option></select></label>
          <fieldset class="admin-field admin-field--wide admin-checks"><legend>厨具（多选）</legend><label v-for="item in appliances" :key="item"><input v-model="form.appliance_tag" type="checkbox" :value="item"><span>{{ item }}</span></label></fieldset>
          <label class="admin-field admin-field--wide"><span>主料（逗号分隔）</span><input v-model="form.ingredientsText"></label>
          <label class="admin-field admin-field--wide"><span>辅料（逗号分隔）</span><input v-model="form.auxText"></label>
          <label class="admin-field admin-field--wide"><span>过敏原标签（逗号分隔）</span><input v-model="form.allergenText"></label>
          <label class="admin-field admin-field--wide"><span>图片路径</span><input v-model="form.image_url" maxlength="255"></label>
          <label class="admin-field admin-field--wide"><span>菜谱步骤</span><textarea v-model="form.recipe_steps" rows="3" maxlength="20000" /></label>
          <fieldset class="admin-feature-grid admin-field--wide"><legend>八维向量（0–1；全部留空 = 未打标）</legend><label v-for="([key, label]) in featureKeys" :key="key"><span>{{ label }}</span><input v-model="form.feature[key]" type="number" min="0" max="1" step="0.01"></label></fieldset>
        </template>
        <p v-if="localError.value || error" class="admin-form-error" role="alert">{{ localError.value || error }}</p>
        <footer class="admin-modal__footer">
          <button class="admin-button" type="button" :disabled="saving" @click="emit('cancel')">取消</button>
          <button class="admin-button admin-button--primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存到数据库' }}</button>
        </footer>
      </form>
    </section>
  </div>
</template>
