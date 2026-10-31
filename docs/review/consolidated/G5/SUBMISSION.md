# G5 开发交付：Android 工程与调试 APK

- 状态：开发与构建完成；真机安装、权限、断网和扫码测试按用户要求后置到统一验收。
- appId：`com.eatwhat.app`，应用名：`食刻 EatWhat`。
- 调试 APK：`data/eatwhat-debug.apk`，23,049,849 bytes，SHA-256 `3449af2d601e0fa1ca175521f5f92ecaa78b9fe2e5c71a851ebe2115de838245`。
- 构建：Capacitor 8 + Android compile/target SDK 36；本地 Gradle 8.14.3、JDK 24；`BUILD SUCCESSFUL`。
- 原生网络：`VITE_API_ORIGIN=http://10.235.60.171:8000`、`VITE_WS_ORIGIN=ws://10.235.60.171:8000`；Manifest 允许本地 HTTP cleartext。
- 图标：黑色底 + 白色碗筷矢量，替换 Capacitor 默认图标。
- 冻结：`scripts/freeze_release.py` 已实现，必须等统一验收 `overall_ok=true` 后才执行；展示壳不提前启用。

## 后置验收

1. 真机安装与启动、局域网 API/WebSocket。
2. 权限、后台/断网/重连。
3. 二维码扫码进入房间。
4. 统一测试通过后执行冻结并启用展示壳。
