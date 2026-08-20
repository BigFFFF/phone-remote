import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../application/phone_remote_controller.dart';
import '../models/device.dart';
import '../services/pointer_move_dispatcher.dart';
import 'find_computers_screen.dart';

class RemoteShell extends StatefulWidget {
  const RemoteShell({
    super.key,
    required this.controller,
    this.demo = false,
  });

  const RemoteShell.demo({super.key})
      : controller = null,
        demo = true;

  final PhoneRemoteController? controller;
  final bool demo;

  @override
  State<RemoteShell> createState() => _RemoteShellState();
}

class _RemoteShellState extends State<RemoteShell> {
  int _index = 0;

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
      _RemotePage(controller: widget.controller, demo: widget.demo),
      _AppsPage(controller: widget.controller, demo: widget.demo),
      _DevicesPage(controller: widget.controller, demo: widget.demo),
      _SettingsPage(controller: widget.controller, demo: widget.demo),
    ];
    return Scaffold(
      appBar: AppBar(
        title:
            Text(widget.demo ? 'Phone Remote' : device?.name ?? 'Phone Remote'),
        actions: <Widget>[
          if (widget.demo)
            const Padding(
              padding: EdgeInsets.only(right: 16),
              child: Chip(label: Text('Demo')),
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
        destinations: const <NavigationDestination>[
          NavigationDestination(
            icon: Icon(Icons.touch_app_outlined),
            selectedIcon: Icon(Icons.touch_app_rounded),
            label: 'Remote',
          ),
          NavigationDestination(
            icon: Icon(Icons.apps_outlined),
            selectedIcon: Icon(Icons.apps_rounded),
            label: 'Apps',
          ),
          NavigationDestination(
            icon: Icon(Icons.devices_outlined),
            selectedIcon: Icon(Icons.devices_rounded),
            label: 'Devices',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings_rounded),
            label: 'Settings',
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
          'Online',
          Colors.green,
          Icons.check_circle,
        ),
      RemoteConnectionPhase.connecting => (
          'Connecting',
          Colors.orange,
          Icons.sync,
        ),
      RemoteConnectionPhase.waking => (
          'Waking',
          Colors.orange,
          Icons.power_settings_new,
        ),
      RemoteConnectionPhase.identityMismatch => (
          'Identity alert',
          Colors.red,
          Icons.gpp_bad,
        ),
      RemoteConnectionPhase.unauthorized => (
          'Pair again',
          Colors.red,
          Icons.lock_reset,
        ),
      RemoteConnectionPhase.offline => (
          'Offline',
          Colors.grey,
          Icons.cloud_off,
        ),
      RemoteConnectionPhase.disconnected => (
          'Disconnected',
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
  const _RemotePage({required this.controller, required this.demo});

  final PhoneRemoteController? controller;
  final bool demo;

  @override
  State<_RemotePage> createState() => _RemotePageState();
}

class _RemotePageState extends State<_RemotePage> {
  String _lastAction = 'Touch and move to control the pointer';
  bool _touchpad = true;
  late final PointerMoveDispatcher _moves;
  late final PointerMoveDispatcher _wheel;

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
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$error')),
    );
  }

  Future<void> _invoke(
    String label,
    Future<void> Function(PhoneRemoteController controller) operation,
  ) async {
    setState(() => _lastAction = label);
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
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        if (!widget.demo && widget.controller != null)
          _ConnectionBanner(controller: widget.controller!),
        SegmentedButton<bool>(
          segments: const <ButtonSegment<bool>>[
            ButtonSegment<bool>(
              value: true,
              icon: Icon(Icons.touch_app_rounded),
              label: Text('Touchpad'),
            ),
            ButtonSegment<bool>(
              value: false,
              icon: Icon(Icons.gamepad_rounded),
              label: Text('D-pad'),
            ),
          ],
          selected: <bool>{_touchpad},
          onSelectionChanged: (selection) {
            setState(() => _touchpad = selection.single);
          },
        ),
        const SizedBox(height: 16),
        if (_touchpad)
          _TouchpadSurface(
            status: _lastAction,
            onMove: (delta) {
              setState(() => _lastAction = 'Pointer move');
              if (!widget.demo) {
                _moves.add(delta.dx * 1.35, delta.dy * 1.35);
              }
            },
            onWheel: (delta) {
              setState(() => _lastAction = 'Scroll');
              if (!widget.demo) {
                _wheel.add(0, delta);
              }
            },
            onLeftClick: () => _invoke(
              'Left click',
              (controller) => controller.sendMouseClick(),
            ),
            onRightClick: () => _invoke(
              'Right click',
              (controller) => controller.sendMouseClick(button: 'right'),
            ),
            onDoubleClick: () => _invoke(
              'Double click',
              (controller) => controller.sendMouseDoubleClick(),
            ),
          )
        else
          _Dpad(
            onAction: (label, action) =>
                _invoke(label, (controller) => controller.sendAction(action)),
          ),
        const SizedBox(height: 16),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 1.8,
          children: <Widget>[
            _QuickControl(
              label: 'Back',
              icon: Icons.arrow_back,
              onTap: () => _invoke(
                'Back',
                (controller) => controller.sendAction('escape'),
              ),
            ),
            _QuickControl(
              label: 'Keyboard',
              icon: Icons.keyboard,
              onTap: () => _openKeyboard(context),
            ),
            _QuickControl(
              label: 'Full',
              icon: Icons.fullscreen,
              onTap: () => _invoke(
                'Fullscreen',
                (controller) => controller.sendAction('f11'),
              ),
            ),
            _QuickControl(
              label: 'Vol−',
              icon: Icons.volume_down,
              onTap: () => _invoke(
                'Volume down',
                (controller) => controller.sendAction('volume_down'),
              ),
            ),
            _QuickControl(
              label: 'Mute',
              icon: Icons.volume_off,
              onTap: () => _invoke(
                'Mute',
                (controller) => controller.sendAction('volume_mute'),
              ),
            ),
            _QuickControl(
              label: 'Vol+',
              icon: Icons.volume_up,
              onTap: () => _invoke(
                'Volume up',
                (controller) => controller.sendAction('volume_up'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: <Widget>[
            Expanded(
              child: _QuickControl(
                label: 'Previous',
                icon: Icons.skip_previous,
                onTap: () => _invoke(
                  'Previous',
                  (controller) => controller.sendAction('media_previous'),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _QuickControl(
                label: 'Play',
                icon: Icons.play_arrow,
                onTap: () => _invoke(
                  'Play / Pause',
                  (controller) => controller.sendAction('media_play_pause'),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _QuickControl(
                label: 'Next',
                icon: Icons.skip_next,
                onTap: () => _invoke(
                  'Next',
                  (controller) => controller.sendAction('media_next'),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _openKeyboard(BuildContext context) async {
    final input = TextEditingController();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          MediaQuery.viewInsetsOf(sheetContext).bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            TextField(
              controller: input,
              autofocus: true,
              maxLength: 2000,
              minLines: 1,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Text Input',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                for (final item in const <(String, String)>[
                  ('Enter', 'enter'),
                  ('Tab', 'tab'),
                  ('Escape', 'escape'),
                  ('⌫', 'back'),
                ])
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: OutlinedButton(
                        onPressed: () => _invoke(
                          item.$1,
                          (controller) => controller.sendAction(item.$2),
                        ),
                        child: Text(item.$1),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () async {
                  final text = input.text;
                  if (text.isEmpty) {
                    return;
                  }
                  await _invoke(
                    'Text sent',
                    (controller) => controller.sendText(text),
                  );
                  if (sheetContext.mounted) {
                    Navigator.of(sheetContext).pop();
                  }
                },
                icon: const Icon(Icons.send),
                label: const Text('Send'),
              ),
            ),
          ],
        ),
      ),
    );
    input.dispose();
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
                        ? 'Sending Wake on LAN…'
                        : 'Connecting securely…'
                    : controller.connectionError ?? 'Not connected.',
              ),
            ),
            if (!busy && !identityAlert)
              TextButton(
                onPressed: controller.reconnect,
                child: const Text('Retry'),
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
      label:
          'Touchpad. One finger moves. Tap clicks. Two-finger tap right-clicks. Two-finger drag scrolls.',
      child: Listener(
        behavior: HitTestBehavior.opaque,
        onPointerDown: _down,
        onPointerMove: _move,
        onPointerUp: _up,
        onPointerCancel: _up,
        child: Container(
          height: 330,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          child: Center(
            child: Text(
              'Touchpad\n\n${widget.status}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
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
    return SizedBox(
      height: 330,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          _RoundControl(
            icon: Icons.keyboard_arrow_up,
            onTap: () => onAction('Up', 'up'),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              _RoundControl(
                icon: Icons.keyboard_arrow_left,
                onTap: () => onAction('Left', 'left'),
              ),
              _RoundControl(
                icon: Icons.circle_outlined,
                onTap: () => onAction('Enter', 'enter'),
              ),
              _RoundControl(
                icon: Icons.keyboard_arrow_right,
                onTap: () => onAction('Right', 'right'),
              ),
            ],
          ),
          _RoundControl(
            icon: Icons.keyboard_arrow_down,
            onTap: () => onAction('Down', 'down'),
          ),
        ],
      ),
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
      padding: const EdgeInsets.all(4),
      child: Semantics(
        button: true,
        child: Listener(
          onPointerDown: _down,
          onPointerUp: _up,
          onPointerCancel: _cancel,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 90),
            width: 66,
            height: 66,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _pressed
                  ? Theme.of(context).colorScheme.secondaryContainer
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: Icon(widget.icon, size: 34),
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
    return FilledButton.tonalIcon(
      onPressed: onTap,
      icon: Icon(icon),
      label: Text(label),
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
      const apps = <(String, IconData)>[
        ('Steam', Icons.sports_esports_rounded),
        ('Browser', Icons.public_rounded),
        ('Music', Icons.music_note_rounded),
        ('Movies', Icons.movie_rounded),
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
                SnackBar(content: Text('${app.$1} launched in Demo')),
              ),
            ),
        ],
      );
    }
    final current = controller;
    final apps = current?.apps ?? const [];
    if (current == null || !current.connected) {
      return const Center(
          child: Text('Connect to a PC to load approved apps.'));
    }
    if (apps.isEmpty) {
      return const Center(
          child: Text('No approved Windows apps are configured.'));
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
            icon: Icons.desktop_windows_rounded,
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
          SnackBar(content: Text('$name launched')),
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
    required this.icon,
    required this.available,
    required this.onTap,
  });

  final String name;
  final IconData icon;
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
            Icon(icon, size: 48),
            const SizedBox(height: 12),
            Text(name),
            if (!available)
              const Text('Unavailable', style: TextStyle(color: Colors.grey)),
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
      return const ListTile(
        leading: CircleAvatar(child: Icon(Icons.computer_rounded)),
        title: Text('Living Room PC'),
        subtitle: Text('Demo • Online'),
        trailing: Icon(Icons.star_rounded),
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
                    ? '${device.host}:${device.port} • Online'
                    : '${device.host}:${device.port} • Saved securely',
              ),
              trailing: IconButton(
                tooltip: device.favorite ? 'Remove favorite' : 'Make favorite',
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
          label: const Text('Add PC'),
        ),
      ],
    );
  }

  Future<void> _confirmRemove(BuildContext context, Device device) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Forget this PC?'),
        content: Text(
          '${device.name} and its local credential will be removed from this phone.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Forget'),
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
  const _SettingsPage({required this.controller, required this.demo});

  final PhoneRemoteController? controller;
  final bool demo;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        const ListTile(
          leading: Icon(Icons.security_rounded),
          title: Text('Local and private'),
          subtitle: Text(
            'No cloud account, analytics, ads, or keyboard content collection.',
          ),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.bedtime_outlined),
          title: const Text('Sleep'),
          onTap: () => _power(context, 'sleep', 'Sleep'),
        ),
        ListTile(
          leading: const Icon(Icons.pause_circle_outline),
          title: const Text('Hibernate'),
          onTap: () => _power(context, 'hibernate', 'Hibernate'),
        ),
        ListTile(
          leading: const Icon(Icons.restart_alt),
          title: const Text('Restart'),
          onTap: () => _confirmPower(context, 'restart', 'Restart'),
        ),
        ListTile(
          leading: const Icon(Icons.power_settings_new),
          title: const Text('Shut down'),
          onTap: () => _confirmPower(context, 'shutdown', 'Shut down'),
        ),
        const Divider(),
        const ListTile(
          leading: Icon(Icons.info_outline_rounded),
          title: Text('Phone Remote 1.0.0'),
          subtitle: Text('Mobile API v1'),
        ),
      ],
    );
  }

  Future<void> _confirmPower(
    BuildContext context,
    String action,
    String label,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('$label this PC?'),
        content: const Text('Unsaved work on the Windows PC may be lost.'),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
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
        SnackBar(content: Text('$label simulated in Demo')),
      );
      return;
    }
    try {
      await controller?.sendPowerAction(action);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$label command sent')),
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
