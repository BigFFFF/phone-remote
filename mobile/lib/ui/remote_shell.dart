import 'dart:async';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../application/phone_remote_controller.dart';
import '../localization.dart';
import '../models/device.dart';
import '../services/pointer_move_dispatcher.dart';
import '../services/touchpad_settings.dart';
import 'find_computers_screen.dart';

class RemoteShell extends StatefulWidget {
  const RemoteShell({
    super.key,
    required this.controller,
    this.demo = false,
    this.touchpadSettingsStore,
  });

  const RemoteShell.demo({super.key, this.touchpadSettingsStore})
      : controller = null,
        demo = true;

  final PhoneRemoteController? controller;
  final bool demo;
  final TouchpadSettingsStore? touchpadSettingsStore;

  @override
  State<RemoteShell> createState() => _RemoteShellState();
}

class _RemoteShellState extends State<RemoteShell> {
  int _index = 0;
  TouchpadSettings _touchpadSettings = const TouchpadSettings();
  late final TouchpadSettingsStore _touchpadSettingsStore;

  @override
  void initState() {
    super.initState();
    _touchpadSettingsStore =
        widget.touchpadSettingsStore ?? _defaultTouchpadSettingsStore();
    unawaited(_loadTouchpadSettings());
  }

  TouchpadSettingsStore _defaultTouchpadSettingsStore() {
    try {
      return SharedPreferencesTouchpadSettingsStore();
    } on StateError {
      // Flutter unit tests do not register the platform preference plugin.
      return MemoryTouchpadSettingsStore();
    }
  }

  Future<void> _loadTouchpadSettings() async {
    try {
      final settings = await _touchpadSettingsStore.load();
      if (mounted) {
        setState(() => _touchpadSettings = settings);
      }
    } on Object {
      // Defaults remain usable if preference storage is temporarily unavailable.
    }
  }

  void _changeTouchpadSettings(TouchpadSettings settings) {
    setState(() => _touchpadSettings = settings);
  }

  void _saveTouchpadSettings() {
    unawaited(
        _touchpadSettingsStore.save(_touchpadSettings).catchError((_) {}));
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    if (controller == null) {
      return _buildShell(context, null);
    }
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) => _buildShell(context, controller.preferredDevice),
    );
  }

  Widget _buildShell(BuildContext context, Device? device) {
    final pages = <Widget>[
      _RemotePage(
        controller: widget.controller,
        demo: widget.demo,
        touchpadSettings: _touchpadSettings,
      ),
      _AppsPage(controller: widget.controller, demo: widget.demo),
      _DevicesPage(controller: widget.controller, demo: widget.demo),
      _SettingsPage(
        controller: widget.controller,
        demo: widget.demo,
        touchpadSettings: _touchpadSettings,
        onTouchpadSettingsChanged: _changeTouchpadSettings,
        onTouchpadSettingsChangeEnd: _saveTouchpadSettings,
      ),
    ];
    return Scaffold(
      appBar: AppBar(
        title:
            Text(widget.demo ? 'Phone Remote' : device?.name ?? 'Phone Remote'),
        actions: <Widget>[
          if (widget.demo)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Chip(label: Text(context.tr('Demo'))),
            )
          else if (widget.controller != null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: _ConnectionChip(controller: widget.controller!),
            ),
        ],
      ),
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: <NavigationDestination>[
          NavigationDestination(
            icon: const Icon(Icons.touch_app_outlined),
            selectedIcon: const Icon(Icons.touch_app_rounded),
            label: context.tr('Remote'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.apps_outlined),
            selectedIcon: const Icon(Icons.apps_rounded),
            label: context.tr('Apps'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.devices_outlined),
            selectedIcon: const Icon(Icons.devices_rounded),
            label: context.tr('Devices'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.settings_outlined),
            selectedIcon: const Icon(Icons.settings_rounded),
            label: context.tr('Settings'),
          ),
        ],
      ),
    );
  }
}

class _ConnectionChip extends StatelessWidget {
  const _ConnectionChip({required this.controller});

  final PhoneRemoteController controller;

