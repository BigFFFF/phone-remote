# Phone Remote V1.0 — 完整开发计划

> **文档状态：Current Baseline + Execution Tracking**
>
> **基线日期：2026-08-18**
>
> **本机执行进度更新：2026-08-20**
>
> 本文档是 Phone Remote V1.0 当前唯一开发基线。后续开发计划采用增量修改；只有在明确要求输出最新版完整计划时，才重新合并全文。

## 本机执行进度（2026-08-20）

本轮已继续执行 Flutter Android/iOS 工程、移动端核心架构、真实 Python HTTPS 联调、
Android 构建、Mobile CI 和开发工具链恢复；Windows/Python Server 也在本机重新全量验证。
Windows 无法执行的 iOS/Xcode 编译及必须使用物理设备/VM 的验收仍保留为 Release Gate。

状态说明：`完成` 表示已实现并经过本机自动验证；`源码完成` 表示实现和 Mock/静态测试完成，
仍需真实 Windows/VM/手机验收；`部分完成` 表示已有产物但仍有明确 Release Gate。

| 原执行步骤 | 状态 | 本轮结果 |
| --- | --- | --- |
| 01–02 Inspect / baseline tests | 完成 | 建立原型回归后再替换；最终 Python 测试 52 项通过 |
| 03–05 Monorepo / move / modularize Server | 完成（Server 范围） | `server/phone_remote` 模块化工程；旧 `src/` 单体已在回归通过后移除 |
| 06–07 Protocol / OpenAPI v1 | 完成 | `protocol/openapi.yaml` 为 API v1 Source of Truth |
| 08–13 Identity / Auth / many-to-many / Pairing / Revocation / TLS | 完成 | ECDSA P-256 长期 Identity、可续期证书、独立 scrypt Credential、限速配对和独立撤销 |
| 14 LAN Discovery | 源码完成 | mDNS `_phone-remote._tcp.local.`；真实多设备发现待局域网验收 |
| 15–16 Tray / Setup / network / firewall / WoL diagnostics | 源码完成 | 托盘、loopback 管理页、Private+LocalSubnet 规则、Public-only 阻断和适配器诊断 |
| 17–23 App Discovery / Catalog / Missing | 完成 | Start Menu、Registry、App Paths、MSIX、Known Apps、显式批准及 Missing Detection |
| 24 Web Fallback migration | 完成 | Pairing、Authentication、API v1、Server Identity 变化阻断 |
| 25–28 Flutter project / architecture / multi-PC / onboarding | 完成 | Flutter 3.24.5 正式 Android+iOS 工程、分层服务、真实/演示仓库、安全多 PC 元数据和原生 Onboarding |
| 29 Discovery / Manual Address | 源码完成 | mDNS `_phone-remote._tcp.local`、TXT/SRV/A 合并、HTTPS-only 手工地址和测试；真实多设备 LAN 待验收 |
| 30–32 Pairing / Secure Credential / trusted reconnect | 完成（源码与本机联调） | 自签名 TLS 证书原始 SPKI Identity 校验、六位码、独立 Credential、Bearer 重连；真实 Python Server HTTPS 集成通过 |
| 33–38 Remote / Touchpad / D-pad / Keyboard / Media / Apps / Power | 源码完成 | Touchpad 默认、33 ms 合并节流、双指手势、原生控制 UI 和 API v1 命令；物理手机 UX/真实控制待验收 |
| 39–42 Android WoL / iOS capability / Auto Wake / Demo | 源码完成 | Android Magic Packet（定向广播优先）、iOS graceful unavailable、唤醒重试和显式 Demo；物理 LAN/WoL 待验收 |
| 43–44 Security hardening / Python tests | 完成 | 鉴权、过期/限速、边界、注入、遍历、敏感日志、Identity、Firewall 等测试 |
| 45 Flutter tests | 完成（源码范围） | 31 项 unit/widget 测试通过；另有 1 项 opt-in 真实 Python HTTPS 配对/重连集成通过 |
| 46 PyInstaller | 完成 | `PhoneRemote.exe` 已构建并通过 `--smoke-test` |
| 47–48 Inno Setup / Firewall lifecycle | 源码完成 | `PhoneRemoteSetup.exe` 编译成功；安装/卸载会管理自有规则和启动项 |
| 49 Installer migration/upgrade tests | 部分完成 | 迁移和命令生成自动测试完成；Fresh/Upgrade/Uninstall VM 矩阵待执行 |
| 50 Server CI | 源码完成 | Windows + Python 3.12 + Ruff + pytest + PyInstaller smoke workflow；首次 GitHub run 待 push 后验证 |
| 51 Mobile CI | 源码完成 | 固定 Flutter 3.24.5/JDK 17，Android analyze/test/debug APK/unsigned AAB；`protocol/**` 同时触发 |
| 52 iOS no-sign compile | 源码完成 | macOS 15 no-sign workflow 已加入；首次托管 Xcode 运行待 push 后验证 |
| 53 Documentation | 完成（当前真实状态） | 架构、协议、安全、开发、安装、发布、审核准备、隐私和 Release Gate 文档 |
| 54 Full regression | 完成（本机可执行范围） | Ruff、52 Python tests、31 Flutter tests、真实跨栈 HTTPS、Android APK/AAB、EXE smoke、Inno compile 均通过 |
| 55 Windows RC installer | 部分完成 | 未签名安装器产物已生成；真实安装矩阵和代码签名仍是 Release Gate |
| 56 Android readiness | 部分完成 | Debug APK、unsigned Release APK/AAB 均构建成功；签名、物理机矩阵和商店 RC 待执行 |
| 57 iOS readiness | 源码完成 | Bundle ID、本地网络/Bonjour 权限、Keychain-backed storage、Wake 降级和 no-sign CI 已配置；macOS 首次编译待验证 |
| 58 Release Gate report | 完成 | 见 `docs/RELEASE_GATE.md` |

本轮自动验证结果：

```text
Python 3.12.10
Ruff format/check: pass
pytest: 52 passed
HTTPS source runtime: pass (Python TLS + Windows Schannel)
PyInstaller: PhoneRemote.exe build + smoke pass
Inno Setup 6.7.3: PhoneRemoteSetup.exe compile pass
Flutter 3.24.5 / Dart 3.5.4 / JDK 17 / Android API 36
flutter analyze: pass
flutter test: 31 passed (live integration normally skipped)
Flutter ↔ real Python HTTPS pairing/reconnect integration: pass
Android debug APK: pass
Android unsigned release APK/AAB: pass
```

未执行且不得误标为完成：真实手机多设备 LAN/控制/WoL 验收、iOS Xcode 本机编译、真实
Installer 系统变更/升级/卸载 VM 矩阵、代码签名、GitHub 托管 CI 首次运行、商店账号、
Signing、受限 Entitlement 和 Production 发布。

---

## 1. 产品定义

### 1.1 产品架构

