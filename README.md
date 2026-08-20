# Phone Remote

**Phone Remote — Cross-platform remote control for Windows PCs**

Phone Remote 是一个面向用户自有 Windows PC 的可信局域网遥控系统。当前仓库包含
Windows/Python Companion、HTTPS API、Windows 管理界面、Web Fallback Client，以及
原生 Flutter Android/iOS Client。

## 当前功能

- 长期 Server Identity、自签名 TLS 证书和异常 Identity 变化保护
- 6 位一次性安全配对码、5 分钟有效期、尝试次数及请求速率限制
- 每台客户端独立 256-bit Credential、哈希存储、独立撤销和 Revoke All
- API v1、D-pad、Touchpad、Unicode Keyboard、Media 和 Power Control
- 仅允许按配置 ID 启动应用，不接受远程 EXE、URL、Shell 或命令行
- Start Menu、Registry、App Paths、MSIX 应用发现，用户批准后才进入 Catalog
- mDNS/DNS-SD `_phone-remote._tcp.local.` 局域网发现
- 托盘入口、仅本机管理页、配对设备和应用 Catalog 管理
- Web Fallback Client 的 Pairing、Authentication 和 Server Identity 检查
- Flutter 原生 Onboarding、mDNS/手工地址发现、安全配对、多 PC 与 Favorite
- Flutter Touchpad-first Remote、D-pad、Unicode Keyboard、Media、Apps 和 Power UI
- Android Wake on LAN、自动唤醒重连、iOS 能力降级和显式离线 Demo Mode
- Rotating Log、Private/LocalSubnet 防火墙规则、Public Network 运行时阻断
- PyInstaller、Inno Setup 安装器工程、Server/Mobile GitHub Actions CI

## 仓库结构

```text
server/                 Python 3.12 Windows Companion、测试和 Web Client
mobile/                 Flutter 3.24.5 Android/iOS Client 与测试
protocol/openapi.yaml   API v1 正式协议边界
packaging/windows/      PyInstaller 与 Inno Setup 工程
docs/                   架构、安全、开发、安装、隐私和发布文档
.github/workflows/      Server CI 与 Mobile CI
config.example.json     version=1 配置兼容性样例
```

## 从源码运行

要求 Windows 11 和 Python 3.12.x：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\server[dev]"
.\.venv\Scripts\python.exe -m phone_remote
```

首次启动会在 `%LOCALAPPDATA%\PhoneRemote` 创建配置、长期身份、TLS 证书、客户端状态
和日志。源代码运行不会修改防火墙；安装器才负责最小权限规则。

托盘菜单可打开管理页和 Web Remote。首次使用 Web Remote 时请求配对码，然后在
Windows Companion 通知中读取并输入。HTTPS 使用本机生成的证书，浏览器首次打开可能
要求用户确认本地证书。

无托盘开发模式：

```powershell
.\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

## 验证与构建

```powershell
Set-Location server
..\.venv\Scripts\ruff.exe format --check .
..\.venv\Scripts\ruff.exe check .
..\.venv\Scripts\python.exe -m pytest
Set-Location ..
.\packaging\windows\build.ps1
.\packaging\windows\build.ps1 -Installer
```

完整开发、协议、安全和安装说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)、
[docs/PROTOCOL.md](docs/PROTOCOL.md)、[docs/SECURITY.md](docs/SECURITY.md) 和
[docs/WINDOWS_INSTALL.md](docs/WINDOWS_INSTALL.md)。移动端工具链、国内镜像和真实 HTTPS
联调说明见 [mobile/README.md](mobile/README.md)。

## 安全边界

本产品仅用于可信 Private LAN。不要做路由器端口映射、不要开放 Public Profile，也不要
把 Credential、`state.json`、Identity Key 或 TLS Key 提交到 Git。服务不采集键盘内容，
不上传遥控历史，不包含云账号、广告、Analytics 或第三方遥测。