  @override
  Widget build(BuildContext context) {
    final (label, color, icon) = switch (controller.connectionPhase) {
      RemoteConnectionPhase.connected => (
          context.tr('Online'),
          Colors.green,
          Icons.check_circle,
        ),
      RemoteConnectionPhase.connecting => (
          context.tr('Connecting'),
          Colors.orange,
          Icons.sync,
        ),
      RemoteConnectionPhase.waking => (
          context.tr('Waking'),
          Colors.orange,
          Icons.power_settings_new,
        ),
      RemoteConnectionPhase.identityMismatch => (
          context.tr('Identity alert'),
          Colors.red,
          Icons.gpp_bad,
        ),
      RemoteConnectionPhase.unauthorized => (
          context.tr('Pair again'),
          Colors.red,
          Icons.lock_reset,
        ),
      RemoteConnectionPhase.offline => (
          context.tr('Offline'),
          Colors.grey,
          Icons.cloud_off,
        ),
      RemoteConnectionPhase.disconnected => (
          context.tr('Disconnected'),
          Colors.grey,
          Icons.link_off,
        ),
    };
    return Chip(
      avatar: Icon(icon, color: color, size: 18),
      label: Text(label),
      visualDensity: VisualDensity.compact,
    );
  }
}

class _RemotePage extends StatefulWidget {
  const _RemotePage({
    required this.controller,
    required this.demo,
    required this.touchpadSettings,
  });

  final PhoneRemoteController? controller;
  final bool demo;
  final TouchpadSettings touchpadSettings;

  @override
  State<_RemotePage> createState() => _RemotePageState();
}

class _RemotePageState extends State<_RemotePage> {
  String _lastAction = 'Touch and move to control the pointer';
  bool _touchpad = true;
  late final PointerMoveDispatcher _moves;
  late final PointerMoveDispatcher _wheel;
  String? _lastDispatcherError;
  DateTime? _lastDispatcherErrorAt;

  @override
  void initState() {
    super.initState();
    _moves = PointerMoveDispatcher(
      send: (dx, dy) =>
          widget.controller?.sendMouseMove(dx, dy) ?? Future.value(),
      onError: _handleDispatcherError,
    );
    _wheel = PointerMoveDispatcher(
      send: (_, delta) =>
          widget.controller?.sendMouseWheel(delta) ?? Future.value(),
      onError: _handleDispatcherError,
    );
  }

  @override
  void dispose() {
    _moves.dispose();
    _wheel.dispose();
    super.dispose();
  }