**Phone Remote = Windows Companion Server + Flutter iOS/Android Client + Web Fallback Client**

Phone Remote 是一个面向用户自有 Windows PC 的可信局域网遥控系统。

核心目标：

- 手机发现 Windows PC；
- 首次安全配对；
- 后续长期可信连接；
- Wake on LAN；
- D-pad / 快捷按键；
- Touchpad；
- Unicode Keyboard；
- Media Control；
- Windows 应用启动；
- Power Control；
- 多 Windows PC 管理；
- 一台 Windows PC 支持多台手机/平板同时配对；
- Windows Web Fallback Client；
- Windows Companion 安装、网络、防火墙和配置管理。

### 1.2 产品边界

Phone Remote 只负责：

```text
Mobile Control Transport
        ↓
Windows PC
```

显示输出属于独立的 **Display Transport**。

Phone Remote 不假设 Windows PC 使用某种具体显示连接方式。PC 可以连接：

- 本地显示器；
- 电视；
- 投影仪；
- 其他独立显示/串流方案。

Server/Mobile 中不得硬编码“TV mode”“HDMI mode”等显示链路假设。

### 1.3 V1 不实现

V1 不实现：

- 公网远程控制；
- Cloud Relay；
- 用户云账号；
- 订阅；
- 支付；
- 广告；
- Analytics；
- 第三方遥测；
- 屏幕捕获；
- Remote Desktop Video；
- 自研视频编码/串流；
- 文件传输；
- Clipboard Sync；
- Voice Control；
- 自动公网端口映射；
- UPnP 公网暴露；
- Windows 自动更新器；
- 自动商店 Production 发布。

---

# 2. 仓库与工程结构

采用 **Monorepo**：

```text
BigFFFF/phone-remote
│
├── server/
│   ├── phone_remote/
│   ├── tests/
│   ├── web/
│   └── pyproject.toml
│
├── mobile/
│   ├── lib/
│   ├── android/
│   ├── ios/
│   ├── test/
│   └── pubspec.yaml
│
├── protocol/
│   ├── openapi.yaml
│   ├── schemas/
│   └── README.md
│
├── packaging/
│   └── windows/
│
├── docs/
│
├── .github/
│   └── workflows/
│
├── config.example.json
├── README.md
└── .gitignore
```

设计原则：

- `server/` 是完整独立的 Windows/Python 工程；
- `mobile/` 是完整独立的 Flutter 工程；
- `protocol/` 是 Server 与 Mobile 的正式协议边界；
- 两边版本号不强制同步；
- API Version 单独管理。

独立运行：

```powershell
cd server
pytest
```

```bash
cd mobile
flutter test
```

---

# 3. Git 工作流

项目为单人开发。

统一采用：

```text
main
```

直接开发。

不使用：

- feature branch；
- PR；
- code review workflow。

开发流程：

```text
修改
 ↓
本地测试
 ↓
git add
 ↓
git commit
 ↓
继续
```

要求：

- 每个相对完整功能或阶段完成后 commit；
- 不把明显不可运行状态长期留在 `main`；
- commit 粒度清晰；
- 默认不自动 push，除非执行任务明确要求 push。

推荐提交信息：

```text
refactor: split Windows server modules
feat: add secure pairing
feat: add application discovery
feat: add Flutter device discovery
feat: add native remote controls
feat: add wake-on-LAN
build: add Windows installer
test: add authentication tests
ci: add server and mobile workflows
```

---

# 4. GitHub Actions CI

PR 不需要，但 CI 保留。

触发模型：

```text
push main
    │
    ├── server/** changed
    │       ↓
    │   Server CI
    │
    ├── mobile/** changed
    │       ↓
    │   Mobile CI
    │
    └── protocol/** changed
            ↓
       Server CI + Mobile CI
```

## 4.1 Server CI

Windows GitHub Runner：

```text
Checkout
 ↓
Setup Python
 ↓
Install dependencies
 ↓
Lint / static check
 ↓
pytest
 ↓
PyInstaller smoke build
```

要求：

- Windows-specific 电源/键鼠逻辑必须可 mock；
- CI 绝不能实际 Sleep/Restart/Shutdown；
- 测试不得修改 runner 系统环境中的真实防火墙规则。

## 4.2 Mobile CI

```text
Checkout
 ↓
Setup Flutter
 ↓
flutter pub get
 ↓
flutter analyze
 ↓
flutter test
 ↓
Android build check
```

iOS 工程成熟后增加：

```text
macOS Runner
 ↓
Flutter iOS no-sign build feasibility check
```

CI 不：

- 自动修改代码；
- 自动 commit；
- 自动发布商店；
- 自动创建开发者账号。

---

# 5. CD 策略

V1 开发期先完成 CI。

开发者账号、Signing、商店应用准备完成后再实现 CD。

建议最终：

## Android RC

```text
mobile-v1.x.x-rcN
 ↓
Build AAB
 ↓
Sign
 ↓
Google Play Internal Testing
```

## iOS RC

```text
mobile-v1.x.x-rcN
 ↓
macOS Runner
 ↓
Archive
 ↓
Sign
 ↓
TestFlight
```

## 正式版本

```text
mobile-v1.x.x
 ↓
Build
 ↓
Sign
 ↓
Upload Store
 ↓
人工最终确认
```

正式 Production 公开发布保留最后一道人工确认。

---

# 6. 当前代码基线与回归保护

执行开发前必须完整检查：

- `README.md`
- `src/server.py`
- `src/index.html`
- `config.example.json`
- `.gitignore`
- 当前 icons/assets
- 当前 Git 状态

先建立基线测试，再做结构重构。

至少覆盖现有功能：

- config validation；
- apps parsing；
- browser launch args；
- program launch args；
- invalid URL rejection；
- invalid path rejection；
- duplicate app ID；
- action validation；
- text length validation；
- mouse parameter clamp；
- unknown action rejection。

原则：

> 不先推倒现有实现；新实现通过回归测试后再替换旧结构。

---

# 7. Windows Server 模块化

目标结构：

```text
server/
└── phone_remote/
    ├── __init__.py
    ├── __main__.py
    ├── server.py
    ├── api.py
    ├── auth.py
    ├── pairing.py
    ├── discovery.py
    ├── config.py
    ├── state.py
    ├── security.py
    ├── windows_control.py
    ├── app_launcher.py
    ├── app_discovery/
    │   ├── __init__.py
    │   ├── discovery.py
    │   ├── start_menu.py
    │   ├── registry.py
    │   ├── app_paths.py
    │   ├── msix.py
    │   └── known_apps.py
    └── tray.py
```

职责：

### `config.py`

- `config.json` 加载；
- schema validation；
- hot reload；
- version migration；
- app configuration。

### `windows_control.py`

- Keyboard；
- Mouse；
- Media Keys；
- Desktop；
- Fullscreen；
- Close Window；
- Power-adjacent controls。

### `app_launcher.py`

