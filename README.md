# Phone Remote

Phone Remote 是一个仅在局域网内运行的 Windows 手机网页遥控器，可用手机控制方向键、媒体播放、音量、鼠标和键盘输入，并从配置文件启动常用音视频应用。

## 功能

- 遥控：方向键、确认、返回、桌面、关闭窗口、全屏和媒体控制
- 触控：移动指针、单击、双击、右键和双指滚动
- 键盘：向当前 Windows 焦点控件发送中英文文本
- 应用：从外部 JSON 配置动态加载应用和图标
- 电源：睡眠、重启和关机，带二次确认
- 配置热加载：修改后无需重启服务，手机端最多约 5 秒刷新

## 目录

```text
PhoneRemote.exe       Windows 部署程序，本地生成，不提交到 Git
config.json           当前电脑的运行配置，不提交到 Git
config.example.json   可提交的配置模板
icons/                应用图标
src/                  Python 服务、网页界面和通用图标
```

## 从源码运行

1. 将 `config.example.json` 复制为 `config.json`，按本机安装位置修改应用路径。
2. 在项目根目录运行：

```powershell
py .\src\server.py
```

3. 手机与电脑连接同一局域网，在手机浏览器打开 `http://<电脑局域网IP>:8765`。

服务只依赖 Python 标准库。Windows 防火墙需要允许 TCP 端口 `8765` 的专用网络入站连接。

## 构建单文件程序

安装 PyInstaller：

```powershell
py -m pip install pyinstaller
```

在 `src` 目录执行：

```powershell
py -m PyInstaller --noconfirm --clean --onefile --windowed --name PhoneRemote --add-data "index.html;." --add-data "assets;assets" server.py
```

生成的 `src\dist\PhoneRemote.exe` 可放到项目根目录。`config.json` 和 `icons` 保持外置，因此增加应用或替换图标不需要重新构建。

## 配置应用

`config.json` 顶层包含 `browsers` 和 `apps`。应用顺序就是手机端显示顺序，`enabled: false` 会隐藏应用。

浏览器启动示例：

```json
{
  "id": "example_web",
  "name": "示例网站",
  "enabled": true,
  "icon": "example.png",
  "launch": {
    "type": "browser",
    "browser": "edge",
    "url": "https://example.com",
    "fullscreen": true
  }
}
```

程序启动示例：

```json
{
  "id": "example_app",
  "name": "示例程序",
  "enabled": true,
  "icon": "example.png",
  "launch": {
    "type": "program",
    "path": "C:\\Program Files\\Example\\example.exe",
    "args": []
  }
}
```

应用 ID 仅支持小写英文字母、数字、下划线和连字符。图标必须是 `icons` 目录内的文件名；网页地址仅支持 HTTP/HTTPS，不支持任意 Shell 命令。

## 安全说明

本服务没有账号认证，设计用途是受信任的家庭局域网。不要把端口 `8765` 映射到公网，也不要在公共网络配置文件中放行该端口。