  void _handleDispatcherError(Object error) {
    if (!mounted) {
      return;
    }
    final message = '$error';
    final now = DateTime.now();
    if (_lastDispatcherError == message &&
        _lastDispatcherErrorAt != null &&
        now.difference(_lastDispatcherErrorAt!) < const Duration(seconds: 2)) {
      return;
    }
    _lastDispatcherError = message;
    _lastDispatcherErrorAt = now;
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(content: Text('$error')),
    );
  }

  void _setLastAction(String label) {
    if (_lastAction == label) {
      return;
    }
    setState(() => _lastAction = label);
  }

  Future<void> _invoke(
    String label,
    Future<void> Function(PhoneRemoteController controller) operation,
  ) async {
    _setLastAction(label);
    if (widget.demo) {
      return;
    }
    final controller = widget.controller;
    if (controller == null) {
      return;
    }
    try {
      await operation(controller);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final quickControls = <Widget>[
      _QuickControl(
        label: context.tr('Back'),
        icon: Icons.arrow_back,
        onTap: () => _invoke(
          context.tr('Back'),
          (controller) => controller.sendAction('escape'),
        ),
      ),
      _QuickControl(
        label: context.tr('Keyboard'),
        icon: Icons.keyboard,
        onTap: () => _openKeyboard(context),
      ),
      _QuickControl(
        label: context.tr('Fullscreen'),
        icon: Icons.fullscreen,
        onTap: () => _invoke(
          context.tr('Fullscreen'),
          (controller) => controller.sendAction('f11'),
        ),
      ),
      _QuickControl(
        label: context.tr('Desktop'),
        icon: Icons.desktop_windows_outlined,
        onTap: () => _invoke(
          context.tr('Desktop'),
          (controller) => controller.sendAction('desktop'),
        ),
      ),
      _QuickControl(
        label: context.tr('Close active window'),
        icon: Icons.close,
        onTap: () => _invoke(
          context.tr('Close active window'),
          (controller) => controller.sendAction('close_active'),
        ),
      ),
      _QuickControl(
        label: context.tr('Volume down'),
        icon: Icons.volume_down,
        onTap: () => _invoke(
          context.tr('Volume down'),
          (controller) => controller.sendAction('volume_down'),
        ),
      ),
      _QuickControl(
        label: context.tr('Mute'),
        icon: Icons.volume_off,
        onTap: () => _invoke(
          context.tr('Mute'),
          (controller) => controller.sendAction('volume_mute'),
        ),
      ),
      _QuickControl(
        label: context.tr('Volume up'),
        icon: Icons.volume_up,
        onTap: () => _invoke(
          context.tr('Volume up'),
          (controller) => controller.sendAction('volume_up'),
        ),
      ),
      _QuickControl(
        label: context.tr('Previous'),
        icon: Icons.skip_previous,
        onTap: () => _invoke(
          context.tr('Previous'),
          (controller) => controller.sendAction('media_previous'),
        ),
      ),
      _QuickControl(
        label: context.tr('Play / Pause'),
        icon: Icons.play_arrow,
        onTap: () => _invoke(
          context.tr('Play / Pause'),
          (controller) => controller.sendAction('media_play_pause'),
        ),
      ),
      _QuickControl(
        label: context.tr('Next'),
        icon: Icons.skip_next,
        onTap: () => _invoke(
          context.tr('Next'),
          (controller) => controller.sendAction('media_next'),
        ),
      ),
    ];

    return Padding(
      key: const ValueKey<String>('remote-page'),
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Column(
        children: <Widget>[
          if (!widget.demo && widget.controller != null)
            _ConnectionBanner(controller: widget.controller!),
          SegmentedButton<bool>(
            segments: <ButtonSegment<bool>>[
              ButtonSegment<bool>(
                value: true,
                icon: const Icon(Icons.touch_app_rounded),
                label: Text(context.tr('Touchpad')),
              ),
              ButtonSegment<bool>(
                value: false,
                icon: const Icon(Icons.gamepad_rounded),
                label: Text(context.tr('D-pad')),
              ),
            ],
            selected: <bool>{_touchpad},
            onSelectionChanged: (selection) {
              setState(() => _touchpad = selection.single);
            },
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _touchpad
                ? _TouchpadSurface(
                    status: context.tr(_lastAction),
                    onMove: (delta) {
                      _setLastAction(context.tr('Pointer move'));
                      if (!widget.demo &&
                          (widget.controller?.connected ?? false)) {
                        final sensitivity =
                            widget.touchpadSettings.pointerSensitivity;
                        _moves.add(
                          delta.dx * 1.35 * sensitivity,
                          delta.dy * 1.35 * sensitivity,
                        );
                      }
                    },
                    onWheel: (delta) {
                      _setLastAction(context.tr('Scroll'));
                      if (!widget.demo &&
                          (widget.controller?.connected ?? false)) {
                        _wheel.add(
                          0,
                          delta * widget.touchpadSettings.scrollSensitivity,
                        );
                      }
                    },
                    onLeftClick: () => _invoke(
                      context.tr('Left click'),
                      (controller) => controller.sendMouseClick(),
                    ),
                    onRightClick: () => _invoke(
                      context.tr('Right click'),
                      (controller) =>
                          controller.sendMouseClick(button: 'right'),
                    ),
                    onDoubleClick: () => _invoke(
                      context.tr('Double click'),
                      (controller) => controller.sendMouseDoubleClick(),
                    ),
                  )
                : _Dpad(
                    onAction: (label, action) => _invoke(
                      label,
                      (controller) => controller.sendAction(action),
                    ),
                  ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 140,
            child: Column(
              children: <Widget>[
                for (var row = 0; row < 3; row++) ...<Widget>[
                  if (row > 0) const SizedBox(height: 4),
                  Expanded(
                    child: Row(
                      children: <Widget>[
                        for (var column = 0; column < 4; column++) ...<Widget>[
                          if (column > 0) const SizedBox(width: 8),
                          Expanded(
                            child: row * 4 + column < quickControls.length
                                ? quickControls[row * 4 + column]
                                : const SizedBox.shrink(),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openKeyboard(BuildContext context) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (sheetContext) => _KeyboardSheet(
        onAction: (label, action) =>
            _invoke(label, (controller) => controller.sendAction(action)),
        onSend: (text) => _invoke(
            context.tr('Text sent'), (controller) => controller.sendText(text)),
      ),
    );
  }
}

class _KeyboardSheet extends StatefulWidget {
  const _KeyboardSheet({required this.onAction, required this.onSend});

  final Future<void> Function(String label, String action) onAction;
  final Future<void> Function(String text) onSend;

  @override
  State<_KeyboardSheet> createState() => _KeyboardSheetState();
}

class _KeyboardSheetState extends State<_KeyboardSheet> {
  final TextEditingController _input = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text;
    if (text.isEmpty || _sending) {
      return;
    }
    setState(() => _sending = true);
    await widget.onSend(text);
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        MediaQuery.viewInsetsOf(context).bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          TextField(
            controller: _input,
            autofocus: true,
            maxLength: 2000,
            minLines: 1,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: context.tr('Text Input'),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: <Widget>[
              for (final item in <(String, String, IconData)>[
                (context.tr('Enter'), 'enter', Icons.keyboard_return),
                (context.tr('Tab'), 'tab', Icons.keyboard_tab),
                (context.tr('Escape'), 'escape', Icons.close),
                (context.tr('Backspace'), 'back', Icons.backspace_outlined),
              ])
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 2),
                    child: Semantics(
                      button: true,
                      label: item.$1,
                      child: Tooltip(
                        message: item.$1,
                        excludeFromSemantics: true,
                        child: OutlinedButton(
                          onPressed: _sending
                              ? null
                              : () => widget.onAction(item.$1, item.$2),
                          child: ExcludeSemantics(child: Icon(item.$3)),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _sending ? null : _send,
              icon: const Icon(Icons.send),
              label: Text(context.tr('Send')),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConnectionBanner extends StatelessWidget {
  const _ConnectionBanner({required this.controller});

  final PhoneRemoteController controller;

  @override
  Widget build(BuildContext context) {
    if (controller.connected && controller.connectionError == null) {
      return const SizedBox.shrink();
    }
    final busy =
        controller.connectionPhase == RemoteConnectionPhase.connecting ||
            controller.connectionPhase == RemoteConnectionPhase.waking;
    final identityAlert =
        controller.connectionPhase == RemoteConnectionPhase.identityMismatch;
    return Card(
      color: identityAlert
          ? Theme.of(context).colorScheme.errorContainer
          : Theme.of(context).colorScheme.surfaceContainerHighest,
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: <Widget>[
            if (busy)
              const SizedBox.square(
                dimension: 22,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              Icon(identityAlert ? Icons.gpp_bad : Icons.info_outline),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                busy
                    ? controller.connectionPhase == RemoteConnectionPhase.waking
                        ? context.tr('Sending Wake on LAN…')
                        : context.tr('Connecting securely…')
                    : controller.connectionError ??
                        context.tr('Not connected.'),
              ),
            ),
            if (!busy && !identityAlert)
              TextButton(
                onPressed: controller.reconnect,
                child: Text(context.tr('Retry')),
              ),
          ],
        ),
      ),
    );
  }
}

class _TouchpadSurface extends StatefulWidget {
  const _TouchpadSurface({
    required this.status,
    required this.onMove,
    required this.onWheel,
    required this.onLeftClick,
    required this.onRightClick,
    required this.onDoubleClick,
  });

  final String status;
  final ValueChanged<Offset> onMove;
  final ValueChanged<double> onWheel;
  final VoidCallback onLeftClick;
  final VoidCallback onRightClick;
  final VoidCallback onDoubleClick;

  @override
  State<_TouchpadSurface> createState() => _TouchpadSurfaceState();
}

class _TouchpadSurfaceState extends State<_TouchpadSurface> {
  final Map<int, Offset> _positions = <int, Offset>{};
  int _maxPointers = 0;
  double _travel = 0;
  Timer? _singleTapTimer;

  @override
  void dispose() {
    _singleTapTimer?.cancel();
    super.dispose();
  }

  void _down(PointerDownEvent event) {
    if (_positions.isEmpty) {
      _maxPointers = 0;
      _travel = 0;
    }
    _positions[event.pointer] = event.localPosition;
    _maxPointers =
        _positions.length > _maxPointers ? _positions.length : _maxPointers;
  }

  void _move(PointerMoveEvent event) {
    final previous = _positions[event.pointer];
    if (previous == null) {
      return;
    }
    final delta = event.localPosition - previous;
    _positions[event.pointer] = event.localPosition;
    _travel += delta.distance;
    if (_positions.length >= 2) {
      if (delta.dy.abs() >= 0.5) {
        widget.onWheel(-delta.dy * 2.5);
      }
    } else if (_maxPointers == 1) {
      widget.onMove(delta);
    }
  }

  void _up(PointerEvent event) {
    _positions.remove(event.pointer);
    if (_positions.isNotEmpty) {
      return;
    }
    if (_travel < 12) {
      if (_maxPointers >= 2) {
        _singleTapTimer?.cancel();
        widget.onRightClick();
      } else {
        _tap();
      }
    }
  }

  void _tap() {
    if (_singleTapTimer?.isActive ?? false) {
      _singleTapTimer?.cancel();
      _singleTapTimer = null;
      widget.onDoubleClick();
      return;
    }
    _singleTapTimer = Timer(const Duration(milliseconds: 260), () {
      _singleTapTimer = null;
      widget.onLeftClick();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: context.tr(
        'Touchpad. One finger moves. Tap clicks. Two-finger tap right-clicks. Two-finger drag scrolls.',
      ),
      child: RawGestureDetector(
        key: const ValueKey<String>('touchpad-surface'),
        behavior: HitTestBehavior.opaque,
        gestures: <Type, GestureRecognizerFactory>{
          EagerGestureRecognizer:
              GestureRecognizerFactoryWithHandlers<EagerGestureRecognizer>(
            EagerGestureRecognizer.new,
            (_) {},
          ),
        },
        child: Listener(
          behavior: HitTestBehavior.opaque,
          onPointerDown: _down,
          onPointerMove: _move,
          onPointerUp: _up,
          onPointerCancel: _up,
          child: Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            child: Center(
              child: Text(
                '${context.tr('Touchpad')}\n\n${widget.status}',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Dpad extends StatelessWidget {
  const _Dpad({required this.onAction});

  final void Function(String label, String action) onAction;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        _RoundControl(
          icon: Icons.keyboard_arrow_up,
          onTap: () => onAction(context.tr('Up'), 'up'),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            _RoundControl(
              icon: Icons.keyboard_arrow_left,
              onTap: () => onAction(context.tr('Left'), 'left'),
            ),
            _RoundControl(
              icon: Icons.circle_outlined,
              onTap: () => onAction(context.tr('Enter'), 'enter'),
            ),
            _RoundControl(
              icon: Icons.keyboard_arrow_right,
              onTap: () => onAction(context.tr('Right'), 'right'),
            ),
          ],
        ),
        _RoundControl(
          icon: Icons.keyboard_arrow_down,
          onTap: () => onAction(context.tr('Down'), 'down'),
        ),
      ],
    );
  }
}

class _RoundControl extends StatefulWidget {
  const _RoundControl({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  State<_RoundControl> createState() => _RoundControlState();
}

class _RoundControlState extends State<_RoundControl> {
  Timer? _holdTimer;
  Timer? _repeatTimer;
  bool _pressed = false;
  bool _repeated = false;

  @override
  void dispose() {
    _cancelTimers();
    super.dispose();
  }

  void _down(PointerDownEvent _) {
    _cancelTimers();
    setState(() {
      _pressed = true;
      _repeated = false;
    });
    _holdTimer = Timer(const Duration(milliseconds: 450), () {
      _repeated = true;
      _fire();
      _repeatTimer = Timer.periodic(
        const Duration(milliseconds: 120),
        (_) => widget.onTap(),
      );
    });
  }

  void _up(PointerEvent _) {
    final repeated = _repeated;
    _cancelTimers();
    if (mounted) {
      setState(() => _pressed = false);
    }
    if (!repeated) {
      _fire();
    }
  }

  void _fire() {
    unawaited(HapticFeedback.selectionClick());
    widget.onTap();
  }

  void _cancel(PointerEvent _) {
    _cancelTimers();
    if (mounted) {
      setState(() => _pressed = false);
    }
  }

  void _cancelTimers() {
    _holdTimer?.cancel();
    _repeatTimer?.cancel();
    _holdTimer = null;
    _repeatTimer = null;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(3),
      child: Semantics(
        button: true,
        child: Listener(
          onPointerDown: _down,
          onPointerUp: _up,
          onPointerCancel: _cancel,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 90),
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _pressed
                  ? Theme.of(context).colorScheme.secondaryContainer
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: Icon(widget.icon, size: 32),
          ),
        ),
      ),
    );
  }
}

class _QuickControl extends StatelessWidget {
  const _QuickControl({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: label,
      child: Tooltip(
        message: label,
        excludeFromSemantics: true,
        child: SizedBox.expand(
          child: FilledButton.tonal(
            style: FilledButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            onPressed: onTap,
            child: ExcludeSemantics(child: Icon(icon)),
          ),
        ),
      ),
    );
  }
}

class _AppsPage extends StatelessWidget {
  const _AppsPage({required this.controller, required this.demo});

  final PhoneRemoteController? controller;
  final bool demo;

  @override
  Widget build(BuildContext context) {
    if (demo) {
      final apps = <(String, IconData)>[
        ('Steam', Icons.sports_esports_rounded),
        (context.tr('Browser'), Icons.public_rounded),
        (context.tr('Music'), Icons.music_note_rounded),
        (context.tr('Movies'), Icons.movie_rounded),
      ];
      return GridView.count(
        padding: const EdgeInsets.all(24),
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        children: <Widget>[
          for (final app in apps)
            _AppCard(
              name: app.$1,
              icon: app.$2,
              available: true,
              onTap: () => ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                    content: Text(
                  Localizations.localeOf(context).languageCode == 'zh'
                      ? '演示模式已启动 ${app.$1}'
                      : '${app.$1} launched in Demo',
                )),
              ),
            ),
        ],
      );
    }
    final current = controller;
    final apps = current?.apps ?? const [];
    if (current == null || !current.connected) {
      return Center(
          child: Text(context.tr('Connect to a PC to load approved apps.')));
    }
    if (apps.isEmpty) {
      return Center(
          child: Text(context.tr('No approved Windows apps are configured.')));
    }
    return GridView.count(
      padding: const EdgeInsets.all(24),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      children: <Widget>[
        for (final app in apps)
          _AppCard(
            name: app.name,
            iconBytes: app.iconBytes,
            available: app.available,
            onTap: () => _launch(context, current, app.id, app.name),
          ),
      ],
    );
  }

  Future<void> _launch(
    BuildContext context,
    PhoneRemoteController controller,
    String id,
    String name,
  ) async {
    try {
      await controller.launchApp(id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
            Localizations.localeOf(context).languageCode == 'zh'
                ? '$name 已启动'
                : '$name launched',
          )),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }
}

class _AppCard extends StatelessWidget {
  const _AppCard({
    required this.name,
    required this.available,
    required this.onTap,
    this.icon,
    this.iconBytes,
  });

  final String name;
  final IconData? icon;
  final Uint8List? iconBytes;
  final bool available;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: available ? onTap : null,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            if (iconBytes != null)
              Image.memory(
                iconBytes!,
                key: ValueKey<String>('app-icon-$name'),
                width: 52,
                height: 52,
                fit: BoxFit.contain,
                errorBuilder: (_, _, _) => const Icon(
                  Icons.desktop_windows_rounded,
                  size: 48,
                ),
              )
            else
              Icon(icon ?? Icons.desktop_windows_rounded, size: 48),
            const SizedBox(height: 12),
            Text(name),
            if (!available)
              Text(context.tr('Unavailable'),
                  style: const TextStyle(color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}

class _DevicesPage extends StatelessWidget {
  const _DevicesPage({required this.controller, required this.demo});

  final PhoneRemoteController? controller;
  final bool demo;

  @override
  Widget build(BuildContext context) {
    if (demo) {
      return ListTile(
        leading: const CircleAvatar(child: Icon(Icons.computer_rounded)),
        title: Text(context.tr('Living Room PC')),
        subtitle: Text('${context.tr('Demo')} • ${context.tr('Online')}'),
        trailing: const Icon(Icons.star_rounded),
      );
    }
    final devices = controller?.devices ?? const <Device>[];
    final selectedId = controller?.selectedDevice?.id;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        for (final device in devices)
          Card(
            child: ListTile(
              selected: device.id == selectedId,
              leading: const CircleAvatar(child: Icon(Icons.computer_rounded)),
              title: Text(device.name),
              subtitle: Text(
                device.id == selectedId && (controller?.connected ?? false)
                    ? '${device.host}:${device.port} • ${context.tr('Online')}'
                    : '${device.host}:${device.port} • ${context.tr('Saved securely')}',
              ),
              trailing: IconButton(
                tooltip: device.favorite
                    ? context.tr('Remove favorite')
                    : context.tr('Make favorite'),
                onPressed: () => controller?.toggleFavorite(device),
                icon: Icon(
                  device.favorite
                      ? Icons.star_rounded
                      : Icons.star_outline_rounded,
                ),
              ),
              onTap: () => controller?.connect(device),
              onLongPress: () => _confirmRemove(context, device),
            ),
          ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () {
            final currentController = controller;
            if (currentController != null) {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => FindComputersScreen(
                    controller: currentController,
                  ),
                ),
              );
            }
          },
          icon: const Icon(Icons.add_rounded),
          label: Text(context.tr('Add PC')),
        ),
      ],
    );
  }

  Future<void> _confirmRemove(BuildContext context, Device device) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.tr('Forget this PC?')),
        content: Text(
          Localizations.localeOf(context).languageCode == 'zh'
              ? '将从此手机中移除 ${device.name} 及其本地凭据。'
              : '${device.name} and its local credential will be removed from this phone.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(context.tr('Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(context.tr('Forget')),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await controller?.remove(device);
    }
  }
}

class _SettingsPage extends StatelessWidget {
  const _SettingsPage({
    required this.controller,
    required this.demo,
    required this.touchpadSettings,
    required this.onTouchpadSettingsChanged,
    required this.onTouchpadSettingsChangeEnd,
  });

  final PhoneRemoteController? controller;
  final bool demo;
  final TouchpadSettings touchpadSettings;
  final ValueChanged<TouchpadSettings> onTouchpadSettingsChanged;
  final VoidCallback onTouchpadSettingsChangeEnd;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        ListTile(
          leading: const Icon(Icons.security_rounded),
          title: Text(context.tr('Local and private')),
          subtitle: Text(
            context.tr(
                'No cloud account, analytics, ads, or keyboard content collection.'),
          ),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.settings_input_antenna_rounded),
          title: Text(context.tr('Wake on LAN')),
          onTap: () => _wake(context),
        ),
        ListTile(
          leading: const Icon(Icons.bedtime_outlined),
          title: Text(context.tr('Standby (S3)')),
          onTap: () => _power(context, 'sleep', context.tr('Standby')),
        ),
        ListTile(
          leading: const Icon(Icons.pause_circle_outline),
          title: Text(context.tr('Hibernate')),
          onTap: () => _power(context, 'hibernate', context.tr('Hibernate')),
        ),
        ListTile(
          leading: const Icon(Icons.restart_alt),
          title: Text(context.tr('Restart')),
          onTap: () => _confirmPower(context, 'restart', context.tr('Restart')),
        ),
        ListTile(
          leading: const Icon(Icons.power_settings_new),
          title: Text(context.tr('Shut down')),
          onTap: () =>
              _confirmPower(context, 'shutdown', context.tr('Shut down')),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.mouse_outlined),
          title: Text(context.tr('Pointer sensitivity')),
          subtitle: Slider(
            value: touchpadSettings.pointerSensitivity,
            min: TouchpadSettings.minimumSensitivity,
            max: TouchpadSettings.maximumSensitivity,
            divisions: 6,
            label: '${touchpadSettings.pointerSensitivity.toStringAsFixed(2)}×',
            onChanged: (value) => onTouchpadSettingsChanged(
              touchpadSettings.copyWith(pointerSensitivity: value),
            ),
            onChangeEnd: (_) => onTouchpadSettingsChangeEnd(),
          ),
          trailing: Text(
            '${touchpadSettings.pointerSensitivity.toStringAsFixed(2)}×',
          ),
        ),
        ListTile(
          leading: const Icon(Icons.swap_vert_rounded),
          title: Text(context.tr('Scroll sensitivity')),
          subtitle: Slider(
            value: touchpadSettings.scrollSensitivity,
            min: TouchpadSettings.minimumSensitivity,
            max: TouchpadSettings.maximumSensitivity,
            divisions: 6,
            label: '${touchpadSettings.scrollSensitivity.toStringAsFixed(2)}×',
            onChanged: (value) => onTouchpadSettingsChanged(
              touchpadSettings.copyWith(scrollSensitivity: value),
            ),
            onChangeEnd: (_) => onTouchpadSettingsChangeEnd(),
          ),
          trailing: Text(
            '${touchpadSettings.scrollSensitivity.toStringAsFixed(2)}×',
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: () {
              onTouchpadSettingsChanged(const TouchpadSettings());
              onTouchpadSettingsChangeEnd();
            },
            icon: const Icon(Icons.restore_rounded),
            label: Text(context.tr('Reset touchpad settings')),
          ),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.language_rounded),
          title: Text(context.tr('Language')),
          subtitle: Align(
            alignment: Alignment.centerLeft,
            child: SegmentedButton<String>(
              segments: <ButtonSegment<String>>[
                ButtonSegment<String>(
                    value: 'zh', label: Text(context.tr('Chinese'))),
                ButtonSegment<String>(
                    value: 'en', label: Text(context.tr('English'))),
              ],
              selected: <String>{Localizations.localeOf(context).languageCode},
              onSelectionChanged: (selection) =>
                  AppLanguageScope.maybeOf(context)
                      ?.onLocaleChanged(Locale(selection.single)),
            ),
          ),
        ),
        const Divider(),
        const ListTile(
          leading: Icon(Icons.info_outline_rounded),
          title: Text('Phone Remote 1.3.0'),
          subtitle: Text('Mobile API v1'),
        ),
      ],
    );
  }

  Future<void> _wake(BuildContext context) async {
    if (demo) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('Wake on LAN simulated in Demo'))),
      );
      return;
    }
    try {
      await controller?.wakeAndConnect();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.tr('PC connection is ready'))),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }

  Future<void> _confirmPower(
    BuildContext context,
    String action,
    String label,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(
          Localizations.localeOf(context).languageCode == 'zh'
              ? '确认$label这台电脑？'
              : '$label this PC?',
        ),
        content:
            Text(context.tr('Unsaved work on the Windows PC may be lost.')),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(context.tr('Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(label),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await _power(context, action, label);
    }
  }

  Future<void> _power(
    BuildContext context,
    String action,
    String label,
  ) async {
    if (demo) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
          Localizations.localeOf(context).languageCode == 'zh'
              ? '演示模式已模拟$label'
              : '$label simulated in Demo',
        )),
      );
      return;
    }
    try {
      await controller?.sendPowerAction(action);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
            Localizations.localeOf(context).languageCode == 'zh'
                ? '$label命令已发送'
                : '$label command sent',
          )),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }
}