- browser launch；
- program launch；
- arguments；
- configured app catalog；
- known-app launch behavior。

### `app_discovery/`

- 已安装应用发现；
- candidate normalization；
- icon discovery；
- duplicate merge；
- Known App matching；
- missing-app detection。

### `api.py`

- HTTP routes；
- request validation；
- auth middleware；
- response mapping。

### `auth.py`

- Client Credential；
- token validation；
- revocation。

### `pairing.py`

- pairing sessions；
- pairing codes；
- expiration；
- brute-force protection。

### `discovery.py`

- LAN Discovery；
- mDNS/DNS-SD。

### `security.py`

- server identity；
- TLS；
- certificate generation；
- crypto helpers。

### `state.py`

- Server persistent state。

### `tray.py`

- Windows Companion UI；
- paired devices；
- network status；
- app management；
- pairing。

---

# 8. 配置兼容性

继续兼容当前 `config.json` 的 `version=1`。

保留：

- `browsers`
- `apps`
- `enabled`
- `icon`
- `program`
- `browser`
- `url`
- `args`
- `fullscreen`
- 用户自定义应用顺序

现有用户配置不得因为正式版重构而失效。

如果配置位置变化：

```text
Detect old config
 ↓
Migrate or continue reading
 ↓
Preserve user configuration
```

不得静默覆盖用户手工修改。

正式版中：

> `config.json` 是持久化格式和高级用户接口，不再是普通用户配置应用的主要 UX。

普通用户通过 Windows Companion GUI 管理 Applications。

---

# 9. 用户数据目录

程序安装：

```text
C:\Program Files\Phone Remote\
```

用户数据：

```text
%LOCALAPPDATA%\PhoneRemote\
```

建议：

```text
%LOCALAPPDATA%\PhoneRemote\
├── state.json
├── server-identity.*
├── server.crt
├── server.key
└── logs/
```

不得将用户秘密状态写到 Program Files。

---

# 10. Server Identity 与长期配对

第一次启动生成长期 Server Identity：

```text
server_id
install_id
server identity key
TLS certificate
display_name
```

默认：

```text
display_name = Windows computer name
```

## 10.1 Pairing 生命周期

采用：

> **一次配对，长期有效，直到明确撤销、Credential 丢失或 Server Identity 重置。**

V1 不设置：

- 30 天；
- 90 天；
- 365 天；

等固定配对过期时间。

正常情况下以下事件不要求重新配对：

- PC Restart；
- PC Shutdown/Sleep；
- Windows Update；
- Server Update；
- Mobile Update；
- 手机 Restart；
- PC LAN IP 改变；
- 路由器重启；
- Wi-Fi/Ethernet 变化；
- 长时间未使用。

重新配对条件：

1. PC 端 Remove Client；
2. Revoke All；
3. Mobile Forget Device；
4. Mobile App 数据被删除；
5. Mobile Credential 丢失；
6. Server 用户状态被重置；
7. Server Identity 被重建/改变；
8. 安全验证失败。

## 10.2 Server Identity 与 TLS Certificate 区分

Mobile 长期信任的核心是：

```text
Server Identity
```

不是单纯某一张短期 TLS Certificate。

TLS Certificate 正常更新时，只要能够通过稳定的 Server Identity 验证身份，不应强制用户重新配对。

如果 Server Identity Key 发生无法解释的改变：

```text
Reject trust
 ↓
Require re-pair
```

---

# 11. 多手机 / 多 PC Pairing

Pairing 关系必须从 V1 开始设计为：

> **Many-to-Many**

即：

```text
PC 1 ←→ Mobile A
PC 1 ←→ Mobile B
PC 1 ←→ Mobile C

PC 2 ←→ Mobile A
PC 3 ←→ Mobile C
```

## 11.1 一台 PC 支持多客户端

每台 Mobile 有独立 Client Identity 和 Credential：

```text
server
└── paired_clients[]
    ├── client_A
    │   ├── client_id
    │   ├── device_name
    │   ├── platform
    │   ├── credential_hash
    │   ├── created_at
    │   └── last_seen
    ├── client_B
    └── client_C
```

要求：

- 每台设备独立 Credential；
- 不能多个手机共享同一个 Bearer Token；
- 撤销 Mobile A 不影响 Mobile B/C；
- 多个已授权客户端允许同时控制一台 PC；
- V1 不做“控制权抢占/主遥控器/Exclusive Lock”；
- 控制事件按 Server 实际收到的顺序执行。

## 11.2 同一时间 Pairing Session

Server 同时只需维护一个有效的主动 Pairing Session。

流程：

```text
Pair New Device
 ↓
Generate code
 ↓
One Mobile pairs successfully
 ↓
Session closes
```

配第二台设备时重新创建 Pairing Session。

---

# 12. API Contract

建立：

```text
protocol/openapi.yaml
```

作为正式 Source of Truth。

API Base：

```text
/api/v1/
```

## Public

```http
GET /api/v1/info
```

示例：

```json
{
  "serverId": "...",
  "name": "Living Room PC",
  "version": "1.0.0",
  "apiVersion": 1,
  "pairing": true
}
```

## Pairing

```http
POST /api/v1/pair/request
POST /api/v1/pair/complete
```

## Authenticated

```http
GET  /api/v1/status
GET  /api/v1/apps

POST /api/v1/action
POST /api/v1/mouse
POST /api/v1/text
POST /api/v1/power
```

旧接口在迁移期可以保留，但标记 Legacy，待 Web Client 完成迁移并经过兼容周期后再删除。

---

# 13. API Versioning

定义：

```text
Product Version: 1.x.x
API Version: 1
```

Server/Mobile Version 不要求一致。

例如：

```text
Server 1.4.2
Mobile 1.2.0
API v1
```

仍然兼容。

Mobile 必须验证 API compatibility。

不兼容时明确提示：

```text
Update Phone Remote on your PC
```

或：

```text
Update Phone Remote app
```

不得直接 crash。

---

# 14. 安全 Pairing

流程：

```text
Mobile
 ↓
Discover Server
 ↓
Pair
 ↓
POST pair/request
 ↓
Windows displays 6-digit code
 ↓
Mobile enters code
 ↓
POST pair/complete
 ↓
Server issues independent client credential
```

Pairing Code：

- cryptographically secure random；
- 6 digits；
- 5 分钟有效；
- 一次性；
- 新请求废除旧 Pairing Session；
- 成功立即失效；
- 错误尝试次数限制；
- Rate Limit。

---

# 15. Authentication

成功 Pair 后生成：

```text
client_id
credential/token
```

Credential：

- 至少 256-bit random entropy；
- 只在配对成功时返回给 Client；
- Server 不保存明文；
- Server 保存 secure hash / verifier；
- comparison 使用 constant-time method。

Client Metadata：

```text
client_id
device_name
platform
created_at
last_seen
credential_hash/verifier
```

移动端敏感 Credential：

