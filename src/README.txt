Phone Remote source

server.py   Local HTTP service, config validation and Windows input control
index.html  Mobile remote interface
assets\     Embedded interface icons

Runtime entry: G:\SetTopMode\PhoneRemote.exe
Service URL: http://<PC-LAN-IP>:8765

External application files:
  G:\SetTopMode\config.json  Browsers, applications and launch settings
  G:\SetTopMode\icons\      Application icons referenced by config.json

Applications are rendered from /api/apps. Config changes are reloaded
automatically; the service does not need to be restarted. List order controls
display order, and enabled=false hides an application.

Supported launch types:
  browser  References a browser entry and accepts url/fullscreen settings.
  program  Uses an absolute executable path and an optional args array.

IDs must use lowercase ASCII letters, numbers, underscores or hyphens. Icon
values must be filenames inside the icons directory. URLs are limited to HTTP
and HTTPS, and arbitrary shell commands are not supported.

The deployed EXE is a PyInstaller one-file, windowless build. It bundles
index.html and interface assets; config.json and application icons remain
external so they can be edited without rebuilding the EXE.
