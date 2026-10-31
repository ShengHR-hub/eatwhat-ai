import daisyui from 'daisyui'

/**
 * 设计令牌唯一出处（MASTER_SPEC v2.3.1 第六章 §6 + MOBILE_VISUAL_SPEC §1）。
 *
 * v2.3 起为「黑 · 灰 · 银 · 白」单色体系，旧的暖橙 / 森林绿 / 奶油白全部作废：
 *   近黑 #17171A ｜ 银灰 #55555E ｜ 白 #FFFFFF ｜ 浅灰 #F4F4F5
 *
 * 规则：
 *  - 双模式不再靠颜色区分，靠图标 + 文案 + 分段开关选中态（深灰实底白字）；
 *  - 业务组件只许用语义类（primary / secondary / base-* / ink / steel），禁止硬编码 hex；
 *  - JS 侧（ECharts / confetti / Lottie）统一走 src/utils/theme.js 读 CSS 变量，不要在这里 import。
 */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        // 单色体系原始令牌
        ink: '#17171A', // 近黑：主文字 / 主按钮
        steel: '#55555E', // 银灰：次级文字 / 次级按钮
        mist: '#F4F4F5', // 浅灰：内容底
        silver: '#D4D4D8', // 分隔线 / 描边
        // 动效背景用色（由 Vue Bits props 消费，禁止在组件里写死）
        backdrop: {
          grainA: '#3A3A40',
          grainB: '#17171A',
          grainC: '#55555E',
          chrome: '#1A1A1A',
          chromeMax: '#222226',
        },
      },
      fontFamily: {
        sans: [
          '"Inter var"',
          'Inter',
          '"SF Pro SC"',
          '"PingFang SC"',
          '"HarmonyOS Sans SC"',
          '"Noto Sans SC"',
          'system-ui',
          'sans-serif',
        ],
        display: ['"SF Pro Display"', '"Inter"', '"PingFang SC"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        // 规范锁定：卡片投影就是这个值，不要另造
        bento: '0 8px 30px rgb(0 0 0 / 0.04)',
        lift: '0 12px 40px rgb(0 0 0 / 0.08)',
        pill: '0 4px 18px rgb(0 0 0 / 0.06)',
        drawer: '-18px 0 48px rgb(0 0 0 / 0.12)',
      },
      borderRadius: {
        bento: '1.5rem', // = rounded-3xl 的语义别名
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      keyframes: {
        'rise-in': {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.9)', opacity: '0.55' },
          '70%': { transform: 'scale(1.35)', opacity: '0' },
          '100%': { transform: 'scale(1.35)', opacity: '0' },
        },
      },
      animation: {
        'rise-in': 'rise-in 0.36s cubic-bezier(0.34, 1.56, 0.64, 1) both',
        'pulse-ring': 'pulse-ring 2.2s ease-out infinite',
      },
    },
  },
  plugins: [daisyui],
  daisyui: {
    logs: false,
    themes: [
      {
        eatwhat: {
          primary: '#17171A',
          'primary-content': '#FFFFFF',
          secondary: '#55555E',
          'secondary-content': '#FFFFFF',
          accent: '#D4D4D8',
          'accent-content': '#17171A',
          neutral: '#3A3A40',
          'neutral-content': '#FFFFFF',
          'base-100': '#FFFFFF',
          'base-200': '#F4F4F5',
          'base-300': '#E4E4E7',
          'base-content': '#17171A',
          info: '#55555E',
          success: '#3A3A40',
          warning: '#55555E',
          error: '#17171A',
          '--rounded-box': '1.5rem',
          '--rounded-btn': '1rem',
          '--rounded-badge': '9999px',
          '--animation-btn': '0.2s',
          '--btn-focus-scale': '0.97',
          '--border-btn': '1px',
          '--tab-radius': '1rem',
        },
      },
    ],
  },
}