- Android → Keystore-backed secure storage；
- iOS → Keychain-backed secure storage。

不允许放普通 SharedPreferences / plain JSON。

未来可以实现透明 Credential Rotation，但不得影响“长期 Pairing Relationship”的用户体验。

---

# 16. TLS / Transport Security

正式 LAN API 使用 HTTPS。

首次启动生成 Server Certificate。

禁止：

```text
trustAllCertificates = true
```

移动端必须：

- 识别已配对 Server Identity；
- 验证当前 transport identity；
- 对异常 Identity change 明确阻断；
- 正常 Certificate Renewal 不应导致无意义重新配对。

安全模型写入：

```text
docs/SECURITY.md
docs/PROTOCOL.md
```

---

# 17. Client Revocation

Windows Companion：

```text
Paired Devices

Longjie's iPhone
Last seen: now
[Remove]

Pixel
Last seen: yesterday
[Remove]

[Revoke All Devices]
```

要求：

- Remove 后该 Credential 立即失效；
- 不影响其他客户端；
- Revoke All 使所有客户端失效；
- 已撤销 Mobile 再连接得到 Unauthorized，并进入重新 Pair 流程。

---

# 18. Windows Application Discovery

正式 V1 增加**应用自动发现**。

目标：

> 普通用户安装 Windows Companion 后不需要自己编辑 `config.json` 和输入 EXE 路径。

但不得把所有扫描结果自动变成可远程执行程序。

流程：

```text
Discover
 ↓
Candidate
 ↓
User Approves
 ↓
Configured App Catalog
 ↓
Expose to Mobile
```

## 18.1 Discovery Sources

优先级：

### A. Start Menu Shortcuts

扫描：

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs
%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs
```

解析 `.lnk`：

- target；
- arguments；
- working directory；
- icon；
- display name。

这是主要高质量来源。

### B. Installed Application Registry Metadata

检查典型 Installed App metadata：

```text
HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall
HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall
HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall
```

用于辅助获取：

- DisplayName；
- InstallLocation；
- DisplayIcon；
- Publisher。

Registry 字符串不得未经验证直接作为远程 Shell Command。

### C. Windows App Paths

读取 Windows App Paths 作为 executable 定位补充。

### D. MSIX / Store Apps

使用单独 Provider。

不能假设 Store App 一定存在可以直接从任意文件路径执行的普通 EXE。

---

# 19. Known App Detector

维护 Known Apps metadata。

示例类别：

```text
Media Players
Browsers
Music
Games / Launchers
Streaming clients
```

例如 Steam 可识别为：

```text
Known App: Steam
default couch mode:
steam://open/bigpicture
```

Known App metadata 只定义：

- executable aliases；
- display aliases；
- launch recommendation；
- category；
- icon metadata hints。

不得用硬编码安装路径替代 Windows discovery。

---

# 20. Application Discovery Data Model

候选：

```text
DiscoveredApp
├── discoveryId
├── name
├── executable/app identity
├── arguments
├── icon
├── source
├── category
├── confidence
└── knownAppId?
```

用户批准后：

```text
ConfiguredApp
├── id
├── name
├── enabled
├── icon
└── launch
```

只有：

```text
Configured + Enabled
```

的应用才能出现在 Remote API / Mobile。

---

# 21. 应用 Catalog 管理

Windows Companion 增加：

```text
Applications
```

来源分三类：

```text
Installed Apps
Web Presets
Manual
```

### Installed Apps

自动发现本地可用软件。

### Web Presets

例如常用 Web 服务 Preset，用户确认后转换为 browser launch config。

### Manual

高级用户手动增加：

- Program；
- Website。

Mobile 永远不能传任意 executable/path/shell command。

它只能请求：

```text
launch configured app ID
```

Server 再次验证。

---

# 22. Application Rescan / Missing Detection

Rescan 时：

- 已配置 App → 保留用户自定义；
- 新应用 → 标记 `New`；
- 已卸载 → 标记 `Missing/Unavailable`；
- 不自动覆盖名称、顺序、参数、图标等用户修改。

例如：

```text
Steam      Available
VLC        Available
Spotify    New
Kodi       Missing
```

Mobile API 可以返回：

```json
{
  "id": "kodi",
  "name": "Kodi",
  "available": false
}
```

Mobile 将其灰显，而不是点击后才发生异常。

---

# 23. Application Discovery 禁止项

V1 明确禁止：

- 递归扫描整块磁盘查找所有 `*.exe`；
- 自动信任任意 EXE；
- 自动把所有发现程序暴露给 Mobile；
- 自动覆盖现有用户 Configured App；
- 从 Mobile 接收任意 Shell command；
- 从 Mobile 接收任意 EXE path；
- 从 Mobile 接收任意 CMD/PowerShell command。

---

# 24. Windows Companion UI

Server 不再完全 invisible。

Tray：

```text
Phone Remote
────────────────
Status: Running
Open Phone Remote
Pair New Device
Paired Devices
Applications
Start with Windows ✓
Copy Device Address
Exit
```

Setup/Management UI 至少包含：

- Server Status；
- Network；
- Network Profile；
- Port；
- Discovery；
- Pairing；
- Paired Clients；
- Applications；
- Firewall status；
- WoL Diagnostics；
- Version。

---

# 25. LAN Discovery

使用 mDNS / DNS-SD：

```text
_phone-remote._tcp.local.
```

广播：

- Server ID；
- Display Name；
- API Version；
- Server Version；
- Port；
- Identity hint/fingerprint identifier。

Mobile 同时支持：

```text
Automatic Discovery
+
Manual Host/IP
```

Discovery 失败不能阻止手动连接。

---

# 26. Windows 网络和防火墙原则

正式用户不应该手工配置端口/Firewall。

安装器自动配置最小必要权限。

## 26.1 API 防火墙规则

原则：

```text
Program
+
Protocol
+
Port
+
Private
+
LocalSubnet
```

典型：

```text
Program:
C:\Program Files\Phone Remote\PhoneRemote.exe

Direction:
Inbound

Protocol:
TCP

LocalPort:
8765

Profile:
Private

RemoteAddress:
LocalSubnet

Action:
Allow
```

实际最终端口和命令由实现决定，但 V1 默认保持固定明确端口。

## 26.2 Outbound

不创建无意义的：

```text
Allow PhoneRemote Outbound Any
```

除非未来存在必须特殊放行的明确出站需求。

## 26.3 Public Network

Phone Remote：

```text
Private Network  → Allow
Public Network   → Block
```

安装器不得自动：

```text
Public → Private
```

因为网络信任级别必须由用户决定。

如果当前网络是 Public：

```text
Phone Remote only accepts connections
on trusted Private networks.

[Open Windows Network Settings]
```

由用户决定是否修改。

## 26.4 Discovery Firewall

根据最终 Windows mDNS backend 创建最小必要规则。

不得无条件粗暴开放 UDP 5353 到所有 Profile/地址。

---

# 27. Windows Installer

正式 Server 主发布：

```text
PhoneRemoteSetup.exe
```

工具链：

```text
Python
 ↓
