const messages = {
      zh: { connecting: '正在连接', connected: '已连接', disconnected: '连接断开', powerMenu: '电源菜单', remoteControls: '遥控按键', remotePages: '遥控器页面', up: '向上', down: '向下', left: '向左', right: '向右', volumeDown: '降低音量', volumeUp: '提高音量', mute: '静音', playPause: '播放或暂停', fullscreen: '全屏', back: '返回', desktop: '桌面', close: '关闭', touchpad: '触控板', touchHelp: '单指移动，轻点单击，双指滚动', leftClick: '左键', doubleClick: '双击', rightClick: '右键', play: '播放', typeText: '输入文字', send: '发送', backspace: '退格', enter: '回车', clear: '清空', remote: '遥控', touch: '触控', apps: '应用', keyboard: '键盘', securePairing: '安全配对', firstPair: '首次连接需要由 Windows Companion 显示一次性验证码。', deviceName: '此设备名称', requestCode: '请求验证码', completePairing: '完成配对', power: '电源', standby: '待机 (S3)', hibernate: '休眠', restart: '重启', shutdown: '关机', cancel: '取消', confirm: '确认', confirmActionTitle: '确认操作', credentialExpired: '配对凭据已失效，请重新配对。', requestPairFailed: '无法请求配对', enterCode: seconds => `请在 ${seconds} 秒内输入 Windows Companion 显示的 6 位验证码。`, pairingRequestFailed: '配对请求失败', pairingFailed: '配对失败', pairingSuccess: '配对成功', identityChanged: '检测到 Server Identity 变化，已阻止连接。请确认后重新配对。', openingApp: name => `正在打开${name}`, appOpened: name => `${name}已打开`, desktopShown: '已显示电脑桌面', windowClosed: '已关闭当前窗口', operationFailed: '操作失败', connectionFailed: '连接失败', touchFailed: '触控失败', sendFailed: '发送失败', textSent: '文字已发送', noApps: '暂无应用', appsUnavailable: '应用配置不可用', configWarning: warning => `配置错误，已使用上次设置：${warning}`, appsLoadFailed: '应用列表加载失败', touchConnectionFailed: '触控连接失败', confirmAction: label => `确认${label}`, executesImmediately: label => `${label}会立即执行。` },
      en: { connecting: 'Connecting', connected: 'Connected', disconnected: 'Disconnected', powerMenu: 'Power menu', remoteControls: 'Remote controls', remotePages: 'Remote pages', up: 'Up', down: 'Down', left: 'Left', right: 'Right', volumeDown: 'Volume down', volumeUp: 'Volume up', mute: 'Mute', playPause: 'Play or pause', fullscreen: 'Fullscreen', back: 'Back', desktop: 'Desktop', close: 'Close', touchpad: 'Touchpad', touchHelp: 'Move with one finger, tap to click, and use two fingers to scroll', leftClick: 'Left click', doubleClick: 'Double click', rightClick: 'Right click', play: 'Play', typeText: 'Type text', send: 'Send', backspace: 'Backspace', enter: 'Enter', clear: 'Clear', remote: 'Remote', touch: 'Touch', apps: 'Apps', keyboard: 'Keyboard', securePairing: 'Secure pairing', firstPair: 'The first connection requires a one-time code shown by Windows Companion.', deviceName: 'Device name', requestCode: 'Request code', completePairing: 'Complete pairing', power: 'Power', standby: 'Standby (S3)', hibernate: 'Hibernate', restart: 'Restart', shutdown: 'Shut down', cancel: 'Cancel', confirm: 'Confirm', confirmActionTitle: 'Confirm action', credentialExpired: 'The pairing credential expired. Pair again.', requestPairFailed: 'Unable to request pairing', enterCode: seconds => `Enter the six-digit code shown by Windows Companion within ${seconds} seconds.`, pairingRequestFailed: 'Pairing request failed', pairingFailed: 'Pairing failed', pairingSuccess: 'Paired successfully', identityChanged: 'The server identity changed, so the connection was blocked. Confirm the PC and pair again.', openingApp: name => `Opening ${name}`, appOpened: name => `${name} opened`, desktopShown: 'PC desktop shown', windowClosed: 'Active window closed', operationFailed: 'Operation failed', connectionFailed: 'Connection failed', touchFailed: 'Touch control failed', sendFailed: 'Send failed', textSent: 'Text sent', noApps: 'No apps', appsUnavailable: 'App configuration unavailable', configWarning: warning => `Configuration error; using the previous settings: ${warning}`, appsLoadFailed: 'Unable to load apps', touchConnectionFailed: 'Touch connection failed', confirmAction: label => `Confirm ${label}`, executesImmediately: label => `${label} will run immediately.` }
    };
    let language = localStorage.getItem('phone-remote-language') || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
    const t = (key, value) => {
      const result = messages[language][key];
      return typeof result === 'function' ? result(value) : (result || key);
    };
    function applyLanguage() {
      document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
      document.title = language === 'zh' ? '客厅遥控' : 'Phone Remote';
      document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(node => { node.placeholder = t(node.dataset.i18nPlaceholder); });
      document.querySelectorAll('[data-i18n-aria]').forEach(node => { const value = t(node.dataset.i18nAria); node.setAttribute('aria-label', value); node.title = value; });
      document.getElementById('languageSelect').value = language;
    }
    document.getElementById('languageSelect').addEventListener('change', event => {
      language = event.target.value;
      localStorage.setItem('phone-remote-language', language);
      applyLanguage();
      setConnection(dot.classList.contains('connected'), true);
      appsSignature = '';
      if (credential) refreshApps(); else renderApps([]);
    });
    const dot = document.getElementById('dot');
    const statusText = document.getElementById('status');
    const toast = document.getElementById('toast');
    const touchpad = document.getElementById('touchpad');
    const powerDialog = document.getElementById('powerDialog');
    const powerMenu = document.getElementById('powerMenu');
    const confirmPane = document.getElementById('confirmPane');
    const confirmTitle = document.getElementById('confirmTitle');
    const confirmText = document.getElementById('confirmText');
    const confirmAction = document.getElementById('confirmAction');
    const appGrid = document.getElementById('appGrid');
    const keyboardInput = document.getElementById('keyboardInput');
    const sendTextButton = document.getElementById('sendTextButton');
    const pairDialog = document.getElementById('pairDialog');
    const pairHelp = document.getElementById('pairHelp');
    const pairCode = document.getElementById('pairCode');
    const deviceName = document.getElementById('deviceName');
    const completePairPane = document.getElementById('completePairPane');
    let credential = localStorage.getItem('phone-remote-credential') || '';
    let pairedServerId = localStorage.getItem('phone-remote-server-id') || '';
    let identityFingerprint = localStorage.getItem('phone-remote-identity') || '';
    let pairingSessionId = '';
    let pendingAction = null;
    let toastTimer = 0;
    let wakeLock = null;
    let appsSignature = '';
    let lastConfigWarning = '';
    let activeView = 'remote';
    let statusRefreshPromise = null;
    let appsRefreshPromise = null;
    let connectionState = null;

    function vibrate(duration = 8) {
      if (navigator.vibrate) navigator.vibrate(duration);
    }
    function showToast(text, duration = 1300) {
      toast.textContent = text;
      toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove('show'), duration);
    }
    function setConnection(connected, force = false) {
      connected = Boolean(connected);
      if (!force && connectionState === connected) return;
      connectionState = connected;
      dot.classList.toggle('connected', connected);
      statusText.textContent = connected ? t('connected') : t('disconnected');
    }
    function showPairing(message = t('firstPair')) {
      pairHelp.textContent = message;
      completePairPane.classList.add('hidden');
      pairingSessionId = '';
      if (!pairDialog.open) pairDialog.showModal();
    }
    async function apiFetch(path, options = {}) {
      const headers = { ...(options.headers || {}) };
      const requestCredential = credential;
      if (requestCredential) headers.Authorization = `Bearer ${requestCredential}`;
      const response = await fetch(path, { ...options, headers });
      if (response.status === 401 && !path.includes('/pair/')) {
        // Ignore a response sent with an older credential. It may finish while
        // a new pairing session is open or after the replacement credential is saved.
        if (requestCredential !== credential) return response;
        discardPointerSocket();
        credential = '';
        localStorage.removeItem('phone-remote-credential');
        showPairing(t('credentialExpired'));
      }
      return response;
    }
    async function requestPairing() {
      try {
        const response = await fetch('/api/v1/pair/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || t('requestPairFailed'));
        pairingSessionId = data.sessionId;
        pairHelp.textContent = t('enterCode', data.expiresIn);
        completePairPane.classList.remove('hidden');
        pairCode.focus({ preventScroll: true });
      } catch (error) { showToast(error.message || t('pairingRequestFailed'), 2200); }
    }
    async function completePairing() {
      try {
        const response = await fetch('/api/v1/pair/complete', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessionId: pairingSessionId, code: pairCode.value, deviceName: deviceName.value || navigator.userAgent.slice(0, 80), platform: 'web' })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || t('pairingFailed'));
        discardPointerSocket();
        credential = data.credential; pairedServerId = data.serverId; identityFingerprint = data.identityFingerprint;
        localStorage.setItem('phone-remote-credential', credential);
        localStorage.setItem('phone-remote-server-id', pairedServerId);
        localStorage.setItem('phone-remote-identity', identityFingerprint);
        pairingSessionId = '';
        pairCode.value = ''; pairDialog.close(); showToast(t('pairingSuccess')); refresh(); refreshApps();
      } catch (error) { showToast(error.message || t('pairingFailed'), 2200); }
    }
    async function verifyServerIdentity() {
      try {
        const response = await fetch('/api/v1/info', { cache: 'no-store' });
        const data = await response.json();
        if (pairedServerId && (data.serverId !== pairedServerId || data.identityFingerprint !== identityFingerprint)) {
          discardPointerSocket();
          credential = '';
          localStorage.removeItem('phone-remote-credential');
          showPairing(t('identityChanged'));
          return false;
        }
        if (!credential) {
          if (!pairingSessionId) showPairing();
          return false;
        }
        return true;
      } catch { setConnection(false); return false; }
    }
    async function send(action, button = null) {
      const appName = button?.dataset.appName;
      const givesFeedback = action === 'desktop' || action === 'close_active' || action.startsWith('app:');
      if (button && givesFeedback) button.classList.add('busy');
      if (appName) showToast(t('openingApp', appName));
      try {
        const isPower = ['sleep', 'hibernate', 'restart', 'shutdown'].includes(action);
        const appId = action.startsWith('app:') ? action.slice(4) : '';
        const endpoint = appId ? `/api/v1/apps/${encodeURIComponent(appId)}/launch` : (isPower ? '/api/v1/power' : '/api/v1/action');
        const response = await apiFetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(appId ? {} : { action })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || t('operationFailed'));
        setConnection(true);
        if (appName) showToast(t('appOpened', appName));
        if (action === 'desktop') showToast(t('desktopShown'));
        if (action === 'close_active') showToast(t('windowClosed'));
      } catch (error) {
        setConnection(false);
        showToast(error.message || t('connectionFailed'), 1800);
      } finally {
        if (button) button.classList.remove('busy');
      }
    }
    async function sendMouse(payload, quiet = false) {
      try {
        if (payload.type === 'move' || payload.type === 'wheel') {
          const socket = await pointerWebSocket();
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
            setConnection(true);
            return true;
          }
        }
        const response = await apiFetch('/api/v1/mouse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(t('touchFailed'));
        setConnection(true);
        return true;
      } catch (error) {
        setConnection(false);
        if (!quiet) showToast(error.message || t('connectionFailed'), 1800);
        return false;
      }
    }
    let pointerSocket = null;
    let pointerSocketPromise = null;
    let pointerSocketRetryAt = 0;
    function discardPointerSocket() {
      const socket = pointerSocket;
      pointerSocket = null;
      if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
    }
    async function pointerWebSocket() {
      if (pointerSocket?.readyState === WebSocket.OPEN) return pointerSocket;
      if (!credential || Date.now() < pointerSocketRetryAt) return null;
      if (pointerSocketPromise) return pointerSocketPromise;
      pointerSocketPromise = new Promise((resolve) => {
        const url = new URL('/api/v1/pointer', window.location.href);
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        const socket = new WebSocket(url, ['phone-remote.v1', `auth.${credential}`]);
        let settled = false;
        const timeout = window.setTimeout(() => {
          failed();
          try { socket.close(); } catch (_) { /* Connection is still opening. */ }
        }, 2000);
        const failed = () => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          if (pointerSocket === socket) pointerSocket = null;
          pointerSocketRetryAt = Date.now() + 5000;
          resolve(null);
        };
        socket.addEventListener('open', () => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          pointerSocket = socket;
          pointerSocketRetryAt = 0;
          resolve(socket);
        }, { once: true });
        socket.addEventListener('error', failed, { once: true });
        socket.addEventListener('close', () => {
          if (!settled) failed();
          if (pointerSocket === socket) pointerSocket = null;
        });
      }).finally(() => { pointerSocketPromise = null; });
      return pointerSocketPromise;
    }
    async function sendKeyboardText() {
      const value = keyboardInput.value;
      if (!value) {
        keyboardInput.focus();
        return;
      }
      sendTextButton.classList.add('busy');
      try {
        const response = await apiFetch('/api/v1/text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: value })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || t('sendFailed'));
        keyboardInput.value = '';
        setConnection(true);
        showToast(t('textSent'));
      } catch (error) {
        setConnection(false);
        showToast(error.message || t('connectionFailed'), 1800);
      } finally {
        sendTextButton.classList.remove('busy');
        keyboardInput.focus();
      }
    }
    function refresh() {
      if (!credential) return Promise.resolve();
      if (statusRefreshPromise) return statusRefreshPromise;
      statusRefreshPromise = (async () => {
        try {
          const response = await apiFetch('/api/v1/status', { cache: 'no-store' });
          const data = await response.json();
          setConnection(Boolean(data.ok));
        } catch {
          setConnection(false);
        }
      })().finally(() => { statusRefreshPromise = null; });
      return statusRefreshPromise;
    }
    function renderApps(apps) {
      appGrid.replaceChildren();
      if (!apps.length) {
        const empty = document.createElement('div');
        empty.className = 'app-empty';
        empty.textContent = t('noApps');
        appGrid.append(empty);
        return;
      }
      const fragment = document.createDocumentFragment();
      apps.forEach((app) => {
        const button = document.createElement('button');
        button.className = 'app-button';
        button.dataset.action = `app:${app.id}`;
        button.dataset.appName = app.name;

        const image = document.createElement('img');
        image.className = 'app-icon';
        image.src = app.icon;
        image.alt = '';
        image.addEventListener('error', () => {
          image.src = '/assets/layout-grid.svg';
          image.classList.add('fallback');
        }, { once: true });

        const label = document.createElement('span');
        label.className = 'app-label';
        label.textContent = app.name;
        button.append(image, label);
        fragment.append(button);
      });
      appGrid.append(fragment);
    }
    function refreshApps() {
      if (!credential) return Promise.resolve();
      if (appsRefreshPromise) return appsRefreshPromise;
      appsRefreshPromise = (async () => {
        try {
          const response = await apiFetch('/api/v1/apps', { cache: 'no-store' });
          const data = await response.json();
          if (!response.ok || !data.ok) throw new Error(data.error || t('appsUnavailable'));
          const signature = JSON.stringify(data.apps);
          if (signature !== appsSignature) {
            renderApps(data.apps);
            appsSignature = signature;
          }
          if (data.warning && data.warning !== lastConfigWarning) {
            showToast(t('configWarning', data.warning), 2600);
          }
          lastConfigWarning = data.warning || '';
        } catch (error) {
          if (!appsSignature) renderApps([]);
          showToast(error.message || t('appsLoadFailed'), 2000);
        }
      })().finally(() => { appsRefreshPromise = null; });
      return appsRefreshPromise;
    }
    function switchView(name) {
      activeView = name;
      document.querySelectorAll('.view').forEach((view) => {
        view.classList.toggle('active', view.id === `view-${name}`);
      });
      document.querySelectorAll('.tab-button').forEach((button) => {
        const active = button.dataset.view === name;
        button.classList.toggle('active', active);
        button.setAttribute('aria-current', active ? 'page' : 'false');
      });
      localStorage.setItem('settop-view', name);
      if (name === 'apps' && credential) refreshApps();
    }
    function showPowerMenu() {
      pendingAction = null;
      powerMenu.classList.remove('hidden');
      confirmPane.classList.add('hidden');
      if (!powerDialog.open) powerDialog.showModal();
    }
    document.getElementById('powerButton').addEventListener('click', showPowerMenu);
    document.getElementById('requestPair').addEventListener('click', requestPairing);
    document.getElementById('completePair').addEventListener('click', completePairing);
    document.getElementById('closePower').addEventListener('click', () => powerDialog.close());
    document.getElementById('backToPower').addEventListener('click', showPowerMenu);
    document.addEventListener('pointerdown', (event) => {
      if (event.target.closest('button')) vibrate();
    });
    document.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button._suppressClick) {
        button._suppressClick = false;
        return;
      }
      if (button.dataset.view) {
        switchView(button.dataset.view);
        if (button.dataset.view === 'keyboard') keyboardInput.focus();
        return;
      }
      if (button.dataset.action) {
        send(button.dataset.action, button);
        return;
      }
      if (button.dataset.mouseClick) {
        const type = button.dataset.mouseClick;
        sendMouse(type === 'double' ? { type: 'double' } : { type: 'click', button: type });
        return;
      }
      if (button.dataset.confirm) {
        pendingAction = button.dataset.confirm;
        const label = button.textContent.trim();
        confirmTitle.textContent = t('confirmAction', label);
        confirmText.textContent = t('executesImmediately', label);
        powerMenu.classList.add('hidden');
        confirmPane.classList.remove('hidden');
      }
    });
    confirmAction.addEventListener('click', () => {
      if (pendingAction) send(pendingAction);
      pendingAction = null;
      powerDialog.close();
    });
    sendTextButton.addEventListener('click', sendKeyboardText);
    document.getElementById('clearTextButton').addEventListener('click', () => {
      keyboardInput.value = '';
      keyboardInput.focus();
    });
    keyboardInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        sendKeyboardText();
      }
    });
    document.querySelectorAll('[data-repeat]').forEach((button) => {
      let delayTimer = 0;
      let holding = false;
      let repeatGeneration = 0;
      const stop = () => {
        clearTimeout(delayTimer);
        holding = false;
        repeatGeneration += 1;
        button.classList.remove('is-pressed');
      };
      const repeatAction = async (generation) => {
        while (holding && generation === repeatGeneration) {
          await send(button.dataset.action);
          if (!holding || generation !== repeatGeneration) return;
          await new Promise(resolve => setTimeout(resolve, 110));
        }
      };
      button.addEventListener('pointerdown', () => {
        button._suppressClick = false;
        button.classList.add('is-pressed');
        holding = true;
        const generation = ++repeatGeneration;
        delayTimer = setTimeout(() => {
          if (!holding || generation !== repeatGeneration) return;
          button._suppressClick = true;
          repeatAction(generation);
        }, 430);
      });
      button.addEventListener('pointerup', stop);
      button.addEventListener('pointercancel', stop);
      button.addEventListener('pointerleave', stop);
    });
    const pointers = new Map();
    let gesture = null;
    let lastTapTime = 0;
    let singleTapTimer = 0;
    const tapSlop = 6;
    const pointerTraffic = {
      moveX: 0, moveY: 0, wheel: 0,
      scheduled: 0, inFlight: 0, maxInFlight: 1,
      lastFailureToast: 0
    };
    const pointerBufferLimit = 32 * 1024;
    const pendingMoveLimit = 240;
    const pendingWheelLimit = 960;
    function hasPendingPointerTraffic() {
      return Math.abs(pointerTraffic.moveX) >= 0.01 ||
        Math.abs(pointerTraffic.moveY) >= 0.01 ||
        Math.abs(pointerTraffic.wheel) >= 0.01;
    }
    function schedulePointerFlush() {
      if (!pointerTraffic.scheduled) {
        pointerTraffic.scheduled = requestAnimationFrame(flushPointerTraffic);
      }
    }
    function queueMove(dx, dy) {
      pointerTraffic.moveX = takeBounded(pointerTraffic.moveX + dx * 1.55, pendingMoveLimit);
      pointerTraffic.moveY = takeBounded(pointerTraffic.moveY + dy * 1.55, pendingMoveLimit);
      schedulePointerFlush();
    }
    function queueWheel(delta) {
      pointerTraffic.wheel = takeBounded(pointerTraffic.wheel + delta * 9, pendingWheelLimit);
      schedulePointerFlush();
    }
    function takeBounded(value, limit) {
      return Math.max(-limit, Math.min(limit, value));
    }
    function flushPointerTraffic() {
      pointerTraffic.scheduled = 0;
      if (pointerTraffic.inFlight >= pointerTraffic.maxInFlight) {
        schedulePointerFlush();
        return;
      }
      if (pointerSocket?.readyState === WebSocket.OPEN &&
          pointerSocket.bufferedAmount >= pointerBufferLimit) {
        schedulePointerFlush();
        return;
      }
      let payload = null;
      if (Math.abs(pointerTraffic.moveX) >= 0.01 || Math.abs(pointerTraffic.moveY) >= 0.01) {
        const dx = takeBounded(pointerTraffic.moveX, 120);
        const dy = takeBounded(pointerTraffic.moveY, 120);
        pointerTraffic.moveX -= dx;
        pointerTraffic.moveY -= dy;
        payload = { type: 'move', dx, dy };
      } else if (Math.abs(pointerTraffic.wheel) >= 0.01) {
        const delta = takeBounded(pointerTraffic.wheel, 480);
        pointerTraffic.wheel -= delta;
        payload = { type: 'wheel', delta };
      }
      if (!payload) return;
      pointerTraffic.inFlight += 1;
      sendMouse(payload, true).then((ok) => {
        const now = Date.now();
        if (!ok && now - pointerTraffic.lastFailureToast > 2000) {
          pointerTraffic.lastFailureToast = now;
          showToast(t('touchConnectionFailed'), 1800);
        }
      }).finally(() => {
        pointerTraffic.inFlight -= 1;
        if (hasPendingPointerTraffic()) schedulePointerFlush();
      });
      if (hasPendingPointerTraffic()) schedulePointerFlush();
    }
    function registerTap() {
      const now = Date.now();
      if (now - lastTapTime < 300 && singleTapTimer) {
        clearTimeout(singleTapTimer);
        singleTapTimer = 0;
        lastTapTime = 0;
        vibrate(12);
        sendMouse({ type: 'double' });
        return;
      }
      lastTapTime = now;
      singleTapTimer = setTimeout(() => {
        sendMouse({ type: 'click', button: 'left' });
        singleTapTimer = 0;
      }, 270);
    }
    touchpad.addEventListener('pointerdown', (event) => {
      touchpad.setPointerCapture(event.pointerId);
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (pointers.size === 1) {
        gesture = {
          startTime: Date.now(), moved: false, multi: false, scrollDistance: 0,
          startX: event.clientX, startY: event.clientY,
          lastX: event.clientX, lastY: event.clientY, lastCenterY: event.clientY
        };
      } else if (gesture) {
        gesture.multi = true;
        gesture.lastCenterY = [...pointers.values()].reduce((sum, point) => sum + point.y, 0) / pointers.size;
      }
      touchpad.classList.add('active');
      event.preventDefault();
    });
    touchpad.addEventListener('pointermove', (event) => {
      if (!pointers.has(event.pointerId) || !gesture) return;
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (pointers.size >= 2) {
        const centerY = [...pointers.values()].reduce((sum, point) => sum + point.y, 0) / pointers.size;
        const dy = centerY - gesture.lastCenterY;
        gesture.scrollDistance += Math.abs(dy);
        if (gesture.scrollDistance >= tapSlop) {
          gesture.moved = true;
          queueWheel(dy);
        }
        gesture.lastCenterY = centerY;
      } else if (!gesture.multi) {
        const samples = typeof event.getCoalescedEvents === 'function'
          ? event.getCoalescedEvents()
          : [event];
        for (const sample of samples.length ? samples : [event]) {
          const dx = sample.clientX - gesture.lastX;
          const dy = sample.clientY - gesture.lastY;
          const totalX = sample.clientX - gesture.startX;
          const totalY = sample.clientY - gesture.startY;
          if (!gesture.moved && Math.hypot(totalX, totalY) >= tapSlop) {
            gesture.moved = true;
            queueMove(totalX, totalY);
          } else if (gesture.moved) {
            queueMove(dx, dy);
          }
          gesture.lastX = sample.clientX;
          gesture.lastY = sample.clientY;
        }
      }
      event.preventDefault();
    });
    function endPointer(event, cancelled = false) {
      pointers.delete(event.pointerId);
      if (pointers.size === 0) {
        if (gesture && !cancelled && !gesture.moved && Date.now() - gesture.startTime < 280) {
          if (gesture.multi) {
            vibrate(10);
            sendMouse({ type: 'click', button: 'right' });
          } else {
            registerTap();
          }
        }
        gesture = null;
        touchpad.classList.remove('active');
      } else if (gesture?.multi) {
        gesture.lastCenterY = [...pointers.values()].reduce((sum, point) => sum + point.y, 0) / pointers.size;
      }
      event.preventDefault();
    }
    touchpad.addEventListener('pointerup', endPointer);
    touchpad.addEventListener('pointercancel', (event) => endPointer(event, true));
    async function keepAwake() {
      if (!('wakeLock' in navigator) || document.visibilityState !== 'visible') return;
      try { wakeLock = await navigator.wakeLock.request('screen'); } catch { wakeLock = null; }
    }
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        refresh();
        if (activeView === 'apps') refreshApps();
        keepAwake();
      }
    });
    applyLanguage();
    const savedView = localStorage.getItem('settop-view');
    switchView(['remote', 'touch', 'apps', 'keyboard'].includes(savedView) ? savedView : 'remote');
    verifyServerIdentity().then(valid => { if (valid) { refresh(); refreshApps(); } });
    keepAwake();
    setInterval(() => {
      if (document.visibilityState === 'visible') refresh();
    }, 15000);
    setInterval(() => {
      if (document.visibilityState === 'visible' && activeView === 'apps') refreshApps();
    }, 60000);
