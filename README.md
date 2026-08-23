# Phone Remote

Phone Remote 是一个在局域网内控制 Windows PC 的项目，包含 Windows Companion、原生
Flutter 手机端和浏览器备用遥控器。

## 下载正式版

- [Windows 安装包](https://github.com/BigFFFF/phone-remote/releases/latest/download/PhoneRemoteSetup-v1.3.0.exe)
- [Android 安装包](https://github.com/BigFFFF/phone-remote/releases/latest/download/PhoneRemote-v1.3.0-android.apk)
- [版本说明与校验文件](https://github.com/BigFFFF/phone-remote/releases/latest)

Windows 与 Android 端需要安装在同一可信局域网内。首次连接请按 Windows 托盘程序显示的
配对码完成配对。

## 功能

- 一次配对、长期信任，多手机与多电脑独立管理
- Touchpad、D-pad、键盘、媒体、应用启动和电源控制
- mDNS 自动发现与手工地址连接
- Android 手动 Wake on LAN；iOS 在能力不可用时安全降级
- 可调节并持久化的 Touchpad 指针与滚动灵敏度
- Windows 首次运行自动发现已安装的 Edge 和 Steam
- Windows 托盘双击直达 Applications 管理页，并可集中设置开机启动、配对和应用
- Windows、Web Remote 与手机 App 可手动选择中文或 English
- 待机、休眠、重启与关机控制
- 原生 App 使用固定 Server Identity 的 HTTPS
- Web Remote 供可信私有局域网中的普通浏览器使用

## 目录

```text
server/                 Windows Companion、管理页和 Web Remote
mobile/                 Flutter Android/iOS App
protocol/openapi.yaml   API v1 的唯一机器可读契约
packaging/windows/      Windows 打包与安装器
docs/                   设计、开发、安全和发布说明
```

## 从源码运行 Companion

要求 Windows 11 和 Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\server[dev]"
.\.venv\Scripts\python.exe -m phone_remote
```

数据默认保存在 `%LOCALAPPDATA%\PhoneRemote`。托盘菜单可打开管理页、显示配对码和复制
Web Remote 地址。无托盘开发模式：

```powershell
.\.venv\Scripts\python.exe -m phone_remote --no-tray --print-pair-code
```

## 开发入口

- [开发与测试](docs/DEVELOPMENT.md)
- [架构](docs/ARCHITECTURE.md)
- [协议概览](docs/PROTOCOL.md)
- [安全边界](docs/SECURITY.md)
- [Windows 安装](docs/WINDOWS_INSTALL.md)
- [Web Remote 使用说明](docs/WEB_REMOTE.md)
- [发布状态](docs/RELEASE_GATE.md)

本项目只面向局域网，不应通过端口映射、公共防火墙规则或云隧道暴露到互联网。Web
Remote 使用未加密 HTTP，仅适用于可信私有网络。