PyInstaller
 ↓
PhoneRemote.exe
 ↓
Inno Setup
 ↓
PhoneRemoteSetup.exe
```

## 27.1 Installer 自动处理

- UAC 一次；
- Program Files 安装；
- Start Menu；
- optional Desktop shortcut；
- Uninstaller；
- Start with Windows；
- Private Firewall Rule；
- LocalSubnet 限制；
- Program-specific Rule；
- 必要 TCP/Discovery traffic；
- Upgrade 时维护规则；
- Uninstall 时移除自己的规则。

Installer 可以管理员权限运行。

日常 `PhoneRemote.exe` 必须普通用户权限运行，不应每次启动 UAC。

## 27.2 Installer 禁止

不得：

- Disable Windows Firewall；
- 修改 global firewall policy；
- Public profile 开放控制服务；
- Public → Private；
- 配置 Router NAT；
- 公网 Port Forwarding；
- UPnP 公网映射；
- 修改其他程序 Firewall Rule。

---

# 28. Installer / Upgrade / Uninstall Lifecycle

安装：

```text
Install files
 ↓
Create startup configuration
 ↓
Create firewall rules
 ↓
Launch Companion
```

升级：

- Preserve `config.json`；
- Preserve Server Identity；
- Preserve paired clients；
- Repair/update owned firewall rules；
- 不要求正常用户重新 Pair。

卸载：

```text
Stop app
Remove startup
Remove owned firewall rules
Remove Program Files
```

用户数据：

```text
%LOCALAPPDATA%\PhoneRemote
```

默认建议保留。

提供：

```text
Remove paired devices and settings
```

用户显式选择后才清除。

---

# 29. WoL Windows 侧

WoL 与普通应用 Firewall 不同。

涉及：

- BIOS/UEFI；
- NIC driver；
- Wake on Magic Packet；
- Windows device power management；
- Network adapter capability。

Windows Companion 增加诊断：

```text
Wake on LAN

Adapter:
Realtek ...

Wake on Magic Packet: ✓
Wake Permission: ✓
Wake Test: ...
```

能够安全自动修改的 Windows 设置可以提供：

```text
Configure Automatically
```

硬件/BIOS 不支持则只提示，不应伪造成功。

---

# 30. Flutter Mobile Project

`mobile/` 创建正式 Flutter 工程。

目标平台：

- Android；
- iOS。

Mobile 主 UI 必须是 Flutter 原生 UI。

WebView 不作为正式核心 Remote UI。

Web Client 是独立 fallback。

---

# 31. Flutter Architecture

至少定义：

```text
DeviceRepository
DiscoveryService
ApiClient
PairingService
SecureStorage
WakeService
```

UI 与网络层分离。

实现：

```text
RealDeviceRepository
DemoDeviceRepository
```

所有核心逻辑应可以 Mock/Test。

---

# 32. Onboarding

首次启动：

```text
Phone Remote

Control your Windows PC
from your phone.

[Get Started]
```

然后：

```text
Find your PC

[Find Computers]
[Enter Address Manually]
[Try Demo]
```

发现：

```text
Living Room PC
Windows
● Available

[Pair]
```

---

# 33. Mobile 多设备模型

Mobile V1 从底层支持多个 PC。

Device：

```text
id
serverId
name
host
port
mac
serverIdentity
clientId
credential reference
lastSeen
favorite
```

UI：

```text
Living Room PC  ● Online
Desktop PC      ○ Offline
```

支持 Favorite。

如果只有一个 Favorite，可以在启动时自动尝试连接。

---

# 34. Remote 主界面

正式版将 **Touchpad 作为默认控制模式**，D-pad 作为可切换的辅助模式。

底部导航调整为：

```text
Remote
Apps
Devices
Settings
```

进入 `Remote` 后默认显示 Touchpad，并在 Remote 内提供模式切换：

```text
Touchpad | D-pad
```

推荐默认布局：

```text
┌───────────────────────────┐
│        Touchpad           │
│                           │
│                           │
│                           │
│                           │
├────────┬────────┬─────────┤
│ Back   │ Play   │ Full    │
├────────┼────────┼─────────┤
│ Vol-   │ Mute   │ Vol+    │
└────────┴────────┴─────────┘
```

Remote 页面同时提供 Quick Controls：

- Back；
- Home/Desktop；
- Fullscreen；
- Close Window；
- Keyboard；
- Media Controls。

D-pad 模式保留用于：

- Steam Big Picture；
- Kodi / 10-foot UI；
- 支持方向键焦点导航的应用；
- 某些播放器/网页播放器快捷控制。

D-pad 布局：

```text
              ↑
          ←   ●   →
              ↓
```

中央 OK：

```text
Enter
```

Back 采用产品级 Back/Escape 行为。

不得混淆 Back 与 Backspace。

交互要求：

- Touchpad 是默认入口；
- D-pad 不占据主界面核心空间；
- 大 touch target；
- press feedback；
- haptic；
- animation；
- 合理 long-press repeat；
- 请求节流；
- 防止误触重复执行。

Keyboard 不再占用 Bottom Navigation，直接从 Remote 页面快速唤起。

---

# 35. Touchpad

支持：

```text
1 finger move → pointer
1 tap         → left click
2 finger tap  → right click
double tap    → double click
2 finger drag → wheel
```

Click + Drag 只有在稳定实现后加入。

必须做 pointer event throttling。

不能将每个 Flutter raw event 直接转为 HTTP Request。

过载时：

> 丢弃过时 Move，比无限排队更重要。

---

# 36. Keyboard

Flutter 原生 Keyboard 页面：

```text
Text Input

[Send]

Enter
Tab
Escape
Backspace
```

支持 Unicode：

- 中文；
- English；
- 数字；
- Symbols。

Server 继续做：

- maximum length；
- type validation；
- control validation。

不得在 Log 中记录输入正文。

---

# 37. Media

支持：

- Previous；
- Play/Pause；
- Next；
- Volume Down；
- Mute；
- Volume Up。

Server 使用 Windows Media Keys。

不绑定某个特定播放器。

---

# 38. Mobile Apps

```http
GET /api/v1/apps
```

Flutter 原生 Grid。

显示 Windows Server 已批准且启用的 Configured App。

Mobile 只能发送：

```text
known configured app ID
```

不能控制 arbitrary program/path/shell command。

---

# 39. Power

支持：

- Sleep；
- Hibernate（系统支持才显示）；
- Restart；
- Shutdown。

Restart/Shutdown 必须二次确认。

Sleep 可直接执行。

---

# 40. Wake on LAN — Mobile

抽象：

```text
WakeService.wake(Device)
```

Device 保存：

- MAC；
- last IPv4；
- subnet/broadcast 信息。

Android：

- UDP Magic Packet；
- 优先 Subnet Directed Broadcast；
- 必要时尝试 limited/global broadcast。

iOS：

保持相同上层 API，但能力必须可报告：

```text
available
unavailable
unavailableReason
```

iOS 所需 platform entitlement 未准备好时：

- App 不 crash；
- 其他 Remote 功能正常；
- UI 明确说明 WoL 当前 build 不可用。

---

# 41. Auto Wake / Connect

打开已保存设备：

```text
Check status
 ↓
