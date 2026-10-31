import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { MotionPlugin } from '@vueuse/motion'

import App from './App.vue'
import router from './router'
import './styles/main.css'
import './styles/glass-tokens.css'
// v2.3.2 内容卡定款液态玻璃（G 方案）
import './styles/glass-card.css'
import './styles/admin.css'
// 管理后台数据大屏 v8（冷色三屏）：独立令牌组，不复用移动端 V5 配色
import './styles/admin-wall.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// @vueuse/motion：WeatherPill 展开、气泡按压回弹（stiffness 300 / damping 20）、模式滑块
app.use(MotionPlugin)

app.mount('#app')
