# G5 Android 构建配置

## 应用

- appId：`com.eatwhat.app`
- appName：`食刻 EatWhat`
- 原生目录：`frontend/android`
- Web 资源：`frontend/dist`

## 本地工具

- Android SDK：`D:\EatWhat\.android-sdk`
- Gradle：`D:\EatWhat\.android-home\gradle-8.14.3`
- JDK：`D:\Program Files\Java\jdk-24`
- SDK/Gradle 大文件目录均已被 `.gitignore` 排除。

## 原生网络

Web 默认仍使用相对 `/api/v1` 与同源 WebSocket。APK 构建时通过环境变量注入：

```bash
VITE_API_ORIGIN=http://10.235.60.171:8000
VITE_WS_ORIGIN=ws://10.235.60.171:8000
```

后端需监听 `0.0.0.0:8000`，手机与电脑需处于同一局域网。Android Manifest 已允许本地 HTTP cleartext；仅用于答辩联调，不作为公网安全声明。

## 构建顺序

1. `npm run build`（frontend，带上述两个 Vite 环境变量）
2. `npx cap sync android`
3. `gradle assembleDebug --no-daemon`（frontend/android）

Gradle 与 Maven 均保留官方仓库，镜像仅用于加速下载。

## 冻结边界

`scripts/freeze_release.py` 已实现，但统一验收前不会执行。展示壳必须在冻结清单生成后再启用，不提前伪装为 S19 完成。