Online?
```

在线：

```text
Enter Remote
```

离线：

```text
WoL available?
 ↓
Send Magic Packet
 ↓
Waking PC...
```

Polling：

```text
1s
1s
2s
2s
...
```

设置合理 timeout。

失败：

```text
Unable to reach PC

[Retry Wake]
[Edit Device]
[Cancel]
```

禁止无限 polling。

---

# 42. iOS Local Network / WoL Release Gate

iOS 局域网连接、Bonjour discovery、UDP broadcast 等必须按 Apple 当前平台要求实现。

WoL 使用 UDP broadcast 时需要考虑 Apple 的 multicast networking entitlement。

该 entitlement 未获批准不应阻塞：

- Android；
- Windows Server；
- iOS 普通 LAN Remote；
- 手动连接；
- Pairing；
- Demo Mode。

具体 release gate 写入：

```text
docs/STORE_RELEASE.md
```

---

# 43. Web Fallback Client

当前网页客户端迁移至：

```text
server/web/
```

继续支持：

- Remote；
- Touchpad；
- Keyboard；
- Apps；
- Power。

但正式版必须加入：

- Pairing；
- Authentication；
- API v1。

浏览器客户端也不能继续“同 LAN 无认证”。

---

# 44. Demo Mode

Mobile 必须实现 Demo Mode。

不访问局域网。

模拟：

- Remote；
- Touchpad；
- Apps；
- Media；
- Power Confirmation；
- Online/Offline State。

UI 明确显示：

```text
Demo
```

目的：

- 用户没有 Windows Companion 时仍可以理解产品；
- App Store Reviewer 可体验主要 UI；
- Mobile Integration 测试可脱离真实 PC。

---

# 45. Logging

Windows：

```text
%LOCALAPPDATA%\PhoneRemote\logs\
```

Rotating Log。

默认 INFO。

可记录：

- client ID；
- connect/disconnect；
- pairing success/failure；
- action type；
- app ID launch；
- error。

禁止记录：

- Bearer Credential；
- Pairing Secret；
- Keyboard Text；
- Password；
- 敏感 Request Body。

---

# 46. Security Hardening

至少验证：

```text
Unauthenticated control → 401
Invalid credential      → 401
Revoked credential      → 401
Expired pair code       → reject
Wrong pair code         → reject
Repeated wrong codes    → rate limit
Unknown app             → reject
Path traversal          → reject
Oversized POST          → reject
Oversized text          → reject
Malformed JSON          → 400
Unknown action          → reject
Arbitrary URL           → impossible
Arbitrary EXE           → impossible
Shell injection         → impossible
Unexpected identity change → reject/re-pair
```

原则：

> Mobile 不能通过任何 API 组合构造 arbitrary Windows command。

---

# 47. Server Tests

使用 pytest。

至少：

- config validation；
- config migration；
- App discovery normalization；
- Known App matching；
- duplicate detection；
- missing-app detection；
- app launch args；
- auth；
- long-term client records；
- multiple paired clients；
- independent revocation；
- pairing；
- pairing expiration；
- pairing rate limit；
- API validation；
- mouse clamp；
- text limit；
- server identity；
- TLS identity logic；
- security；
- firewall command generation；
- installer-supporting logic。

Windows specific actions通过 Mock 测试。

测试不得真的执行：

- Shutdown；
- Restart；
- Sleep；
- Firewall Mutation；
- Registry destructive operation。

---

# 48. Flutter Tests

至少：

- Device serialization；
- 多 PC storage；
- Secure Credential reference；
- Discovery merge；
- Connection state；
- Pairing state；
- long-term paired state；
- revoked state；
- API errors；
- identity mismatch；
- Wake state machine；
- Wake timeout；
- Remote mapping；
- Touchpad gestures；
- App catalog；
- unavailable app；
- Power confirmation；
- Demo Mode。

必须通过：

```bash
flutter analyze
flutter test
```

---

# 49. Windows Build Stages

开发：

```text
python -m phone_remote
```

集成：

```text
PhoneRemote.exe
```

Release Candidate：

```text
PhoneRemoteSetup.exe
```

最终 Windows 验收必须使用真正 Installer，不只验证源码。

---

# 50. Installer 验收

至少：

- Fresh Install；
- Existing old-version config；
- Upgrade；
- Identity preservation；
- Paired client preservation；
- Firewall creation；
- Firewall repair；
- Startup；
- Uninstall；
- Reinstall；
- User-data retention；
- Optional full cleanup；
- Public Network blocked；
- Private LocalSubnet available。

正常用户安装后不需要手工：

- 开端口；
- 建 Firewall Rule；
- 编辑 Registry；
- 修改 JSON 才能开始使用。

---

# 51. Android 发布准备

Flutter Android：

- 正式 Application ID；
- Version Name；
- Version Code；
- Adaptive Icon；
- App Label；
- Local Network / Internet permissions；
- Release configuration；
- secure storage；
- build AAB。

Signing secrets 不提交 Git。

`.gitignore`：

```text
*.jks
*.keystore
keystore.properties
```

提供：

```text
keystore.properties.example
```

### 当前外部要求

截至 2026-08-18，Google 已宣布从 **2026-08-31** 起，新应用和应用更新提交 Google Play 时需 target **Android 16 / API 36 或更高**（特定设备类别除外）。

因此 Phone Remote Mobile 初始正式工程按：

```text
targetSdk >= 36
```

设计；执行/发布时仍需再次检查 Google Play 最新要求。

官方参考：
https://support.google.com/googleplay/android-developer/answer/11926878

---

# 52. iOS 发布准备

准备：

- Bundle ID；
- Display Name；
- Local Network usage description；
- Bonjour service declaration；
- ATS/local networking；
- App Icons；
- Launch Screen；
- Version / Build；
- Runner.entitlements；
- Keychain-backed credential storage。

不要伪造：

> 已经获得 Apple restricted entitlement。

### Apple WoL / Local Network

Apple 当前规定，iOS 上发送/接收 IP multicast 或 broadcast 需要相应 multicast networking entitlement；该 entitlement 需要 Apple permission。

官方参考：

https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.networking.multicast

https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy

---

# 53. App Store 产品形态

Mobile 主 UI 必须是原生 Flutter UI，而不是简单 WebView wrapper。

Apple 当前 App Review Guideline 4.2 要求应用提供超越“重新包装的网站”的功能、内容和 UI。

因此：

- Flutter 原生 Device Management；
- Flutter 原生 Pairing；
- Flutter 原生 Remote；
- Flutter 原生 Touchpad；
- Flutter 原生 Keyboard；
- Flutter 原生 Apps；
- Flutter 原生 Power；
- Flutter 原生 Demo；

都是正式产品要求。

Web Client 只作为 Fallback。

官方参考：

https://developer.apple.com/app-store/review/guidelines/

---

# 54. Android / iOS 发布产物

Android：

开发：

```text
Debug APK
```

RC 真机测试：

```text
Release APK
```

Google Play：

```text
AAB
```

iOS：

```text
Xcode Archive
 ↓
TestFlight
 ↓
App Store
```

---

# 55. Privacy

原则：

```text
No Cloud Account
No Analytics
No Ads
No Telemetry
No Keyboard Content Collection
No Control-history Upload
```

Mobile 本地保存：

- paired PC metadata；
- secure credentials；
- settings。

建立：

```text
docs/PRIVACY_POLICY.md
```

文档必须与真实行为一致。

---

# 56. 文档

最终：

```text
docs/
├── ARCHITECTURE.md
├── PROTOCOL.md
├── SECURITY.md
├── DEVELOPMENT.md
├── WINDOWS_INSTALL.md
├── STORE_RELEASE.md
├── APP_STORE_REVIEW.md
└── PRIVACY_POLICY.md
```

以及：

```text
protocol/openapi.yaml
protocol/README.md
```

---

# 57. README 定位

README 不再以：

```text
网页遥控器
```

作为产品定义。

正式描述：

> **Phone Remote — Cross-platform remote control for Windows PCs**

功能：

- Secure Pairing；
- Long-lived trusted devices；
- Multiple mobile clients；
- Multiple Windows PCs；
- LAN Discovery；
- Wake on LAN；
- D-pad；
- Touchpad；
- Keyboard；
- Media；
- Automatic Application Discovery；
- Application Launcher；
- Power；
- Web Remote。

Quick Start：

```text
Install Windows Companion
 ↓
Install Mobile App
 ↓
Discover
 ↓
Pair once
 ↓
Control
```

---

# 58. 推荐开发执行顺序

Codex Target 模式按以下顺序执行：

```text
01  Inspect current repository
02  Establish baseline regression tests
03  Create final monorepo structure
04  Move current Server into server/
05  Modularize current Server
06  Create protocol/
07  Define OpenAPI v1
08  Implement persistent Server Identity
09  Implement Authentication
10  Implement persistent many-to-many client model
11  Implement Pairing
12  Implement independent Client Revocation
13  Implement TLS / Server Identity validation
14  Implement LAN Discovery
15  Implement Windows Companion Tray / Setup
16  Implement network/profile/firewall diagnostics
17  Implement Application Discovery framework
18  Implement Start Menu discovery
19  Implement Registry/App Paths discovery
20  Implement Known App matching
21  Implement MSIX/Store discovery where feasible
22  Implement Application Catalog GUI
23  Implement Rescan / Missing detection
24  Upgrade Web Fallback to Pairing/Auth/API v1
25  Create Flutter mobile/
26  Implement Flutter architecture
27  Implement Device Storage / Multi-PC
28  Implement Onboarding
29  Implement Discovery / Manual Address
30  Implement Pairing
31  Implement Secure Credential Storage
32  Implement persistent trusted-device reconnect
33  Implement Remote UI with Touchpad as default mode
34  Implement Touchpad
35  Implement optional D-pad mode and Keyboard quick access
36  Implement Media
37  Implement Apps
38  Implement Power
39  Implement Android WoL
40  Implement iOS Wake capability abstraction
41  Implement Auto Wake / Connect
42  Implement Demo Mode
43  Security hardening
44  Expand Python tests
45  Expand Flutter tests
46  PyInstaller build
47  Inno Setup installer
48  Firewall lifecycle
49  Installer migration/upgrade tests
50  GitHub Actions Server CI
51  GitHub Actions Mobile CI
52  iOS no-sign compile check where feasible
53  Complete documentation
54  Full regression
55  Windows Release Candidate installer
56  Android RC build
57  iOS project readiness validation
58  Produce Release Gate report
```

---

# 59. Codex Target 模式执行原则

把本计划交给 Codex 后：

> 不要只输出另一份计划，实际执行。

流程：

```text
Inspect
 ↓
Implement
 ↓
Test
 ↓
Fix
 ↓
Commit
 ↓
Continue
```

要求：

- 直接在 `main`；
- 不创建 feature branch；
- 不创建 PR；
- 每个完整阶段 commit；
- 普通技术选择自行做合理决策；
- 优先成熟且维护中的库；
- 不自己实现复杂密码学算法；
- 不提交 secrets；
- 不因 Apple/Google 外部凭证缺失停止项目；
- 不破坏现有 config compatibility；
- 替代实现验证成功前不删除旧功能；
- 不自动发布商店 Production；
- 不自动创建开发者账号；
- 不自动声称已获得受限 entitlement。

---

# 60. 外部 Release Gates

这些不阻塞正常代码开发：

- Apple Developer Program；
- Google Play Developer Account；
- Apple Signing Certificates；
- Provisioning Profiles；
- Apple multicast networking entitlement approval；
- Google Play Signing；
- App Store Listing；
- Play Listing；
- Store Screenshots；
- App privacy forms；
- Production reviewer metadata。

记录到：

```text
docs/STORE_RELEASE.md
```

---

# 61. V1 完成标准

## Windows Companion

- [ ] 正式 Installer 可安装
- [ ] Server 普通用户权限运行
- [x] Start with Windows（源码/安装器已实现）
- [x] Tray UI（源码完成）
- [x] API v1
- [x] Persistent Server Identity
- [x] Secure Pairing
- [x] 一次 Pair 长期有效
- [x] 多 Mobile Pairing
- [x] 多 Mobile 同时控制
- [x] Independent Credential
- [x] Independent Revocation
- [x] Revoke All
- [x] TLS
- [x] Server identity validation
- [x] LAN Discovery（源码完成，待多设备验收）
- [x] Keyboard（Mock 验证）
- [x] Mouse（Mock 验证）
- [x] Media（Mock 验证）
- [x] Power（Mock 验证，测试未执行真实电源操作）
- [x] App Discovery
- [x] Known App matching
- [x] App Catalog GUI
- [x] Missing App detection
- [x] Web Fallback
- [x] Old config compatibility
- [x] Private Firewall Rule（命令/安装脚本验证）
- [x] LocalSubnet restriction（命令/安装脚本验证）
- [x] Public Network blocked（规则及运行时策略验证）
- [x] WoL diagnostics（源码完成）

## Android

- [x] Discovery（源码/Mock，待真实多设备 LAN 验收）
- [x] Manual device（HTTPS-only 输入校验）
- [x] Multi-PC
- [x] Pairing（真实 Python HTTPS 联调通过）
- [x] Long-lived paired state（Bearer reconnect 联调通过）
- [x] Secure Credential storage（Android Keystore-backed plugin，待物理机验收）
- [x] Identity validation（原始 SPKI DER 钉扎联调通过）
- [x] Remote with Touchpad as default mode
- [x] Touchpad（源码/节流测试，待物理机 UX）
- [x] Optional D-pad mode
- [x] Keyboard quick access from Remote
- [x] Media
- [x] Apps
- [x] Unavailable App handling
- [x] Power（二次确认；自动测试不执行真实电源操作）
- [x] WoL（Magic Packet/广播目标测试，待物理 LAN）
- [x] Auto Wake（重试状态机测试）
- [x] Demo Mode
- [x] flutter analyze
- [x] flutter test
- [x] release-compatible build（unsigned Release APK 构建通过）
- [x] AAB-ready structure（unsigned Release AAB 构建通过）

## iOS

- [x] Discovery（源码/权限配置，待真实设备）
- [x] Manual device
- [x] Multi-PC
- [x] Pairing（共享 Dart 核心）
- [x] Long-lived paired state（共享 Dart 核心）
- [x] Keychain-backed Credential（plugin 配置，待真实设备）
- [x] Identity validation
- [x] Remote with Touchpad as default mode
- [x] Touchpad（源码，待真实设备 UX）
- [x] Optional D-pad mode
- [x] Keyboard quick access from Remote
- [x] Media
- [x] Apps
- [x] Power
- [x] Wake abstraction
- [x] Graceful entitlement limitation
- [x] Demo Mode
- [ ] iOS project build feasibility

## Security

- [x] 未 Pair Client 无法控制
- [x] Invalid Credential rejected
- [x] Revoked Client rejected
- [x] Revoking one Client does not affect others
- [x] Pair brute force mitigated
- [x] Pair code expires
- [x] Unexpected Server Identity change detected
- [x] Arbitrary executable impossible
- [x] Arbitrary shell command impossible
- [x] Discovered Apps not auto-trusted
- [x] Sensitive text not logged
- [x] Credential not logged
- [x] Public Firewall Profile not exposed

## Installer

- [ ] Fresh install
- [ ] Upgrade
- [x] Old config migration（自动测试）
- [x] Identity retained（持久化布局/自动测试）
- [x] Pairings retained（持久化布局/自动测试）
- [x] Firewall install/repair（命令/编译验证）
- [x] Startup（源码/编译验证）
- [ ] Uninstall
- [ ] Reinstall
- [ ] Settings retention
- [ ] Optional full cleanup

## CI

- [x] Server CI（workflow 已实现，首次托管运行待验证）
- [x] Mobile CI（workflow 已实现，首次托管运行待验证）
- [x] `protocol/**` triggers both
- [x] PyInstaller smoke build
- [x] Android build check
- [ ] iOS compile check when feasible（no-sign job 已定义，待首次托管运行）

## Documentation

- [x] README
- [x] ARCHITECTURE
- [x] PROTOCOL
- [x] SECURITY
- [x] DEVELOPMENT
- [x] WINDOWS_INSTALL
- [x] STORE_RELEASE
- [x] APP_STORE_REVIEW
- [x] PRIVACY_POLICY

---

# 62. Codex 最终报告

完成所有无需外部账号/Signing 的可执行内容后，Codex 输出：

1. Architecture Summary
2. Repository Structure
3. Files Added
4. Files Changed
5. Server API Status
6. Protocol Status
7. Server Identity Model
8. Pairing / Authentication Model
9. Multi-client Status
10. Application Discovery Status
11. Flutter Architecture
12. Android Status
13. iOS Status
14. Windows Installer Status
15. Firewall / Network Status
16. Tests Executed
17. CI Status
18. Build Results
19. Remaining Release Gates
20. Known Limitations
21. Exact Manual Release Steps Remaining

然后停止。

不得自动：

- 创建 GitHub Release；
- 发布 Google Play Production；
- 发布 App Store Production；
- 创建 Developer Account；
- 申请受限 entitlement。

---

# 63. 当前开发基线结论

当前 V1 核心架构固定为：

```text
Windows Companion Server
        ↕
   API / Pairing
        ↕
Flutter Android / iOS
```

并保留：

```text
Web Fallback Client
```

正式设计必须满足：

```text
Monorepo
main direct development
CI
Long-lived Pairing
Many-to-Many Devices
Independent Credentials
LAN-only Security
Windows Installer-managed Networking
Automatic Application Discovery
Native Flutter Mobile UI
Display Transport Independence
Store-ready Architecture
```

这份文档作为 **Phone Remote V1.0 Current Baseline** 使用。

后续修改采用增量方式维护。


---

# Development Environment Version Baseline (Fixed)

本项目 V1 开发环境版本固定如下。

原则：

- 所有开发机器尽量使用一致版本；
- 不依赖系统全局 Python 默认版本；
- 使用项目级虚拟环境；
- CI 环境必须与开发基线保持一致；
- 版本升级需要经过验证后再调整。

## 固定工具链

| 工具 | 固定版本 |
| --- | --- |
| Windows | Windows 11 |
| Git | >=2.45 |
| GitHub CLI | >=2.50 |
| Python | 3.12.x |
| pip | >=24 |
| pytest | >=8 |
| Ruff | >=0.5 |
| PyInstaller | >=6 |
| Flutter | 3.24.x Stable |
| Dart | Flutter 自带版本 |
| Android Studio | Ladybug+ |
| Android SDK | target API 36 准备 |
| JDK | 17 LTS |
| Node.js | 22 LTS |
| Inno Setup | 6.x |
| Xcode | 16+ |
| CocoaPods | >=1.15 |

---

## Python Runtime Policy

Phone Remote Server V1 固定：

```text
Python 3.12.x
```

开发机器允许存在其他 Python 版本，但项目开发必须明确使用 Python 3.12：

```powershell
py -3.12 -m venv .venv
```

原因：

- 保证依赖解析一致；
- 保证 PyInstaller 打包结果一致；
- 保证 GitHub Actions CI 可复现；
- 避免 Python 不同版本导致语法、标准库和第三方库行为差异。

---

## CI Version Lock

GitHub Actions 必须固定：

```yaml
python-version: "3.12"
```

Flutter CI 使用：

```text
Flutter 3.24.x Stable
```

Android 构建：

```text
JDK 17
Android SDK target API 36
```

禁止使用：

- latest Python；
- latest Flutter；
- latest JDK。

避免基础环境自动升级导致构建结果变化。

---

## iOS Build Environment

iOS 正式构建固定：

```text
macOS
Xcode 16+
CocoaPods >=1.15
```

Windows 环境可以维护：

- Flutter/Dart代码；
- iOS工程文件；
- 配置文件；

但正式 iOS Build、Archive、Signing 必须在 macOS + Xcode 环境完成。

---
